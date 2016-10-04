# Licensed under the Apache License, Version 2.0 (the "License");
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

import datetime

import mock
from oslo_config import cfg
from oslo_utils import timeutils
from oslo_utils import uuidutils

from magnum.api import attr_validator
from magnum.api.controllers.v1 import cluster as api_cluster
from magnum.common import exception
from magnum.conductor import api as rpcapi
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils


class TestClusterObject(base.TestCase):
    def test_cluster_init(self):
        cluster_dict = apiutils.cluster_post_data(cluster_template_id=None)
        del cluster_dict['node_count']
        del cluster_dict['master_count']
        del cluster_dict['create_timeout']
        cluster = api_cluster.Cluster(**cluster_dict)
        self.assertEqual(1, cluster.node_count)
        self.assertEqual(1, cluster.master_count)
        self.assertEqual(60, cluster.create_timeout)


class TestListCluster(api_base.FunctionalTest):
    _cluster_attrs = ("name", "cluster_template_id", "node_count", "status",
                      "master_count", "stack_id", "create_timeout")

    _expand_cluster_attrs = ("name", "cluster_template_id", "node_count",
                             "status", "api_address", "discovery_url",
                             "node_addresses", "master_count",
                             "master_addresses", "stack_id",
                             "create_timeout", "status_reason")

    def setUp(self):
        super(TestListCluster, self).setUp()
        obj_utils.create_test_cluster_template(self.context)

    def test_empty(self):
        response = self.get_json('/clusters')
        self.assertEqual([], response['clusters'])

    def test_one(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters')
        self.assertEqual(cluster.uuid, response['clusters'][0]["uuid"])
        self._verify_attrs(self._cluster_attrs, response['clusters'][0])

        # Verify attrs do not appear from cluster's get_all response
        none_attrs = \
            set(self._expand_cluster_attrs) - set(self._cluster_attrs)
        self._verify_attrs(none_attrs, response['clusters'][0],
                           positive=False)

    def test_get_one(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters/%s' % cluster['uuid'])
        self.assertEqual(cluster.uuid, response['uuid'])
        self._verify_attrs(self._expand_cluster_attrs, response)

    @mock.patch('magnum.common.clients.OpenStackClients.heat')
    def test_get_one_failed_cluster(self, mock_heat):
        fake_resources = mock.MagicMock()
        fake_resources.resource_name = 'fake_name'
        fake_resources.resource_status_reason = 'fake_reason'

        ht = mock.MagicMock()
        ht.resources.list.return_value = [fake_resources]
        mock_heat.return_value = ht

        cluster = obj_utils.create_test_cluster(self.context,
                                                status='CREATE_FAILED')
        response = self.get_json('/clusters/%s' % cluster['uuid'])
        self.assertEqual(cluster.uuid, response['uuid'])
        self.assertEqual({'fake_name': 'fake_reason'}, response['faults'])

    @mock.patch('magnum.common.clients.OpenStackClients.heat')
    def test_get_one_failed_cluster_heatclient_exception(self, mock_heat):
        mock_heat.resources.list.side_effect = Exception('fake')
        cluster = obj_utils.create_test_cluster(self.context,
                                                status='CREATE_FAILED')
        response = self.get_json('/clusters/%s' % cluster['uuid'])
        self.assertEqual(cluster.uuid, response['uuid'])
        self.assertEqual({}, response['faults'])

    def test_get_one_by_name(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters/%s' % cluster['name'])
        self.assertEqual(cluster.uuid, response['uuid'])
        self._verify_attrs(self._expand_cluster_attrs, response)

    def test_get_one_by_name_not_found(self):
        response = self.get_json(
            '/clusters/not_found',
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_one_by_name_multiple_cluster(self):
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        response = self.get_json('/clusters/test_cluster',
                                 expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_get_all_with_pagination_marker(self):
        cluster_list = []
        for id_ in range(4):
            temp_uuid = uuidutils.generate_uuid()
            cluster = obj_utils.create_test_cluster(self.context, id=id_,
                                                    uuid=temp_uuid)
            cluster_list.append(cluster)

        response = self.get_json('/clusters?limit=3&marker=%s'
                                 % cluster_list[2].uuid)
        self.assertEqual(1, len(response['clusters']))
        self.assertEqual(cluster_list[-1].uuid,
                         response['clusters'][0]['uuid'])

    def test_detail(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters/detail')
        self.assertEqual(cluster.uuid, response['clusters'][0]["uuid"])
        self._verify_attrs(self._expand_cluster_attrs,
                           response['clusters'][0])

    def test_detail_with_pagination_marker(self):
        cluster_list = []
        for id_ in range(4):
            temp_uuid = uuidutils.generate_uuid()
            cluster = obj_utils.create_test_cluster(self.context, id=id_,
                                                    uuid=temp_uuid)
            cluster_list.append(cluster)

        response = self.get_json('/clusters/detail?limit=3&marker=%s'
                                 % cluster_list[2].uuid)
        self.assertEqual(1, len(response['clusters']))
        self.assertEqual(cluster_list[-1].uuid,
                         response['clusters'][0]['uuid'])
        self._verify_attrs(self._expand_cluster_attrs,
                           response['clusters'][0])

    def test_detail_against_single(self):
        cluster = obj_utils.create_test_cluster(self.context)
        response = self.get_json('/clusters/%s/detail' % cluster['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        bm_list = []
        for id_ in range(5):
            temp_uuid = uuidutils.generate_uuid()
            cluster = obj_utils.create_test_cluster(self.context, id=id_,
                                                    uuid=temp_uuid)
            bm_list.append(cluster.uuid)
        response = self.get_json('/clusters')
        self.assertEqual(len(bm_list), len(response['clusters']))
        uuids = [b['uuid'] for b in response['clusters']]
        self.assertEqual(sorted(bm_list), sorted(uuids))

    def test_links(self):
        uuid = uuidutils.generate_uuid()
        obj_utils.create_test_cluster(self.context, id=1, uuid=uuid)
        response = self.get_json('/clusters/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'],
                                               bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_cluster(self.context, id=id_,
                                          uuid=uuidutils.generate_uuid())
        response = self.get_json('/clusters/?limit=3')
        self.assertEqual(3, len(response['clusters']))

        next_marker = response['clusters'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_cluster(self.context, id=id_,
                                          uuid=uuidutils.generate_uuid())
        response = self.get_json('/clusters')
        self.assertEqual(3, len(response['clusters']))

        next_marker = response['clusters'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):
    def setUp(self):
        super(TestPatch, self).setUp()
        self.cluster_template_obj = obj_utils.create_test_cluster_template(
            self.context)
        self.cluster_obj = obj_utils.create_test_cluster(
            self.context, name='cluster_example_A', node_count=3)
        p = mock.patch.object(rpcapi.API, 'cluster_update_async')
        self.mock_cluster_update = p.start()
        self.mock_cluster_update.side_effect = self._sim_rpc_cluster_update
        self.addCleanup(p.stop)

    def _sim_rpc_cluster_update(self, cluster, rollback=False):
        cluster.save()
        return cluster

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        new_node_count = 4
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/node_count',
                                     'value': new_node_count,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name(self, mock_utcnow):
        new_node_count = 4
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/clusters/%s' % self.cluster_obj.name,
                                   [{'path': '/node_count',
                                     'value': new_node_count,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertEqual(new_node_count, response['node_count'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)
        # Assert nothing else was changed
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_not_found(self, mock_utcnow):
        name = 'not_found'
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.patch_json('/clusters/%s' % name,
                                   [{'path': '/name', 'value': name,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(404, response.status_code)

    def test_replace_cluster_template_id_failed(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context,
            uuid=uuidutils.generate_uuid())
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/cluster_template_id',
                                     'value': cluster_template.uuid,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name_multiple_cluster(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())

        response = self.patch_json('/clusters/test_cluster',
                                   [{'path': '/name',
                                     'value': 'test_cluster',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(409, response.status_code)

    def test_replace_non_existent_cluster_template_id(self):
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/cluster_template_id',
                                     'value': uuidutils.generate_uuid(),
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_invalid_node_count(self):
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/node_count', 'value': -1,
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])

    def test_replace_non_existent_cluster(self):
        response = self.patch_json('/clusters/%s' %
                                   uuidutils.generate_uuid(),
                                   [{'path': '/name',
                                     'value': 'cluster_example_B',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_replace_cluster_name_failed(self):
        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/name',
                                     'value': 'cluster_example_B',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/clusters/%s' % self.cluster_obj.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_remove_ok(self):
        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        self.assertIsNotNone(response['name'])

        response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                   [{'path': '/node_count',
                                     'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_code)

        response = self.get_json('/clusters/%s' % self.cluster_obj.uuid)
        # only allow node_count for cluster, and default value is 1
        self.assertEqual(1, response['node_count'])
        # Assert nothing else was changed
        self.assertEqual(self.cluster_obj.uuid, response['uuid'])
        self.assertEqual(self.cluster_obj.cluster_template_id,
                         response['cluster_template_id'])
        self.assertEqual(self.cluster_obj.name, response['name'])
        self.assertEqual(self.cluster_obj.master_count,
                         response['master_count'])

    def test_remove_mandatory_property_fail(self):
        mandatory_properties = ('/uuid', '/cluster_template_id')
        for p in mandatory_properties:
            response = self.patch_json('/clusters/%s' % self.cluster_obj.uuid,
                                       [{'path': p, 'op': 'remove'}],
                                       expect_errors=True)
            self.assertEqual(400, response.status_int)
            self.assertEqual('application/json', response.content_type)
            self.assertTrue(response.json['errors'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/clusters/%s' % self.cluster_obj.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['errors'])


class TestPost(api_base.FunctionalTest):
    def setUp(self):
        super(TestPost, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        p = mock.patch.object(rpcapi.API, 'cluster_create_async')
        self.mock_cluster_create = p.start()
        self.mock_cluster_create.side_effect = self._simulate_cluster_create
        self.addCleanup(p.stop)
        p = mock.patch.object(attr_validator, 'validate_os_resources')
        self.mock_valid_os_res = p.start()
        self.addCleanup(p.stop)

    def _simulate_cluster_create(self, cluster, create_timeout):
        cluster.create()
        return cluster

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_cluster(self, mock_utcnow):
        bdict = apiutils.cluster_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    def test_create_cluster_set_project_id_and_user_id(self):
        bdict = apiutils.cluster_post_data()

        def _simulate_rpc_cluster_create(cluster, create_timeout):
            self.assertEqual(self.context.project_id, cluster.project_id)
            self.assertEqual(self.context.user_id, cluster.user_id)
            cluster.create()
            return cluster

        self.mock_cluster_create.side_effect = _simulate_rpc_cluster_create

        self.post_json('/clusters', bdict)

    def test_create_cluster_doesnt_contain_id(self):
        with mock.patch.object(self.dbapi, 'create_cluster',
                               wraps=self.dbapi.create_cluster) as cc_mock:
            bdict = apiutils.cluster_post_data(name='cluster_example_A')
            response = self.post_json('/clusters', bdict)
            cc_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cc_mock.call_args[0][0])
            self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    def test_create_cluster_generate_uuid(self):
        bdict = apiutils.cluster_post_data()
        del bdict['uuid']

        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)
        self.assertTrue(uuidutils.is_uuid_like(response.json['uuid']))

    def test_create_cluster_no_cluster_template_id(self):
        bdict = apiutils.cluster_post_data()
        del bdict['cluster_template_id']
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_non_existent_cluster_template_id(self):
        temp_uuid = uuidutils.generate_uuid()
        bdict = apiutils.cluster_post_data(cluster_template_id=temp_uuid)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_cluster_template_name(self):
        modelname = self.cluster_template.name
        bdict = apiutils.cluster_post_data(cluster_template_id=modelname)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_node_count_zero(self):
        bdict = apiutils.cluster_post_data()
        bdict['node_count'] = 0
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_node_count_negative(self):
        bdict = apiutils.cluster_post_data()
        bdict['node_count'] = -1
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_no_node_count(self):
        bdict = apiutils.cluster_post_data()
        del bdict['node_count']
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_master_count_zero(self):
        bdict = apiutils.cluster_post_data()
        bdict['master_count'] = 0
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_no_master_count(self):
        bdict = apiutils.cluster_post_data()
        del bdict['master_count']
        response = self.post_json('/clusters', bdict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_invalid_long_name(self):
        bdict = apiutils.cluster_post_data(name='x' * 243)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_invalid_integer_name(self):
        bdict = apiutils.cluster_post_data(name='123456')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_invalid_integer_str_name(self):
        bdict = apiutils.cluster_post_data(name='123456test_cluster')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_hyphen_invalid_at_start_name(self):
        bdict = apiutils.cluster_post_data(name='-test_cluster')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_period_invalid_at_start_name(self):
        bdict = apiutils.cluster_post_data(name='.test_cluster')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_underscore_invalid_at_start_name(self):
        bdict = apiutils.cluster_post_data(name='_test_cluster')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_valid_str_int_name(self):
        bdict = apiutils.cluster_post_data(name='test_cluster123456')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_hyphen_valid_name(self):
        bdict = apiutils.cluster_post_data(name='test-cluster')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_period_valid_name(self):
        bdict = apiutils.cluster_post_data(name='test.cluster')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_period_at_end_valid_name(self):
        bdict = apiutils.cluster_post_data(name='testcluster.')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_hyphen_at_end_valid_name(self):
        bdict = apiutils.cluster_post_data(name='testcluster-')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_underscore_at_end_valid_name(self):
        bdict = apiutils.cluster_post_data(name='testcluster_')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_mix_special_char_valid_name(self):
        bdict = apiutils.cluster_post_data(name='test.-_cluster')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_capital_letter_start_valid_name(self):
        bdict = apiutils.cluster_post_data(name='Testcluster')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_invalid_empty_name(self):
        bdict = apiutils.cluster_post_data(name='')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_without_name(self):
        bdict = apiutils.cluster_post_data()
        del bdict['name']
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_timeout_none(self):
        bdict = apiutils.cluster_post_data()
        bdict['create_timeout'] = None
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_no_timeout(self):
        def _simulate_rpc_cluster_create(cluster, create_timeout):
            self.assertEqual(60, create_timeout)
            cluster.create()
            return cluster

        self.mock_cluster_create.side_effect = _simulate_rpc_cluster_create
        bdict = apiutils.cluster_post_data()
        del bdict['create_timeout']
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_timeout_negative(self):
        bdict = apiutils.cluster_post_data()
        bdict['create_timeout'] = -1
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['errors'])

    def test_create_cluster_with_timeout_zero(self):
        bdict = apiutils.cluster_post_data()
        bdict['create_timeout'] = 0
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_invalid_flavor(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.FlavorNotFound(
            'test-flavor')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_invalid_ext_network(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = \
            exception.ExternalNetworkNotFound('test-net')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_invalid_keypair(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.KeyPairNotFound(
            'test-key')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(404, response.status_int)

    def test_create_cluster_with_nonexist_image(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.ImageNotFound(
            'test-img')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_multi_images_same_name(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = exception.Conflict('test-img')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(409, response.status_int)

    def test_create_cluster_with_on_os_distro_image(self):
        bdict = apiutils.cluster_post_data()
        self.mock_valid_os_res.side_effect = \
            exception.OSDistroFieldNotFound('img')
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(self.mock_valid_os_res.called)
        self.assertEqual(400, response.status_int)

    def test_create_cluster_with_no_lb_one_node(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context, name='foo', uuid='foo', master_lb_enabled=False)
        bdict = apiutils.cluster_post_data(
            cluster_template_id=cluster_template.name, master_count=1)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(202, response.status_int)

    def test_create_cluster_with_no_lb_multi_node(self):
        cluster_template = obj_utils.create_test_cluster_template(
            self.context, name='foo', uuid='foo', master_lb_enabled=False)
        bdict = apiutils.cluster_post_data(
            cluster_template_id=cluster_template.name, master_count=3)
        response = self.post_json('/clusters', bdict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)


class TestDelete(api_base.FunctionalTest):
    def setUp(self):
        super(TestDelete, self).setUp()
        self.cluster_template = obj_utils.create_test_cluster_template(
            self.context)
        self.cluster = obj_utils.create_test_cluster(self.context)
        p = mock.patch.object(rpcapi.API, 'cluster_delete_async')
        self.mock_cluster_delete = p.start()
        self.mock_cluster_delete.side_effect = self._simulate_cluster_delete
        self.addCleanup(p.stop)

    def _simulate_cluster_delete(self, cluster_uuid):
        cluster = objects.Cluster.get_by_uuid(self.context, cluster_uuid)
        cluster.destroy()

    def test_delete_cluster(self):
        self.delete('/clusters/%s' % self.cluster.uuid)
        response = self.get_json('/clusters/%s' % self.cluster.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_cluster_not_found(self):
        uuid = uuidutils.generate_uuid()
        response = self.delete('/clusters/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_cluster_with_name_not_found(self):
        response = self.delete('/clusters/not_found', expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])

    def test_delete_cluster_with_name(self):
        response = self.delete('/clusters/%s' % self.cluster.name,
                               expect_errors=True)
        self.assertEqual(204, response.status_int)

    def test_delete_multiple_cluster_by_name(self):
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        obj_utils.create_test_cluster(self.context, name='test_cluster',
                                      uuid=uuidutils.generate_uuid())
        response = self.delete('/clusters/test_cluster', expect_errors=True)
        self.assertEqual(409, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['errors'])


class TestClusterPolicyEnforcement(api_base.FunctionalTest):
    def setUp(self):
        super(TestClusterPolicyEnforcement, self).setUp()
        obj_utils.create_test_cluster_template(self.context)

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: "project:non_fake"})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "cluster:get_all", self.get_json, '/clusters', expect_errors=True)

    def test_policy_disallow_get_one(self):
        self.cluster = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "cluster:get", self.get_json, '/clusters/%s' % self.cluster.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "cluster:detail", self.get_json,
            '/clusters/%s/detail' % uuidutils.generate_uuid(),
            expect_errors=True)

    def test_policy_disallow_update(self):
        self.cluster = obj_utils.create_test_cluster(self.context,
                                                     name='cluster_example_A',
                                                     node_count=3)
        self._common_policy_check(
            "cluster:update", self.patch_json, '/clusters/%s' %
                                               self.cluster.name,
            [{'path': '/name', 'value': "new_name", 'op': 'replace'}],
            expect_errors=True)

    def test_policy_disallow_create(self):
        bdict = apiutils.cluster_post_data(name='cluster_example_A')
        self._common_policy_check(
            "cluster:create", self.post_json, '/clusters', bdict,
            expect_errors=True)

    def _simulate_cluster_delete(self, cluster_uuid):
        cluster = objects.Cluster.get_by_uuid(self.context, cluster_uuid)
        cluster.destroy()

    def test_policy_disallow_delete(self):
        p = mock.patch.object(rpcapi.API, 'cluster_delete')
        self.mock_cluster_delete = p.start()
        self.mock_cluster_delete.side_effect = self._simulate_cluster_delete
        self.addCleanup(p.stop)
        self.cluster = obj_utils.create_test_cluster(self.context)
        self._common_policy_check(
            "cluster:delete", self.delete, '/clusters/%s' %
                                           self.cluster.uuid,
            expect_errors=True)

    def _owner_check(self, rule, func, *args, **kwargs):
        self.policy.set_rules({rule: "user_id:%(user_id)s"})
        response = func(*args, **kwargs)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            response.json['errors'][0]['detail'])

    def test_policy_only_owner_get_one(self):
        cluster = obj_utils.create_test_cluster(self.context,
                                                user_id='another')
        self._owner_check("cluster:get", self.get_json,
                          '/clusters/%s' % cluster.uuid,
                          expect_errors=True)

    def test_policy_only_owner_update(self):
        cluster = obj_utils.create_test_cluster(self.context,
                                                user_id='another')
        self._owner_check(
            "cluster:update", self.patch_json,
            '/clusters/%s' % cluster.uuid,
            [{'path': '/name', 'value': "new_name", 'op': 'replace'}],
            expect_errors=True)

    def test_policy_only_owner_delete(self):
        cluster = obj_utils.create_test_cluster(self.context,
                                                user_id='another')
        self._owner_check("cluster:delete", self.delete,
                          '/clusters/%s' % cluster.uuid,
                          expect_errors=True)
