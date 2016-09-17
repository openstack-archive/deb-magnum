# Copyright 2013 UnitedStack Inc.
# All Rights Reserved.
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

import uuid

from oslo_log import log as logging
from oslo_utils import timeutils
import pecan
import wsme
from wsme import types as wtypes

from magnum.api import attr_validator
from magnum.api.controllers import base
from magnum.api.controllers import link
from magnum.api.controllers.v1 import collection
from magnum.api.controllers.v1 import types
from magnum.api import expose
from magnum.api import utils as api_utils
from magnum.api.validation import validate_bay_properties
from magnum.common import clients
from magnum.common import exception
from magnum.common import name_generator
from magnum.common import policy
from magnum.i18n import _LW
from magnum import objects
from magnum.objects import fields

LOG = logging.getLogger(__name__)


class BayID(wtypes.Base):
    uuid = types.uuid

    def __init__(self, uuid):
        self.uuid = uuid


class Bay(base.APIBase):
    """API representation of a bay.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a bay.
    """

    _baymodel_id = None

    def _get_baymodel_id(self):
        return self._baymodel_id

    def _set_baymodel_id(self, value):
        if value and self._baymodel_id != value:
            try:
                baymodel = api_utils.get_resource('BayModel', value)
                self._baymodel_id = baymodel.uuid
            except exception.ClusterTemplateNotFound as e:
                # Change error code because 404 (NotFound) is inappropriate
                # response for a POST request to create a Bay
                e.code = 400  # BadRequest
                raise
        elif value == wtypes.Unset:
            self._baymodel_id = wtypes.Unset

    uuid = types.uuid
    """Unique UUID for this bay"""

    name = wtypes.StringType(min_length=1, max_length=242,
                             pattern='^[a-zA-Z][a-zA-Z0-9_.-]*$')
    """Name of this bay, max length is limited to 242 because of heat stack
    requires max length limit to 255, and Magnum amend a uuid length"""

    baymodel_id = wsme.wsproperty(wtypes.text, _get_baymodel_id,
                                  _set_baymodel_id, mandatory=True)
    """The baymodel UUID"""

    node_count = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    """The node count for this bay. Default to 1 if not set"""

    master_count = wsme.wsattr(wtypes.IntegerType(minimum=1), default=1)
    """The number of master nodes for this bay. Default to 1 if not set"""

    bay_create_timeout = wsme.wsattr(wtypes.IntegerType(minimum=0), default=60)
    """Timeout for creating the bay in minutes. Default to 60 if not set"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated bay links"""

    stack_id = wsme.wsattr(wtypes.text, readonly=True)
    """Stack id of the heat stack"""

    status = wtypes.Enum(str, *fields.BayStatus.ALL)
    """Status of the bay from the heat stack"""

    status_reason = wtypes.text
    """Status reason of the bay from the heat stack"""

    discovery_url = wtypes.text
    """Url used for bay node discovery"""

    api_address = wsme.wsattr(wtypes.text, readonly=True)
    """Api address of cluster master node"""

    coe_version = wsme.wsattr(wtypes.text, readonly=True)
    """Version of the COE software currently running in this cluster.
    Example: swarm version or kubernetes version."""

    container_version = wsme.wsattr(wtypes.text, readonly=True)
    """Version of the container software. Example: docker version."""

    node_addresses = wsme.wsattr([wtypes.text], readonly=True)
    """IP addresses of cluster slave nodes"""

    master_addresses = wsme.wsattr([wtypes.text], readonly=True)
    """IP addresses of cluster master nodes"""

    bay_faults = wsme.wsattr(wtypes.DictType(str, wtypes.text))
    """Fault info collected from the heat resources of this bay"""

    def __init__(self, **kwargs):
        super(Bay, self).__init__()

        self.fields = []
        for field in objects.Bay.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(bay, url, expand=True):
        if not expand:
            bay.unset_fields_except(['uuid', 'name', 'baymodel_id',
                                     'node_count', 'status',
                                     'bay_create_timeout', 'master_count',
                                     'stack_id'])

        bay.links = [link.Link.make_link('self', url,
                                         'bays', bay.uuid),
                     link.Link.make_link('bookmark', url,
                                         'bays', bay.uuid,
                                         bookmark=True)]
        return bay

    @classmethod
    def convert_with_links(cls, rpc_bay, expand=True):
        bay = Bay(**rpc_bay.as_dict())
        return cls._convert_with_links(bay, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='example',
                     baymodel_id='4a96ac4b-2447-43f1-8ca6-9fd6f36d146d',
                     node_count=2,
                     master_count=1,
                     bay_create_timeout=15,
                     stack_id='49dc23f5-ffc9-40c3-9d34-7be7f9e34d63',
                     status=fields.BayStatus.CREATE_COMPLETE,
                     status_reason="CREATE completed successfully",
                     api_address='172.24.4.3',
                     node_addresses=['172.24.4.4', '172.24.4.5'],
                     created_at=timeutils.utcnow(),
                     updated_at=timeutils.utcnow(),
                     coe_version=None,
                     container_version=None)
        return cls._convert_with_links(sample, 'http://localhost:9511', expand)


