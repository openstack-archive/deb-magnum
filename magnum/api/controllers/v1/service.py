#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from oslo_utils import timeutils
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes

from magnum.api.controllers import link
from magnum.api.controllers.v1 import base as v1_base
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.api import validation
from magnum.common import exception
from magnum.common import k8s_manifest
from magnum.common import policy
from magnum.i18n import _
from magnum import objects


class ServicePatchType(v1_base.K8sPatchType):

    @staticmethod
    def internal_attrs():
        defaults = v1_base.K8sPatchType.internal_attrs()
        return defaults + ['/selector', '/ports', '/ip']


class Service(v1_base.K8sResourceBase):

    uuid = types.uuid
    """Unique UUID for this service"""

    selector = wsme.wsattr({wtypes.text: wtypes.text}, readonly=True)
    """Selector of this service"""

    ip = wtypes.text
    """IP of this service"""

    ports = wsme.wsattr([{wtypes.text: wtypes.IntegerType()}], readonly=True)
    """Port of this service"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated service links"""

    def __init__(self, **kwargs):
        super(Service, self).__init__()

        self.fields = []
        for field in objects.Service.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(service, url, expand=True):
        if not expand:
            service.unset_fields_except(['uuid', 'name', 'bay_uuid', 'labels',
                                         'selector', 'ip', 'ports'])

        service.links = [link.Link.make_link('self', url,
                                             'services', service.uuid),
                         link.Link.make_link('bookmark', url,
                                             'services', service.uuid,
                                             bookmark=True)
                         ]
        return service

    @classmethod
    def convert_with_links(cls, rpc_service, expand=True):
        service = Service(**rpc_service.as_dict())
        return cls._convert_with_links(service, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='fe78db47-9a37-4e9f-8572-804a10abc0aa',
                     name='MyService',
                     bay_uuid='7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                     labels={'label1': 'foo'},
                     selector={'label1': 'foo'},
                     ip='172.17.2.2',
                     ports=[{"port": 88,
                             "targetPort": 6379,
                             "protocol": "TCP"}],
                     manifest_url='file:///tmp/rc.yaml',
                     manifest='''{
                         "metadata": {
                             "name": "test",
                             "labels": {
                                 "key": "value"
                             }
                         },
                         "spec": {
                             "ports": [
                                 {
                                 "port": 88,
                                 "targetPort": 6379,
                                 "protocol": "TCP"
                                 }
                             ],
                             "selector": {
                                 "bar": "foo"
                             }
                         }
                         }''',
                     created_at=timeutils.utcnow(),
                     updated_at=timeutils.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)

    def parse_manifest(self):
        try:
            manifest = k8s_manifest.parse(self._get_manifest())
        except ValueError as e:
            raise exception.InvalidParameterValue(message=str(e))
        try:
            self.name = manifest["metadata"]["name"]
        except (KeyError, TypeError):
            raise exception.InvalidParameterValue(
                _("Field metadata['name'] can't be empty in manifest."))
        try:
            self.ports = manifest["spec"]["ports"][:]
        except (KeyError, TypeError):
            raise exception.InvalidParameterValue(
                _("Field spec['ports'] can't be empty in manifest."))

        if "selector" in manifest["spec"]:
            self.selector = manifest["spec"]["selector"]
        if "labels" in manifest["metadata"]:
            self.labels = manifest["metadata"]["labels"]


class ServiceCollection(collection.Collection):
    """API representation of a collection of services."""

    services = [Service]
    """A list containing services objects"""

    def __init__(self, **kwargs):
        self._type = 'services'

    @staticmethod
    def convert_with_links(rpc_services, limit, url=None,
                           expand=False, **kwargs):
        collection = ServiceCollection()
        collection.services = [Service.convert_with_links(p, expand)
                               for p in rpc_services]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.services = [Service.sample(expand=False)]
        return sample


