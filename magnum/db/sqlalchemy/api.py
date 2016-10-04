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

"""SQLAlchemy storage backend."""

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import uuidutils
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

from magnum.common import exception
from magnum.db import api
from magnum.db.sqlalchemy import models
from magnum.i18n import _

CONF = cfg.CONF


_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""
    return Connection()


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param session: if present, the session to use
    """

    session = kwargs.get('session') or get_session()
    query = session.query(model, *args)
    return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if strutils.is_int_like(value):
        return query.filter_by(id=value)
    elif uuidutils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


def _paginate_query(model, limit=None, marker=None, sort_key=None,
                    sort_dir=None, query=None):
    if not query:
        query = model_query(model)
    sort_keys = ['id']
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    try:
        query = db_utils.paginate_query(query, model, limit, sort_keys,
                                        marker=marker, sort_dir=sort_dir)
    except db_exc.InvalidSortKey:
        raise exception.InvalidParameterValue(
            _('The sort_key value "%(key)s" is an invalid field for sorting')
            % {'key': sort_key})
    return query.all()


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_tenant_filters(self, context, query):
        if context.is_admin and context.all_tenants:
            return query

        if context.project_id:
            query = query.filter_by(project_id=context.project_id)
        else:
            query = query.filter_by(user_id=context.user_id)

        return query

    def _add_clusters_filters(self, query, filters):
        if filters is None:
            filters = {}

        possible_filters = ["cluster_template_id", "name", "node_count",
                            "master_count", "stack_id", "api_address",
                            "node_addresses", "project_id", "user_id"]

        filter_names = set(filters).intersection(possible_filters)
        filter_dict = {filter_name: filters[filter_name]
                       for filter_name in filter_names}

        query = query.filter_by(**filter_dict)

        if 'status' in filters:
            query = query.filter(models.Cluster.status.in_(filters['status']))

        return query

    def get_cluster_list(self, context, filters=None, limit=None, marker=None,
                         sort_key=None, sort_dir=None):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = self._add_clusters_filters(query, filters)
        return _paginate_query(models.Cluster, limit, marker,
                               sort_key, sort_dir, query)

    def create_cluster(self, values):
        # ensure defaults are present for new clusters
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        cluster = models.Cluster()
        cluster.update(values)
        try:
            cluster.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ClusterAlreadyExists(uuid=values['uuid'])
        return cluster

    def get_cluster_by_id(self, context, cluster_id):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=cluster_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ClusterNotFound(cluster=cluster_id)

    def get_cluster_by_name(self, context, cluster_name):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(name=cluster_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple clusters exist with same name.'
                                     ' Please use the cluster uuid instead.')
        except NoResultFound:
            raise exception.ClusterNotFound(cluster=cluster_name)

    def get_cluster_by_uuid(self, context, cluster_uuid):
        query = model_query(models.Cluster)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=cluster_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ClusterNotFound(cluster=cluster_uuid)

    def destroy_cluster(self, cluster_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Cluster, session=session)
            query = add_identity_filter(query, cluster_id)

            try:
                query.one()
            except NoResultFound:
                raise exception.ClusterNotFound(cluster=cluster_id)

            query.delete()

    def update_cluster(self, cluster_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Cluster.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_cluster(cluster_id, values)

    def _do_update_cluster(self, cluster_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Cluster, session=session)
            query = add_identity_filter(query, cluster_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ClusterNotFound(cluster=cluster_id)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_cluster_template_filters(self, query, filters):
        if filters is None:
            filters = {}

        possible_filters = ["name", "image_id", "flavor_id",
                            "master_flavor_id", "keypair_id",
                            "external_network_id", "dns_nameserver",
                            "project_id", "user_id", "labels"]

        filter_names = set(filters).intersection(possible_filters)
        filter_dict = {filter_name: filters[filter_name]
                       for filter_name in filter_names}

        return query.filter_by(**filter_dict)

    def get_cluster_template_list(self, context, filters=None, limit=None,
                                  marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.ClusterTemplate)
        query = self._add_tenant_filters(context, query)
        query = self._add_cluster_template_filters(query, filters)
        # include public ClusterTemplates
        public_q = model_query(models.ClusterTemplate).filter_by(public=True)
        query = query.union(public_q)

        return _paginate_query(models.ClusterTemplate, limit, marker,
                               sort_key, sort_dir, query)

    def create_cluster_template(self, values):
        # ensure defaults are present for new ClusterTemplates
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        cluster_template = models.ClusterTemplate()
        cluster_template.update(values)
        try:
            cluster_template.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ClusterTemplateAlreadyExists(uuid=values['uuid'])
        return cluster_template

    def get_cluster_template_by_id(self, context, cluster_template_id):
        query = model_query(models.ClusterTemplate)
        query = self._add_tenant_filters(context, query)
        public_q = model_query(models.ClusterTemplate).filter_by(public=True)
        query = query.union(public_q)
        query = query.filter_by(id=cluster_template_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ClusterTemplateNotFound(
                clustertemplate=cluster_template_id)

    def get_cluster_template_by_uuid(self, context, cluster_template_uuid):
        query = model_query(models.ClusterTemplate)
        query = self._add_tenant_filters(context, query)
        public_q = model_query(models.ClusterTemplate).filter_by(public=True)
        query = query.union(public_q)
        query = query.filter_by(uuid=cluster_template_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.ClusterTemplateNotFound(
                clustertemplate=cluster_template_uuid)

    def get_cluster_template_by_name(self, context, cluster_template_name):
        query = model_query(models.ClusterTemplate)
        query = self._add_tenant_filters(context, query)
        public_q = model_query(models.ClusterTemplate).filter_by(public=True)
        query = query.union(public_q)
        query = query.filter_by(name=cluster_template_name)
        try:
            return query.one()
        except MultipleResultsFound:
            raise exception.Conflict('Multiple ClusterTemplates exist with'
                                     ' same name. Please use the '
                                     'ClusterTemplate uuid instead.')
        except NoResultFound:
            raise exception.ClusterTemplateNotFound(
                clustertemplate=cluster_template_name)

    def _is_cluster_template_referenced(self, session, cluster_template_uuid):
        """Checks whether the ClusterTemplate is referenced by cluster(s)."""
        query = model_query(models.Cluster, session=session)
        query = self._add_clusters_filters(query, {'cluster_template_id':
                                                   cluster_template_uuid})
        return query.count() != 0

    def _is_publishing_cluster_template(self, values):
        if (len(values) == 1 and
                'public' in values and values['public'] is True):
            return True
        return False

    def destroy_cluster_template(self, cluster_template_id):
        session = get_session()
        with session.begin():
            query = model_query(models.ClusterTemplate, session=session)
            query = add_identity_filter(query, cluster_template_id)

            try:
                cluster_template_ref = query.one()
            except NoResultFound:
                raise exception.ClusterTemplateNotFound(
                    clustertemplate=cluster_template_id)

            if self._is_cluster_template_referenced(
                    session, cluster_template_ref['uuid']):
                raise exception.ClusterTemplateReferenced(
                    clustertemplate=cluster_template_id)

            query.delete()

    def update_cluster_template(self, cluster_template_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing ClusterTemplate.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_cluster_template(cluster_template_id, values)

    def _do_update_cluster_template(self, cluster_template_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ClusterTemplate, session=session)
            query = add_identity_filter(query, cluster_template_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.ClusterTemplateNotFound(
                    clustertemplate=cluster_template_id)

            if self._is_cluster_template_referenced(session, ref['uuid']):
                # we only allow to update ClusterTemplate to be public
                if not self._is_publishing_cluster_template(values):
                    raise exception.ClusterTemplateReferenced(
                        clustertemplate=cluster_template_id)

            ref.update(values)
        return ref

    def create_x509keypair(self, values):
        # ensure defaults are present for new x509keypairs
        if not values.get('uuid'):
            values['uuid'] = uuidutils.generate_uuid()

        x509keypair = models.X509KeyPair()
        x509keypair.update(values)
        try:
            x509keypair.save()
        except db_exc.DBDuplicateEntry:
            raise exception.X509KeyPairAlreadyExists(uuid=values['uuid'])
        return x509keypair

    def get_x509keypair_by_id(self, context, x509keypair_id):
        query = model_query(models.X509KeyPair)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(id=x509keypair_id)
        try:
            return query.one()
        except NoResultFound:
            raise exception.X509KeyPairNotFound(x509keypair=x509keypair_id)

    def get_x509keypair_by_uuid(self, context, x509keypair_uuid):
        query = model_query(models.X509KeyPair)
        query = self._add_tenant_filters(context, query)
        query = query.filter_by(uuid=x509keypair_uuid)
        try:
            return query.one()
        except NoResultFound:
            raise exception.X509KeyPairNotFound(x509keypair=x509keypair_uuid)

    def destroy_x509keypair(self, x509keypair_id):
        session = get_session()
        with session.begin():
            query = model_query(models.X509KeyPair, session=session)
            query = add_identity_filter(query, x509keypair_id)
            count = query.delete()
            if count != 1:
                raise exception.X509KeyPairNotFound(x509keypair_id)

    def update_x509keypair(self, x509keypair_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing X509KeyPair.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_x509keypair(x509keypair_id, values)

    def _do_update_x509keypair(self, x509keypair_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.X509KeyPair, session=session)
            query = add_identity_filter(query, x509keypair_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.X509KeyPairNotFound(x509keypair=x509keypair_id)

            if 'provision_state' in values:
                values['provision_updated_at'] = timeutils.utcnow()

            ref.update(values)
        return ref

    def _add_x509keypairs_filters(self, query, filters):
        if filters is None:
            filters = {}

        if 'project_id' in filters:
            query = query.filter_by(project_id=filters['project_id'])
        if 'user_id' in filters:
            query = query.filter_by(user_id=filters['user_id'])

        return query

    def get_x509keypair_list(self, context, filters=None, limit=None,
                             marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.X509KeyPair)
        query = self._add_tenant_filters(context, query)
        query = self._add_x509keypairs_filters(query, filters)
        return _paginate_query(models.X509KeyPair, limit, marker,
                               sort_key, sort_dir, query)

    def destroy_magnum_service(self, magnum_service_id):
        session = get_session()
        with session.begin():
            query = model_query(models.MagnumService, session=session)
            query = add_identity_filter(query, magnum_service_id)
            count = query.delete()
            if count != 1:
                raise exception.MagnumServiceNotFound(
                    magnum_service_id=magnum_service_id)

    def update_magnum_service(self, magnum_service_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.MagnumService, session=session)
            query = add_identity_filter(query, magnum_service_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.MagnumServiceNotFound(
                    magnum_service_id=magnum_service_id)

            if 'report_count' in values:
                if values['report_count'] > ref.report_count:
                    ref.last_seen_up = timeutils.utcnow()

            ref.update(values)
        return ref

    def get_magnum_service_by_host_and_binary(self, context, host, binary):
        query = model_query(models.MagnumService)
        query = query.filter_by(host=host, binary=binary)
        try:
            return query.one()
        except NoResultFound:
            return None

    def create_magnum_service(self, values):
        magnum_service = models.MagnumService()
        magnum_service.update(values)
        try:
            magnum_service.save()
        except db_exc.DBDuplicateEntry:
            raise exception.MagnumServiceAlreadyExists(id=magnum_service['id'])
        return magnum_service

    def get_magnum_service_list(self, context, disabled=None, limit=None,
                                marker=None, sort_key=None, sort_dir=None
                                ):
        query = model_query(models.MagnumService)
        if disabled:
            query = query.filter_by(disabled=disabled)

        return _paginate_query(models.MagnumService, limit, marker,
                               sort_key, sort_dir, query)

    def create_quota(self, values):
        quotas = models.Quota()
        quotas.update(values)
        try:
            quotas.save()
        except db_exc.DBDuplicateEntry:
            raise exception.QuotaAlreadyExists(project_id=values['project_id'],
                                               resource=values['resource'])
        return quotas

    def quota_get_all_by_project_id(self, project_id):
        query = model_query(models.Quota)
        result = query.filter_by(project_id=project_id).all()

        return result
