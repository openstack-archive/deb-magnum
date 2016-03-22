# Copyright 2013 Red Hat, Inc.
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

import jsonpatch
from oslo_config import cfg
import pecan
import wsme

from magnum.common import exception
from magnum.common import utils
from magnum.i18n import _
from magnum import objects

CONF = cfg.CONF


JSONPATCH_EXCEPTIONS = (jsonpatch.JsonPatchException,
                        jsonpatch.JsonPointerException,
                        KeyError)


def validate_limit(limit):
    if limit is not None and limit <= 0:
        raise wsme.exc.ClientSideError(_("Limit must be positive"))

    if limit is not None:
        return min(CONF.api.max_limit, limit)
    else:
        return CONF.api.max_limit


def validate_sort_dir(sort_dir):
    if sort_dir not in ['asc', 'desc']:
        raise wsme.exc.ClientSideError(_("Invalid sort direction: %s. "
                                         "Acceptable values are "
                                         "'asc' or 'desc'") % sort_dir)
    return sort_dir


def apply_jsonpatch(doc, patch):
    for p in patch:
        if p['op'] == 'add' and p['path'].count('/') == 1:
            attr = p['path'].lstrip('/')
            if attr not in doc:
                msg = _("Adding a new attribute %s to the root of "
                        "the resource is not allowed.") % p['path']
                raise wsme.exc.ClientSideError(msg)
            if doc[attr] is not None:
                msg = _("The attribute %s has existed, please use "
                        "'replace' operation instead.") % p['path']
                raise wsme.exc.ClientSideError(msg)
    return jsonpatch.apply_patch(doc, patch)


def get_resource(resource, resource_ident):
    """Get the resource from the uuid or logical name.

    :param resource: the resource type.
    :param resource_ident: the UUID or logical name of the resource.

    :returns: The resource.
    """
    resource = getattr(objects, resource)

    if utils.is_uuid_like(resource_ident):
        return resource.get_by_uuid(pecan.request.context, resource_ident)

    return resource.get_by_name(pecan.request.context, resource_ident)


def get_openstack_resource(manager, resource_ident, resource_type):
    """Get the openstack resource from the uuid or logical name.

    :param manager: the resource manager class.
    :param resource_ident: the UUID or logical name of the resource.
    :param resource_type: the type of the resource

    :returns: The openstack resource.
    :raises: ResourceNotFound if the openstack resource is not exist.
             Conflict if multi openstack resources have same name.
    """
    if utils.is_uuid_like(resource_ident):
        resource_data = manager.get(resource_ident)
    else:
        filters = {'name': resource_ident}
        matches = list(manager.list(filters=filters))
        if len(matches) == 0:
            raise exception.ResourceNotFound(name=resource_type,
                                             id=resource_ident)
        if len(matches) > 1:
            msg = ("Multiple '%s' exist with same name '%s'. "
                   "Please use the resource id instead." %
                   (resource_type, resource_ident))
            raise exception.Conflict(msg)
        resource_data = matches[0]
    return resource_data
