# Copyright 2015 OpenStack Foundation
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

"""Tests for manipulating Clusters via the DB API"""
from oslo_utils import uuidutils
import six

from magnum.common import context
from magnum.common import exception
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.tests.unit.db import base
from magnum.tests.unit.db import utils


class DbClusterTestCase(base.DbTestCase):

    def test_create_cluster(self):
        utils.create_test_cluster()

    def test_create_cluster_nullable_cluster_template_id(self):
        utils.create_test_cluster(cluster_template_id=None)

    def test_create_cluster_already_exists(self):
        utils.create_test_cluster()
        self.assertRaises(exception.ClusterAlreadyExists,
                          utils.create_test_cluster)

    def test_get_cluster_by_id(self):
        cluster = utils.create_test_cluster()
        res = self.dbapi.get_cluster_by_id(self.context, cluster.id)
        self.assertEqual(cluster.id, res.id)
        self.assertEqual(cluster.uuid, res.uuid)

    def test_get_cluster_by_name(self):
        cluster = utils.create_test_cluster()
        res = self.dbapi.get_cluster_by_name(self.context, cluster.name)
        self.assertEqual(cluster.name, res.name)
        self.assertEqual(cluster.uuid, res.uuid)

    def test_get_cluster_by_uuid(self):
        cluster = utils.create_test_cluster()
        res = self.dbapi.get_cluster_by_uuid(self.context, cluster.uuid)
        self.assertEqual(cluster.id, res.id)
        self.assertEqual(cluster.uuid, res.uuid)

    def test_get_cluster_that_does_not_exist(self):
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_id,
                          self.context, 999)
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_uuid,
                          self.context,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_get_cluster_list(self):
        uuids = []
        for i in range(1, 6):
            cluster = utils.create_test_cluster(uuid=uuidutils.generate_uuid())
            uuids.append(six.text_type(cluster['uuid']))
        res = self.dbapi.get_cluster_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_cluster_list_sorted(self):
        uuids = []
        for _ in range(5):
            cluster = utils.create_test_cluster(uuid=uuidutils.generate_uuid())
            uuids.append(six.text_type(cluster.uuid))
        res = self.dbapi.get_cluster_list(self.context, sort_key='uuid')
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), res_uuids)

        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.get_cluster_list,
                          self.context,
                          sort_key='foo')

    def test_get_cluster_list_with_filters(self):
        ct1 = utils.get_test_cluster_template(id=1,
                                              uuid=uuidutils.generate_uuid())
        ct2 = utils.get_test_cluster_template(id=2,
                                              uuid=uuidutils.generate_uuid())
        self.dbapi.create_cluster_template(ct1)
        self.dbapi.create_cluster_template(ct2)

        cluster1 = utils.create_test_cluster(
            name='cluster-one',
            uuid=uuidutils.generate_uuid(),
            cluster_template_id=ct1['uuid'],
            status=cluster_status.CREATE_IN_PROGRESS)
        cluster2 = utils.create_test_cluster(
            name='cluster-two',
            uuid=uuidutils.generate_uuid(),
            cluster_template_id=ct2['uuid'],
            node_count=1,
            master_count=1,
            status=cluster_status.UPDATE_IN_PROGRESS)
        cluster3 = utils.create_test_cluster(
            name='cluster-three',
            node_count=2,
            master_count=5,
            status=cluster_status.DELETE_IN_PROGRESS)

        res = self.dbapi.get_cluster_list(
            self.context, filters={'cluster_template_id': ct1['uuid']})
        self.assertEqual([cluster1.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(
            self.context, filters={'cluster_template_id': ct2['uuid']})
        self.assertEqual([cluster2.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'name': 'cluster-one'})
        self.assertEqual([cluster1.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'name': 'bad-cluster'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'node_count': 3})
        self.assertEqual([cluster1.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'node_count': 1})
        self.assertEqual([cluster2.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'master_count': 3})
        self.assertEqual([cluster1.id], [r.id for r in res])

        res = self.dbapi.get_cluster_list(self.context,
                                          filters={'master_count': 1})
        self.assertEqual([cluster2.id], [r.id for r in res])

        filters = {'status': [cluster_status.CREATE_IN_PROGRESS,
                              cluster_status.DELETE_IN_PROGRESS]}
        res = self.dbapi.get_cluster_list(self.context,
                                          filters=filters)
        self.assertEqual([cluster1.id, cluster3.id], [r.id for r in res])

    def test_get_cluster_list_by_admin_all_tenants(self):
        uuids = []
        for i in range(1, 6):
            cluster = utils.create_test_cluster(
                uuid=uuidutils.generate_uuid(),
                project_id=uuidutils.generate_uuid(),
                user_id=uuidutils.generate_uuid())
            uuids.append(six.text_type(cluster['uuid']))
        ctx = context.make_admin_context(all_tenants=True)
        res = self.dbapi.get_cluster_list(ctx)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(sorted(uuids), sorted(res_uuids))

    def test_get_cluster_list_cluster_template_not_exist(self):
        utils.create_test_cluster()
        self.assertEqual(1, len(self.dbapi.get_cluster_list(self.context)))
        res = self.dbapi.get_cluster_list(self.context, filters={
            'cluster_template_id': uuidutils.generate_uuid()})
        self.assertEqual(0, len(res))

    def test_destroy_cluster(self):
        cluster = utils.create_test_cluster()
        self.assertIsNotNone(self.dbapi.get_cluster_by_id(self.context,
                                                          cluster.id))
        self.dbapi.destroy_cluster(cluster.id)
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_id,
                          self.context, cluster.id)

    def test_destroy_cluster_by_uuid(self):
        cluster = utils.create_test_cluster()
        self.assertIsNotNone(self.dbapi.get_cluster_by_uuid(self.context,
                                                            cluster.uuid))
        self.dbapi.destroy_cluster(cluster.uuid)
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.get_cluster_by_uuid, self.context,
                          cluster.uuid)

    def test_destroy_cluster_that_does_not_exist(self):
        self.assertRaises(exception.ClusterNotFound,
                          self.dbapi.destroy_cluster,
                          '12345678-9999-0000-aaaa-123456789012')

    def test_update_cluster(self):
        cluster = utils.create_test_cluster()
        old_nc = cluster.node_count
        new_nc = 5
        self.assertNotEqual(old_nc, new_nc)
        res = self.dbapi.update_cluster(cluster.id, {'node_count': new_nc})
        self.assertEqual(new_nc, res.node_count)

    def test_update_cluster_not_found(self):
        cluster_uuid = uuidutils.generate_uuid()
        self.assertRaises(exception.ClusterNotFound, self.dbapi.update_cluster,
                          cluster_uuid, {'node_count': 5})

    def test_update_cluster_uuid(self):
        cluster = utils.create_test_cluster()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_cluster, cluster.id,
                          {'uuid': ''})
