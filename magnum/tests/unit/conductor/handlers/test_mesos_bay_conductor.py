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
from oslo_service import loopingcall

from magnum.conductor.handlers import bay_conductor
from magnum import objects
from magnum.objects.fields import BayStatus as bay_status
from magnum.tests import base

import mock
from mock import patch


class TestBayConductorWithMesos(base.TestCase):
    def setUp(self):
        super(TestBayConductorWithMesos, self).setUp()
        self.baymodel_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
            'fixed_network': '10.2.0.0/22',
            'cluster_distro': 'ubuntu',
            'coe': 'mesos',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'server_type': 'vm'
        }
        self.bay_dict = {
            'id': 1,
            'uuid': 'some_uuid',
            'baymodel_id': 'xx-xx-xx-xx',
            'name': 'bay1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'node_addresses': ['172.17.2.4'],
            'node_count': 1,
        }

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
            'slave_flavor': 'flavor_id',
            'number_of_slaves': '1',
            'fixed_network_cidr': '10.2.0.0/22',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy'
        }
        self.assertEqual(expected, definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_only_required(
            self,
            mock_objects_baymodel_get_by_uuid):
        not_required = ['image_id', 'master_flavor_id', 'flavor_id',
                        'dns_nameserver', 'fixed_network', 'http_proxy',
                        'https_proxy', 'no_proxy']
        for key in not_required:
            self.baymodel_dict[key] = None

        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'number_of_slaves': '1',
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

        mock_heat_stack.parameters = {'number_of_slaves': 1}
        mock_heat_stack.stack_status = bay_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(1, bay.node_count)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, bay, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_slaves': 2}
        mock_heat_stack.stack_status = bay_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, bay.node_count)