class BayPatchType(types.JsonPatchType):
    _api_base = Bay

    @staticmethod
    def internal_attrs():
        internal_attrs = ['/api_address', '/node_addresses',
                          '/master_addresses', '/stack_id',
                          '/ca_cert_ref', '/magnum_cert_ref',
                          '/trust_id', '/trustee_user_name',
                          '/trustee_password', '/trustee_user_id']
        return types.JsonPatchType.internal_attrs() + internal_attrs


class BayCollection(collection.Collection):
    """API representation of a collection of bays."""

    bays = [Bay]
    """A list containing bays objects"""

    def __init__(self, **kwargs):
        self._type = 'bays'

    @staticmethod
    def convert_with_links(rpc_bays, limit, url=None, expand=False, **kwargs):
        collection = BayCollection()
        collection.bays = [Bay.convert_with_links(p, expand)
                           for p in rpc_bays]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.bays = [Bay.sample(expand=False)]
        return sample


class BaysController(base.Controller):
    """REST controller for Bays."""
    def __init__(self):
        super(BaysController, self).__init__()

    _custom_actions = {
        'detail': ['GET'],
    }

    def _generate_name_for_bay(self, context):
        '''Generate a random name like: zeta-22-bay.'''
        name_gen = name_generator.NameGenerator()
        name = name_gen.generate()
        return name + '-bay'

    def _get_bays_collection(self, marker, limit,
                             sort_key, sort_dir, expand=False,
                             resource_url=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Bay.get_by_uuid(pecan.request.context,
                                                 marker)

        bays = objects.Bay.list(pecan.request.context, limit,
                                marker_obj, sort_key=sort_key,
                                sort_dir=sort_dir)

        return BayCollection.convert_with_links(bays, limit,
                                                url=resource_url,
                                                expand=expand,
                                                sort_key=sort_key,
                                                sort_dir=sort_dir)

    @expose.expose(BayCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of bays.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'bay:get_all',
                       action='bay:get_all')
        return self._get_bays_collection(marker, limit, sort_key,
                                         sort_dir)

    @expose.expose(BayCollection, types.uuid, int, wtypes.text,
                   wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id',
               sort_dir='asc'):
        """Retrieve a list of bays with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'bay:detail',
                       action='bay:detail')

        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "bays":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['bays', 'detail'])
        return self._get_bays_collection(marker, limit,
                                         sort_key, sort_dir, expand,
                                         resource_url)

    def _collect_fault_info(self, context, bay):
        """Collect fault info from heat resources of given bay

        and store them into bay.bay_faults.
        """
        osc = clients.OpenStackClients(context)
        filters = {'status': 'FAILED'}
        try:
            failed_resources = osc.heat().resources.list(
                bay.stack_id, nested_depth=2, filters=filters)
        except Exception as e:
            failed_resources = []
            LOG.warning(_LW("Failed to retrieve failed resources for "
                            "bay %(bay)s from Heat stack %(stack)s "
                            "due to error: %(e)s"),
                        {'bay': bay.uuid, 'stack': bay.stack_id, 'e': e},
                        exc_info=True)

        return {res.resource_name: res.resource_status_reason
                for res in failed_resources}

    @expose.expose(Bay, types.uuid_or_name)
    def get_one(self, bay_ident):
        """Retrieve information about the given bay.

        :param bay_ident: UUID of a bay or logical name of the bay.
        """
        context = pecan.request.context
        bay = api_utils.get_resource('Bay', bay_ident)
        policy.enforce(context, 'bay:get', bay,
                       action='bay:get')

        bay = Bay.convert_with_links(bay)

        if bay.status in fields.BayStatus.STATUS_FAILED:
            bay.bay_faults = self._collect_fault_info(context, bay)

        return bay

    @base.Controller.api_version("1.1", "1.1")
    @expose.expose(Bay, body=Bay, status_code=201)
    def post(self, bay):
        """Create a new bay.

        :param bay: a bay within the request body.
        """
        new_bay = self._post(bay)
        res_bay = pecan.request.rpcapi.bay_create(new_bay,
                                                  bay.bay_create_timeout)

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('bays', res_bay.uuid)
        return Bay.convert_with_links(res_bay)

    @base.Controller.api_version("1.2")  # noqa
    @expose.expose(BayID, body=Bay, status_code=202)
    def post(self, bay):
        """Create a new bay.

        :param bay: a bay within the request body.
        """
        new_bay = self._post(bay)
        pecan.request.rpcapi.bay_create_async(new_bay, bay.bay_create_timeout)
        return BayID(new_bay.uuid)

    def _post(self, bay):
        context = pecan.request.context
        policy.enforce(context, 'bay:create',
                       action='bay:create')
        baymodel = objects.BayModel.get_by_uuid(context, bay.baymodel_id)
        attr_validator.validate_os_resources(context, baymodel.as_dict())
        attr_validator.validate_master_count(bay.as_dict(), baymodel.as_dict())
        bay_dict = bay.as_dict()
        bay_dict['project_id'] = context.project_id
        bay_dict['user_id'] = context.user_id
        # NOTE(yuywz): We will generate a random human-readable name for
        # bay if the name is not spcified by user.
        name = bay_dict.get('name') or self._generate_name_for_bay(context)
        bay_dict['name'] = name
        bay_dict['coe_version'] = None
        bay_dict['container_version'] = None

        new_bay = objects.Bay(context, **bay_dict)
        new_bay.uuid = uuid.uuid4()
        return new_bay

    @base.Controller.api_version("1.1", "1.1")
    @wsme.validate(types.uuid, [BayPatchType])
    @expose.expose(Bay, types.uuid_or_name, body=[BayPatchType])
    def patch(self, bay_ident, patch):
        """Update an existing bay.

        :param bay_ident: UUID or logical name of a bay.
        :param patch: a json PATCH document to apply to this bay.
        """
        bay = self._patch(bay_ident, patch)
        res_bay = pecan.request.rpcapi.bay_update(bay)
        return Bay.convert_with_links(res_bay)

    @base.Controller.api_version("1.2", "1.2")   # noqa
    @wsme.validate(types.uuid, [BayPatchType])
    @expose.expose(BayID, types.uuid_or_name, body=[BayPatchType],
                   status_code=202)
    def patch(self, bay_ident, patch):
        """Update an existing bay.

        :param bay_ident: UUID or logical name of a bay.
        :param patch: a json PATCH document to apply to this bay.
        """
        bay = self._patch(bay_ident, patch)
        pecan.request.rpcapi.bay_update_async(bay)
        return BayID(bay.uuid)

    @base.Controller.api_version("1.3")   # noqa
    @wsme.validate(types.uuid, bool, [BayPatchType])
    @expose.expose(BayID, types.uuid_or_name, bool, body=[BayPatchType],
                   status_code=202)
    def patch(self, bay_ident, rollback=False, patch=None):
        """Update an existing bay.

        :param bay_ident: UUID or logical name of a bay.
        :param rollback: whether to rollback bay on update failure.
        :param patch: a json PATCH document to apply to this bay.
        """
        bay = self._patch(bay_ident, patch)
        pecan.request.rpcapi.bay_update_async(bay, rollback=rollback)
        return BayID(bay.uuid)

    def _patch(self, bay_ident, patch):
        context = pecan.request.context
        bay = api_utils.get_resource('Bay', bay_ident)
        policy.enforce(context, 'bay:update', bay,
                       action='bay:update')
        try:
            bay_dict = bay.as_dict()
            new_bay = Bay(**api_utils.apply_jsonpatch(bay_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Bay.fields:
            try:
                patch_val = getattr(new_bay, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if bay[field] != patch_val:
                bay[field] = patch_val

        delta = bay.obj_what_changed()

        validate_bay_properties(delta)
        return bay

    @base.Controller.api_version("1.1", "1.1")
    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, bay_ident):
        """Delete a bay.

        :param bay_ident: UUID of a bay or logical name of the bay.
        """
        bay = self._delete(bay_ident)

        pecan.request.rpcapi.bay_delete(bay.uuid)

    @base.Controller.api_version("1.2")  # noqa
    @expose.expose(None, types.uuid_or_name, status_code=204)
    def delete(self, bay_ident):
        """Delete a bay.

        :param bay_ident: UUID of a bay or logical name of the bay.
        """
        bay = self._delete(bay_ident)

        pecan.request.rpcapi.bay_delete_async(bay.uuid)

    def _delete(self, bay_ident):
        context = pecan.request.context
        bay = api_utils.get_resource('Bay', bay_ident)
        policy.enforce(context, 'bay:delete', bay,
                       action='bay:delete')
        return bay