class ServicesController(rest.RestController):
    """REST controller for Services."""

    def __init__(self):
        super(ServicesController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_services_collection(self, marker, limit,
                                 sort_key, sort_dir,
                                 bay_ident, expand=False,
                                 resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)
        context = pecan.request.context

        services = pecan.request.rpcapi.service_list(context, bay_ident)

        return ServiceCollection.convert_with_links(services, limit,
                                                    url=resource_url,
                                                    expand=expand,
                                                    sort_key=sort_key,
                                                    sort_dir=sort_dir)

    @expose.expose(ServiceCollection, types.uuid, types.uuid_or_name, int,
                   wtypes.text, wtypes.text)
    @policy.enforce_wsgi("service")
    @validation.enforce_bay_types('kubernetes')
    def get_all(self, marker=None, bay_ident=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of services.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param bay_ident: UUID or logical name of the Bay.
        """
        return self._get_services_collection(marker, limit, sort_key,
                                             sort_dir, bay_ident)

    @expose.expose(ServiceCollection, types.uuid, types.uuid_or_name, int,
                   wtypes.text, wtypes.text)
    @policy.enforce_wsgi("service")
    @validation.enforce_bay_types('kubernetes')
    def detail(self, marker=None, bay_ident=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of services with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param bay_ident: UUID or logical name of the Bay.
        """
        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "services":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['services', 'detail'])
        return self._get_services_collection(marker, limit,
                                             sort_key, sort_dir,
                                             bay_ident, expand,
                                             resource_url)

    @expose.expose(Service, types.uuid_or_name,
                   types.uuid_or_name)
    @policy.enforce_wsgi("service", "get")
    @validation.enforce_bay_types('kubernetes')
    def get_one(self, service_ident, bay_ident):
        """Retrieve information about the given service.

        :param service_ident: UUID or logical name of the service.
        :param bay_ident: UUID or logical name of the Bay.
        """
        context = pecan.request.context
        rpc_service = pecan.request.rpcapi.service_show(context,
                                                        service_ident,
                                                        bay_ident)
        return Service.convert_with_links(rpc_service)

    @expose.expose(Service, body=Service, status_code=201)
    @policy.enforce_wsgi("service", "create")
    @validation.enforce_bay_types('kubernetes')
    def post(self, service):
        """Create a new service.

        :param service: a service within the request body.
        """
        service.parse_manifest()
        service_dict = service.as_dict()
        context = pecan.request.context
        service_dict['project_id'] = context.project_id
        service_dict['user_id'] = context.user_id
        service_obj = objects.Service(context, **service_dict)
        new_service = pecan.request.rpcapi.service_create(service_obj)
        if new_service is None:
            raise exception.InvalidState()

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('services', new_service.uuid)
        return Service.convert_with_links(new_service)

    @wsme.validate(types.uuid, [ServicePatchType])
    @expose.expose(Service, types.uuid_or_name,
                   types.uuid_or_name, body=[ServicePatchType])
    @policy.enforce_wsgi("service", "update")
    @validation.enforce_bay_types('kubernetes')
    def patch(self, service_ident, bay_ident, patch):
        """Update an existing service.

        :param service_ident: UUID or logical name of a service.
        :param bay_ident: UUID or logical name of the Bay.
        :param patch: a json PATCH document to apply to this service.
        """
        service_dict = {}
        service_dict['manifest'] = None
        service_dict['manifest_url'] = None
        try:
            service = Service(**api_utils.apply_jsonpatch(service_dict, patch))
            if service.manifest or service.manifest_url:
                service.parse_manifest()
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        rpc_service = pecan.request.rpcapi.service_update(service_ident,
                                                          bay_ident,
                                                          service.manifest)
        return Service.convert_with_links(rpc_service)

    @expose.expose(None, types.uuid_or_name,
                   types.uuid_or_name, status_code=204)
    @policy.enforce_wsgi("service")
    @validation.enforce_bay_types('kubernetes')
    def delete(self, service_ident, bay_ident):
        """Delete a service.

        :param service_ident: UUID or logical name of a service.
        :param bay_ident: UUID or logical name of the Bay.
        """
        pecan.request.rpcapi.service_delete(service_ident, bay_ident)
