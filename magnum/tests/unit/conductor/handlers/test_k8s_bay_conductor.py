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
from magnum.conductor.handlers import bay_conductor
from magnum import objects
from magnum.tests import base

import mock
from mock import patch
from oslo_config import cfg


class TestBayConductorWithK8s(base.TestCase):
    def setUp(self):
        super(TestBayConductorWithK8s, self).setUp()
        self.baymodel_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
            'fixed_network': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'cluster_distro': 'fedora-atomic',
            'ssh_authorized_key': 'ssh_authorized_key',
            'coe': 'kubernetes',
            'token': None,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_use_vxlan': 'yes'},
            'tls_disabled': False,
            'server_type': 'vm'
        }
        self.bay_dict = {
            'uuid': 'bay-xx-xx-xx-xx',
            'baymodel_id': 'xx-xx-xx-xx',
            'name': 'bay1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'node_addresses': ['172.17.2.4'],
            'node_count': 1,
            'master_count': 1,
            'discovery_url': 'https://discovery.etcd.io/test',
            'master_addresses': ['172.17.2.18'],
            'ca_cert_ref': 'http://barbican/v1/containers/xx-xx-xx-xx',
            'magnum_cert_ref': 'http://barbican/v1/containers/xx-xx-xx-xx',
        }
        self.context.auth_url = 'http://192.168.10.10:5000/v3'
        self.context.user_name = 'fake_user'
        self.context.tenant = 'fake_tenant'
        osc_patcher = mock.patch('magnum.common.clients.OpenStackClients')
        self.mock_osc_class = osc_patcher.start()
        self.addCleanup(osc_patcher.stop)
        self.mock_osc = mock.MagicMock()
        self.mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        self.mock_osc_class.return_value = self.mock_osc
        mock_stack = self.mock_osc.heat.return_value.stacks.get.return_value
        mock_stack.parameters = {'user_token': 'fake_token'}

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid)

    def _test_extract_template_definition(
            self,
            mock_objects_baymodel_get_by_uuid,
            missing_attr=None):
        if missing_attr in self.baymodel_dict:
            self.baymodel_dict[missing_attr] = None
        elif missing_attr in self.bay_dict:
            self.bay_dict[missing_attr] = None
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay = objects.Bay(self.context, **self.bay_dict)

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        mapping = {
            'dns_nameserver': 'dns_nameserver',
            'image_id': 'server_image',
            'flavor_id': 'minion_flavor',
            'docker_volume_size': 'docker_volume_size',
            'fixed_network': 'fixed_network_cidr',
            'network_driver': 'network_driver',
            'master_flavor_id': 'master_flavor',
            'apiserver_port': '',
            'node_count': 'number_of_minions',
            'master_count': 'number_of_masters',
            'discovery_url': 'discovery_url',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_use_vxlan': 'yes'},
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'user_token': self.context.auth_token,
            'bay_uuid': self.bay_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
        }
        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'network_driver': 'network_driver',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'docker_volume_size': 20,
            'discovery_url': 'https://discovery.etcd.io/test',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'auth_url': 'http://192.168.10.10:5000/v2',
            'tenant_name': 'fake_tenant',
            'username': 'fake_user',
            'user_token': 'fake_token',
            'bay_uuid': self.bay_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
        }
        if missing_attr is not None:
            expected.pop(mapping[missing_attr], None)

        self.assertEqual(expected, definition)

    @patch('requests.get')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_coreos_with_disovery(
            self,
            mock_objects_baymodel_get_by_uuid,
            reqget):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['cluster_distro'] = 'coreos'
        cfg.CONF.set_override('coreos_discovery_token_url',
                              'http://tokentest',
                              group='bay')
        mock_req = mock.MagicMock(text='/h1/h2/h3')
        reqget.return_value = mock_req
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
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'ssh_authorized_key': 'ssh_authorized_key',
            'token': 'h3',
            'discovery_url': 'https://discovery.etcd.io/test',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
            'auth_url': 'http://192.168.10.10:5000/v2',
            'tenant_name': 'fake_tenant',
            'username': 'fake_user',
            'user_token': 'fake_token',
            'bay_uuid': self.bay_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
        }
        self.assertEqual(expected, definition)

    @patch('uuid.uuid4')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_coreos_no_discoveryurl(
            self,
            mock_objects_baymodel_get_by_uuid,
            mock_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['cluster_distro'] = 'coreos'
        cfg.CONF.set_override('coreos_discovery_token_url',
                              None,
                              group='bay')
        mock_uuid.return_value = mock.MagicMock(
            hex='ba3d1866282848ddbedc76112110c208')
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
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'ssh_authorized_key': 'ssh_authorized_key',
            'token': 'ba3d1866282848ddbedc76112110c208',
            'discovery_url': 'https://discovery.etcd.io/test',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
            'auth_url': 'http://192.168.10.10:5000/v2',
            'tenant_name': 'fake_tenant',
            'username': 'fake_user',
            'user_token': 'fake_token',
            'bay_uuid': self.bay_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
        }
        self.assertEqual(expected, definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_dns(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='dns_nameserver')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_server_image(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='image_id')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_minion_flavor(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='flavor_id')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_docker_volume_size(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='docker_volume_size')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_fixed_network(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='fixed_network')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_master_flavor(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='master_flavor_id')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_ssh_authorized_key(
            self,
            mock_objects_baymodel_get_by_uuid):
        baymodel_dict = self.baymodel_dict
        baymodel_dict['cluster_distro'] = 'coreos'
        baymodel_dict['ssh_authorized_key'] = None
        baymodel = objects.BayModel(self.context, **baymodel_dict)
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
            'minion_flavor': 'flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'discovery_url': 'https://discovery.etcd.io/test',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
            'auth_url': 'http://192.168.10.10:5000/v2',
            'tenant_name': 'fake_tenant',
            'username': 'fake_user',
            'user_token': 'fake_token',
            'bay_uuid': self.bay_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
        }
        self.assertIn('token', definition)
        del definition['token']
        self.assertEqual(expected, definition)

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_apiserver_port(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='apiserver_port')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_node_count(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='node_count')

    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_master_count(
            self,
            mock_objects_baymodel_get_by_uuid):
        self._test_extract_template_definition(
            mock_objects_baymodel_get_by_uuid,
            missing_attr='master_count')

    @patch('requests.get')
    @patch('magnum.objects.BayModel.get_by_uuid')
    def test_extract_template_definition_without_discovery_url(
            self,
            mock_objects_baymodel_get_by_uuid,
            reqget):
        baymodel = objects.BayModel(self.context, **self.baymodel_dict)
        mock_objects_baymodel_get_by_uuid.return_value = baymodel
        bay_dict = self.bay_dict
        bay_dict['discovery_url'] = None
        bay = objects.Bay(self.context, **bay_dict)

        cfg.CONF.set_override('etcd_discovery_service_endpoint_format',
                              'http://etcd/test?size=%(size)d',
                              group='bay')
        mock_req = mock.MagicMock(text='https://address/token')
        reqget.return_value = mock_req

        (template_path,
         definition) = bay_conductor._extract_template_definition(self.context,
                                                                  bay)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'minion_flavor': 'flavor_id',
            'number_of_minions': '1',
            'number_of_masters': '1',
            'fixed_network_cidr': '10.20.30.0/24',
            'network_driver': 'network_driver',
            'docker_volume_size': 20,
            'discovery_url': 'https://address/token',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_use_vxlan': 'yes',
            'auth_url': 'http://192.168.10.10:5000/v2',
            'tenant_name': 'fake_tenant',
            'username': 'fake_user',
            'user_token': 'fake_token',
            'bay_uuid': self.bay_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
        }
        self.assertEqual(expected, definition)
        reqget.assert_called_once_with('http://etcd/test?size=1')

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_conductor'
           '._extract_template_definition')
    def test_create_stack(self,
                          mock_extract_template_definition,
                          mock_get_template_contents,
                          mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []
        dummy_bay_name = 'expected_stack_name'
        expected_timeout = 15

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {})
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.name = dummy_bay_name

        bay_conductor._create_stack(self.context, mock_osc,
                                    mock_bay, expected_timeout)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files),
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_conductor'
           '._extract_template_definition')
    def test_create_stack_no_timeout_specified(
            self,
            mock_extract_template_definition,
            mock_get_template_contents,
            mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []
        dummy_bay_name = 'expected_stack_name'
        expected_timeout = cfg.CONF.bay_heat.bay_create_timeout

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {})
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.name = dummy_bay_name

        bay_conductor._create_stack(self.context, mock_osc,
                                    mock_bay, None)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files),
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_conductor'
           '._extract_template_definition')
    def test_create_stack_timeout_is_zero(
            self,
            mock_extract_template_definition,
            mock_get_template_contents,
            mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []
        dummy_bay_name = 'expected_stack_name'
        bay_timeout = 0
        expected_timeout = None

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {})
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.name = dummy_bay_name

        bay_conductor._create_stack(self.context, mock_osc,
                                    mock_bay, bay_timeout)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files),
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.bay_conductor'
           '._extract_template_definition')
    def test_update_stack(self,
                          mock_extract_template_definition,
                          mock_get_template_contents):

        mock_stack_id = 'xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        exptected_files = []

        mock_tpl_files = mock.MagicMock()
        mock_tpl_files.items.return_value = exptected_files
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {})
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_bay = mock.MagicMock()
        mock_bay.stack_id = mock_stack_id

        bay_conductor._update_stack({}, mock_osc, mock_bay)

        expected_args = {
            'parameters': {},
            'template': expected_template_contents,
            'files': dict(exptected_files)
        }
        mock_heat_client.stacks.update.assert_called_once_with(mock_stack_id,
                                                               **expected_args)
