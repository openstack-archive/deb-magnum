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
from oslo_policy import policy
from oslo_utils import timeutils
from six.moves.urllib import parse as urlparse
from wsme import types as wtypes

from magnum.api.controllers.v1 import node as api_node
from magnum.common import utils
from magnum.tests import base
from magnum.tests.unit.api import base as api_base
from magnum.tests.unit.api import utils as apiutils
from magnum.tests.unit.objects import utils as obj_utils


class TestNodeObject(base.TestCase):

    def test_node_init(self):
        node_dict = apiutils.node_post_data()
        del node_dict['image_id']
        node = api_node.Node(**node_dict)
        self.assertEqual(wtypes.Unset, node.image_id)


class TestListNode(api_base.FunctionalTest):

    def test_empty(self):
        response = self.get_json('/nodes')
        self.assertEqual([], response['nodes'])

    def _assert_node_fields(self, node):
        node_fields = ['type', 'image_id', 'ironic_node_id']
        for field in node_fields:
            self.assertIn(field, node)

    def test_one(self):
        node = obj_utils.create_test_node(self.context)
        response = self.get_json('/nodes')
        self.assertEqual(node.uuid, response['nodes'][0]["uuid"])
        self._assert_node_fields(response['nodes'][0])

    def test_get_one(self):
        node = obj_utils.create_test_node(self.context)
        response = self.get_json('/nodes/%s' % node['uuid'])
        self.assertEqual(node.uuid, response['uuid'])
        self._assert_node_fields(response)

    def test_get_all_with_pagination_marker(self):
        node_list = []
        for id_ in range(4):
            node = obj_utils.create_test_node(self.context, id=id_,
                                              uuid=utils.generate_uuid())
            node_list.append(node.uuid)

        response = self.get_json('/nodes?limit=3&marker=%s' % node_list[2])
        self.assertEqual(1, len(response['nodes']))
        self.assertEqual(node_list[-1], response['nodes'][0]['uuid'])

    def test_detail(self):
        node = obj_utils.create_test_node(self.context)
        response = self.get_json('/nodes/detail')
        self.assertEqual(node.uuid, response['nodes'][0]["uuid"])
        self._assert_node_fields(response['nodes'][0])

    def test_detail_with_pagination_marker(self):
        node_list = []
        for id_ in range(4):
            node = obj_utils.create_test_node(self.context, id=id_,
                                              uuid=utils.generate_uuid())
            node_list.append(node.uuid)

        response = self.get_json('/nodes/detail?limit=3&marker=%s'
                                 % node_list[2])
        self.assertEqual(1, len(response['nodes']))
        self.assertEqual(node_list[-1], response['nodes'][0]['uuid'])
        self._assert_node_fields(response['nodes'][0])

    def test_detail_against_single(self):
        node = obj_utils.create_test_node(self.context)
        response = self.get_json('/nodes/%s/detail' % node['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        node_list = []
        for id_ in range(5):
            node = obj_utils.create_test_node(self.context, id=id_,
                                              uuid=utils.generate_uuid())
            node_list.append(node.uuid)
        response = self.get_json('/nodes')
        self.assertEqual(len(node_list), len(response['nodes']))
        uuids = [s['uuid'] for s in response['nodes']]
        self.assertEqual(sorted(node_list), sorted(uuids))

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_node(self.context, id=1, uuid=uuid)
        response = self.get_json('/nodes/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_node(self.context, id=id_,
                                       uuid=utils.generate_uuid())
        response = self.get_json('/nodes/?limit=3')
        self.assertEqual(3, len(response['nodes']))

        next_marker = response['nodes'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_node(self.context, id=id_,
                                       uuid=utils.generate_uuid())
        response = self.get_json('/nodes')
        self.assertEqual(3, len(response['nodes']))

        next_marker = response['nodes'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.node = obj_utils.create_test_node(self.context, image_id='Fedora')

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        new_image = 'Ubuntu'
        response = self.get_json('/nodes/%s' % self.node.uuid)
        self.assertNotEqual(new_image, response['image_id'])

        response = self.patch_json('/nodes/%s' % self.node.uuid,
                                   [{'path': '/image_id', 'value': new_image,
                                     'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/nodes/%s' % self.node.uuid)
        self.assertEqual(new_image, response['image_id'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    def test_replace_non_existent_node(self):
        response = self.patch_json('/nodes/%s' % utils.generate_uuid(),
                                   [{'path': '/image_id', 'value': 'Ubuntu',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/nodes/%s' % self.node.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_ok(self):
        response = self.get_json('/nodes/%s' % self.node.uuid)
        self.assertIsNotNone(response['image_id'])

        response = self.patch_json('/nodes/%s' % self.node.uuid,
                                   [{'path': '/image_id', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/nodes/%s' % self.node.uuid)
        self.assertIsNone(response['image_id'])

    def test_remove_uuid(self):
        response = self.patch_json('/nodes/%s' % self.node.uuid,
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/nodes/%s' % self.node.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPost(api_base.FunctionalTest):

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_node(self, mock_utcnow):
        node_dict = apiutils.node_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/nodes', node_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/nodes/%s' % node_dict['uuid']
        self.assertEqual(expected_location,
                         urlparse.urlparse(response.location).path)
        self.assertEqual(node_dict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    def test_create_node_set_project_id_and_user_id(self):
        with mock.patch.object(self.dbapi, 'create_node',
                               wraps=self.dbapi.create_node) as cc_mock:
            node_dict = apiutils.node_post_data()
            self.post_json('/nodes', node_dict)
            cc_mock.assert_called_once_with(mock.ANY)
            self.assertEqual(self.context.project_id,
                             cc_mock.call_args[0][0]['project_id'])
            self.assertEqual(self.context.user_id,
                             cc_mock.call_args[0][0]['user_id'])

    def test_create_node_doesnt_contain_id(self):
        with mock.patch.object(self.dbapi, 'create_node',
                               wraps=self.dbapi.create_node) as cn_mock:
            node_dict = apiutils.node_post_data(image_id='Ubuntu')
            response = self.post_json('/nodes', node_dict)
            self.assertEqual(node_dict['image_id'], response.json['image_id'])
            cn_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cn_mock.call_args[0][0])

    def test_create_node_generate_uuid(self):
        node_dict = apiutils.node_post_data()
        del node_dict['uuid']

        response = self.post_json('/nodes', node_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(node_dict['image_id'],
                         response.json['image_id'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        self.node = obj_utils.create_test_node(self.context, image_id='Fedora')

    def test_delete_node(self):
        self.delete('/nodes/%s' % self.node.uuid)
        response = self.get_json('/nodes/%s' % self.node.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_node_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/nodes/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestNodePolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({rule: "project:non_fake"})
        exc = self.assertRaises(policy.PolicyNotAuthorized,
                                func, *arg, **kwarg)
        self.assertTrue(exc.message.startswith(rule))
        self.assertTrue(exc.message.endswith("disallowed by policy"))

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "node:get_all", self.get_json, '/nodes')

    def test_policy_disallow_get_one(self):
        self._common_policy_check(
            "node:get", self.get_json, '/nodes/111-222-333')

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "node:detail", self.get_json, '/nodes/111-222-333/detail')

    def test_policy_disallow_update(self):
        node = obj_utils.create_test_node(self.context,
                                          type='type_A',
                                          uuid="333-444-5555")
        self._common_policy_check(
            "node:update", self.patch_json,
            '/nodes/%s' % node.uuid,
            [{'type': '/type', 'value': "new_type", 'op': 'replace'}])

    def test_policy_disallow_create(self):
        bdict = apiutils.node_post_data(name='node_example_A')
        self._common_policy_check(
            "node:create", self.post_json, '/nodes', bdict)

    def test_policy_disallow_delete(self):
        node = obj_utils.create_test_node(self.context,
                                          uuid='137-246-789')
        self._common_policy_check(
            "node:delete", self.delete,
            '/nodes/%s' % node.uuid)
