# Copyright 2015 Hewlett-Packard Development Company, L.P.
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

import mock
from mock import patch
from oslo_config import cfg
from oslo_service import loopingcall

from magnum.conductor.handlers import bay_conductor
from magnum import objects
from magnum.objects.fields import BayStatus as bay_status
from magnum.tests import base


class TestBayConductorWithSwarm(base.TestCase):
    def setUp(self):
        super(TestBayConductorWithSwarm, self).setUp()
        self.baymodel_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'docker_volume_size': 20,
            'external_network_id': 'external_network_id',
            'cluster_distro': 'fedora-atomic',
            'coe': 'swarm',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'tls_disabled': False,
            'server_type': 'vm',
            'network_driver': 'network_driver',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_use_vxlan': 'yes'}
        }
        self.bay_dict = {
            'id': 1,
            'uuid': 'some_uuid',
            'baymodel_id': 'xx-xx-xx-xx',
            'name': 'bay1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'node_addresses': ['172.17.2.4'],
            'master_count': 1,
            'node_count': 1,
            'discovery_url': 'https://discovery.test.io/123456789',
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de'
        }
        cfg.CONF.set_override('trustee_domain_id',
                              '3527620c-b220-4f37-9ebc-6e63a81a9b2f',
                              group='trust')
        osc_patcher = mock.patch('magnum.common.clients.OpenStackClients')
        self.mock_osc_class = osc_patcher.start()
        self.addCleanup(osc_patcher.stop)
        self.mock_osc = mock.MagicMock()
        self.mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        self.mock_osc_class.return_value = self.mock_osc
        mock_stack = self.mock_osc.heat.return_value.stacks.get.return_value
        mock_stack.parameters = {'user_token': 'fake_token'}
        self.context.auth_url = 'http://192.168.10.10:5000/v3'

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_all_values(
            self,
            mock_objects_baymodel_get_by_uuid):
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'node_flavor': 'flavor_id',
            'number_of_masters': 1,
            'number_of_nodes': 1,
            'docker_volume_size': 20,
            'discovery_url': 'https://discovery.test.io/123456789',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'user_token': 'fake_token',
            'bay_uuid': 'some_uuid',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'network_driver': 'network_driver',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
            'trustee_domain_id': '3527620c-b220-4f37-9ebc-6e63a81a9b2f',
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3'
        }
        self.assertEqual(expected, definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_only_required(
            self,
            mock_objects_baymodel_get_by_uuid):

        not_required = ['image_id', 'flavor_id', 'dns_nameserver',
                        'docker_volume_size', 'fixed_network', 'http_proxy',
                        'https_proxy', 'no_proxy', 'network_driver',
                        'master_flavor_id']
        for key in not_required:
            self.baymodel_dict[key] = None
        self.bay_dict['discovery_url'] = 'https://discovery.etcd.io/test'

        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'number_of_masters': 1,
            'number_of_nodes': 1,
            'discovery_url': 'https://discovery.etcd.io/test',
            'user_token': 'fake_token',
            'bay_uuid': 'some_uuid',
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'flannel_network_cidr': u'10.101.0.0/16',
            'flannel_network_subnetlen': u'26',
            'flannel_use_vxlan': u'yes',
            'trustee_domain_id': '3527620c-b220-4f37-9ebc-6e63a81a9b2f',
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3'
        }
        self.assertEqual(expected, definition)

    @patch('magnum.conductor.utils.retrieve_baymodel')
    @patch('oslo_config.cfg')
    @patch('magnum.common.clients.OpenStackClients')
    def setup_poll_test(self, mock_openstack_client, cfg,
                        mock_retrieve_baymodel):
        cfg.CONF.bay_heat.max_attempts = 10
        bay = mock.MagicMock()
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_retrieve_baymodel.return_value = baymodel
        poller = bay_conductor.HeatPoller(mock_openstack_client, bay)
        return (mock_heat_stack, bay, poller)

    def test_poll_node_count(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_nodes': 1}
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(1, bay.node_count)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_nodes': 2}
        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, bay.node_count)
