#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

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


class PodPatchType(v1_base.K8sPatchType):
    pass


class Pod(v1_base.K8sResourceBase):
    """API representation of a pod.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a pod.
    """

    uuid = types.uuid
    """Unique UUID for this pod"""

    desc = wtypes.text
    """Description of this pod"""

    images = [wtypes.text]
    """A list of images used by containers in this pod."""

    status = wtypes.text
    """Staus of this pod """

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated pod links"""

    host = wtypes.text
    """The host of this pod"""

    def __init__(self, **kwargs):
        super(Pod, self).__init__()

        self.fields = []
        for field in objects.Pod.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(pod, url, expand=True):
        if not expand:
            pod.unset_fields_except(['uuid', 'name', 'desc', 'bay_uuid',
                                     'images', 'labels', 'status', 'host'])

        pod.links = [link.Link.make_link('self', url,
                                         'pods', pod.uuid),
                     link.Link.make_link('bookmark', url,
                                         'pods', pod.uuid,
                                         bookmark=True)
                     ]
        return pod

    @classmethod
    def convert_with_links(cls, rpc_pod, expand=True):
        pod = Pod(**rpc_pod.as_dict())
        return cls._convert_with_links(pod, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='f978db47-9a37-4e9f-8572-804a10abc0aa',
                     name='MyPod',
                     desc='Pod - Description',
                     bay_uuid='7ae81bb3-dec3-4289-8d6c-da80bd8001ae',
                     images=['MyImage'],
                     labels={'name': 'foo'},
                     status='Running',
                     host='10.0.0.3',
                     manifest_url='file:///tmp/rc.yaml',
                     manifest='''{
                         "metadata": {
                             "name": "name_of_pod"
                         },
                         "spec": {
                             "containers": [
                                 {
                                     "name": "test",
                                     "image": "test"
                                 }
                             ]
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
        images = []
        try:
            for container in manifest["spec"]["containers"]:
                images.append(container["image"])
            self.images = images
        except (KeyError, TypeError):
            raise exception.InvalidParameterValue(
                _("Field spec['containers'] can't be empty in manifest."))
        if "labels" in manifest["metadata"]:
            self.labels = manifest["metadata"]["labels"]


class PodCollection(collection.Collection):
    """API representation of a collection of pods."""

    pods = [Pod]
    """A list containing pods objects"""

    def __init__(self, **kwargs):
        self._type = 'pods'

    @staticmethod
    def convert_with_links(rpc_pods, limit, url=None, expand=False, **kwargs):
        collection = PodCollection()
        collection.pods = [Pod.convert_with_links(p, expand)
                           for p in rpc_pods]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.pods = [Pod.sample(expand=False)]
        return sample


class PodsController(rest.RestController):
    """REST controller for Pods."""

    def __init__(self):
        super(PodsController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_pods_collection(self, marker, limit,
                             sort_key, sort_dir,
                             bay_ident, expand=False,
                             resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)
        context = pecan.request.context

        pods = pecan.request.rpcapi.pod_list(context, bay_ident)

        return PodCollection.convert_with_links(pods, limit,
                                                url=resource_url,
                                                expand=expand,
                                                sort_key=sort_key,
                                                sort_dir=sort_dir)

    @expose.expose(PodCollection, types.uuid, types.uuid_or_name, int,
                   wtypes.text, wtypes.text)
    @policy.enforce_wsgi("pod")
    @validation.enforce_bay_types('kubernetes')
    def get_all(self, marker=None, bay_ident=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of pods.

        :param marker: pagination marker for large data sets.
        :param bay_ident: UUID or logical name of the Bay.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.

        """
        return self._get_pods_collection(marker, limit, sort_key,
                                         sort_dir, bay_ident)

    @expose.expose(PodCollection, types.uuid, types.uuid_or_name, int,
                   wtypes.text, wtypes.text)
    @policy.enforce_wsgi("pod")
    @validation.enforce_bay_types('kubernetes')
    def detail(self, marker=None, bay_ident=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of pods with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param bay_ident: UUID or logical name of the Bay.
        """
        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "pods":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['pods', 'detail'])
        return self._get_pods_collection(marker, limit,
                                         sort_key, sort_dir,
                                         bay_ident, expand,
                                         resource_url)

    @expose.expose(Pod, types.uuid_or_name,
                   types.uuid_or_name)
    @policy.enforce_wsgi("pod", "get")
    @validation.enforce_bay_types('kubernetes')
    def get_one(self, pod_ident, bay_ident):
        """Retrieve information about the given pod.

        :param pod_ident: UUID of a pod or logical name of the pod.
        :param bay_ident: UUID or logical name of the Bay.
        """
        context = pecan.request.context
        rpc_pod = pecan.request.rpcapi.pod_show(context, pod_ident, bay_ident)

        return Pod.convert_with_links(rpc_pod)

    @expose.expose(Pod, body=Pod, status_code=201)
    @policy.enforce_wsgi("pod", "create")
    @validation.enforce_bay_types('kubernetes')
    def post(self, pod):
        """Create a new pod.

        :param pod: a pod within the request body.
        """
        pod.parse_manifest()
        pod_dict = pod.as_dict()
        context = pecan.request.context
        pod_dict['project_id'] = context.project_id
        pod_dict['user_id'] = context.user_id
        pod_obj = objects.Pod(context, **pod_dict)
        new_pod = pecan.request.rpcapi.pod_create(pod_obj)
        # Set the HTTP Location Header
        pecan.response.location = link.build_url('pods', new_pod.uuid)
        return Pod.convert_with_links(new_pod)

    @wsme.validate(types.uuid, [PodPatchType])
    @expose.expose(Pod, types.uuid_or_name,
                   types.uuid_or_name, body=[PodPatchType])
    @policy.enforce_wsgi("pod", "update")
    @validation.enforce_bay_types('kubernetes')
    def patch(self, pod_ident, bay_ident, patch):
        """Update an existing pod.

        :param pod_ident: UUID or logical name of a pod.
        :param bay_ident: UUID or logical name of the Bay.
        :param patch: a json PATCH document to apply to this pod.
        """
        pod_dict = {}
        pod_dict['manifest'] = None
        pod_dict['manifest_url'] = None
        try:
            pod = Pod(**api_utils.apply_jsonpatch(pod_dict, patch))
            if pod.manifest or pod.manifest_url:
                pod.parse_manifest()
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        rpc_pod = pecan.request.rpcapi.pod_update(pod_ident, bay_ident,
                                                  pod.manifest)
        return Pod.convert_with_links(rpc_pod)

    @expose.expose(None, types.uuid_or_name,
                   types.uuid_or_name, status_code=204)
    @policy.enforce_wsgi("pod")
    @validation.enforce_bay_types('kubernetes')
    def delete(self, pod_ident, bay_ident):
        """Delete a pod.

        :param pod_ident: UUID of a pod or logical name of the pod.
        :param bay_ident: UUID or logical name of the Bay.
        """
        pecan.request.rpcapi.pod_delete(pod_ident, bay_ident)
