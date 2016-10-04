# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Base classes for storage engines
"""

import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six


_BACKEND_MAPPING = {'sqlalchemy': 'magnum.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF, backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def __init__(self):
        """Constructor."""

    @abc.abstractmethod
    def get_cluster_list(self, context, filters=None, limit=None,
                         marker=None, sort_key=None, sort_dir=None):
        """Get matching clusters.

        Return a list of the specified columns for all clusters that match the
        specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of clusters to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_cluster(self, values):
        """Create a new cluster.

        :param values: A dict containing several items used to identify
                       and track the cluster, and several dicts which are
                       passed into the Drivers when managing this cluster.
                        For example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A cluster.
        """

    @abc.abstractmethod
    def get_cluster_by_id(self, context, cluster_id):
        """Return a cluster.

        :param context: The security context
        :param cluster_id: The id of a cluster.
        :returns: A cluster.
        """

    @abc.abstractmethod
    def get_cluster_by_uuid(self, context, cluster_uuid):
        """Return a cluster.

        :param context: The security context
        :param cluster_uuid: The uuid of a cluster.
        :returns: A cluster.
        """

    @abc.abstractmethod
    def get_cluster_by_name(self, context, cluster_name):
        """Return a cluster.

        :param context: The security context
        :param cluster_name: The name of a cluster.
        :returns: A cluster.
        """

    @abc.abstractmethod
    def destroy_cluster(self, cluster_id):
        """Destroy a cluster and all associated interfaces.

        :param cluster_id: The id or uuid of a cluster.
        """

    @abc.abstractmethod
    def update_cluster(self, cluster_id, values):
        """Update properties of a cluster.

        :param cluster_id: The id or uuid of a cluster.
        :returns: A cluster.
        :raises: ClusterNotFound
        """

    @abc.abstractmethod
    def get_cluster_template_list(self, context, filters=None,
                                  limit=None, marker=None, sort_key=None,
                                  sort_dir=None):
        """Get matching ClusterTemplates.

        Return a list of the specified columns for all ClusterTemplates that
        match the specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of ClusterTemplates to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_cluster_template(self, values):
        """Create a new ClusterTemplate.

        :param values: A dict containing several items used to identify
                       and track the ClusterTemplate, and several dicts which
                       are passed into the Drivers when managing this
                       ClusterTemplate.
                       For example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'name': 'example',
                         'type': 'virt'
                        }
        :returns: A ClusterTemplate.
        """

    @abc.abstractmethod
    def get_cluster_template_by_id(self, context, cluster_template_id):
        """Return a ClusterTemplate.

        :param context: The security context
        :param cluster_template_id: The id of a ClusterTemplate.
        :returns: A ClusterTemplate.
        """

    @abc.abstractmethod
    def get_cluster_template_by_uuid(self, context, cluster_template_uuid):
        """Return a ClusterTemplate.

        :param context: The security context
        :param cluster_template_uuid: The uuid of a ClusterTemplate.
        :returns: A ClusterTemplate.
        """

    @abc.abstractmethod
    def get_cluster_template_by_name(self, context, cluster_template_name):
        """Return a ClusterTemplate.

        :param context: The security context
        :param cluster_template_name: The name of a ClusterTemplate.
        :returns: A ClusterTemplate.
        """

    @abc.abstractmethod
    def destroy_cluster_template(self, cluster_template_id):
        """Destroy a ClusterTemplate and all associated interfaces.

        :param cluster_template_id: The id or uuid of a ClusterTemplate.
        """

    @abc.abstractmethod
    def update_cluster_template(self, cluster_template_id, values):
        """Update properties of a ClusterTemplate.

        :param cluster_template_id: The id or uuid of a ClusterTemplate.
        :returns: A ClusterTemplate.
        :raises: ClusterTemplateNotFound
        """

    @abc.abstractmethod
    def create_x509keypair(self, values):
        """Create a new x509keypair.

        :param values: A dict containing several items used to identify
                       and track the x509keypair, and several dicts which
                       are passed into the Drivers when managing this
                       x509keypair. For example:

                       ::

                        {
                         'uuid': uuidutils.generate_uuid(),
                         'certificate': 'AAA...',
                         'private_key': 'BBB...',
                         'private_key_passphrase': 'CCC...',
                         'intermediates': 'DDD...',
                        }
        :returns: A X509KeyPair.
        """

    @abc.abstractmethod
    def get_x509keypair_by_id(self, context, x509keypair_id):
        """Return a x509keypair.

        :param context: The security context
        :param x509keypair_id: The id of a x509keypair.
        :returns: A x509keypair.
        """

    @abc.abstractmethod
    def get_x509keypair_by_uuid(self, context, x509keypair_uuid):
        """Return a x509keypair.

        :param context: The security context
        :param x509keypair_uuid: The uuid of a x509keypair.
        :returns: A x509keypair.
        """

    @abc.abstractmethod
    def destroy_x509keypair(self, x509keypair_id):
        """Destroy a x509keypair.

        :param x509keypair_id: The id or uuid of a x509keypair.
        """

    @abc.abstractmethod
    def update_x509keypair(self, x509keypair_id, values):
        """Update properties of a X509KeyPair.

        :param x509keypair_id: The id or uuid of a X509KeyPair.
        :returns: A X509KeyPair.
        """

    @abc.abstractmethod
    def get_x509keypair_list(self, context, filters=None, limit=None,
                             marker=None, sort_key=None, sort_dir=None):
        """Get matching x509keypairs.

        Return a list of the specified columns for all x509keypairs
        that match the specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of x509keypairs to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def destroy_magnum_service(self, magnum_service_id):
        """Destroys a magnum_service record.

        :param magnum_service_id: The id of a magnum_service.
        """

    @abc.abstractmethod
    def update_magnum_service(self, magnum_service_id, values):
        """Update properties of a magnum_service.

        :param magnum_service_id: The id of a magnum_service record.
        """

    @abc.abstractmethod
    def get_magnum_service_by_host_and_binary(self, context, host, binary):
        """Return a magnum_service record.

        :param context: The security context
        :param host: The host where the binary is located.
        :param binary: The name of the binary.
        :returns: A magnum_service record.
        """

    @abc.abstractmethod
    def create_magnum_service(self, values):
        """Create a new magnum_service record.

        :param values: A dict containing several items used to identify
                       and define the magnum_service record.
        :returns: A magnum_service record.
        """

    @abc.abstractmethod
    def get_magnum_service_list(self, context, disabled=None, limit=None,
                                marker=None, sort_key=None, sort_dir=None):
        """Get matching magnum_service records.

        Return a list of the specified columns for all magnum_services
        those match the specified filters.

        :param context: The security context
        :param disabled: Filters disbaled services. Defaults to None.
        :param limit: Maximum number of magnum_services to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_quota(self, values):
        """Create a new Quota record for a resource in a project.

        :param values: A dict containing several items used to identify
                       and track quota for a resource in a project.

                       ::

                        {
                         'id': uuidutils.generate_uuid(),
                         'project_id': 'fake_project',
                         'resource': 'fake_resource',
                         'hard_limit': 'fake_hardlimit',
                        }

        :returns: A quota record.
        """

    @abc.abstractmethod
    def quota_get_all_by_project_id(self, project_id):
        """Gets Quota record for all the resources in a project.

        :param project_id: Project identifier of the project.

        :returns: Quota record for all resources in a project.
        """
