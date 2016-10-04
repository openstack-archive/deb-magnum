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

from magnum.conductor.handlers import cluster_conductor
from magnum import objects
from magnum.tests import base


class TestClusterConductorWithK8s(base.TestCase):
    def setUp(self):
        super(TestClusterConductorWithK8s, self).setUp()
        self.cluster_template_dict = {
            'image_id': 'image_id',
            'flavor_id': 'flavor_id',
            'master_flavor_id': 'master_flavor_id',
            'keypair_id': 'keypair_id',
            'dns_nameserver': 'dns_nameserver',
            'external_network_id': 'external_network_id',
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'docker_volume_size': 20,
            'docker_storage_driver': 'devicemapper',
            'cluster_distro': 'fedora-atomic',
            'coe': 'kubernetes',
            'token': None,
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_backend': 'vxlan'},
            'tls_disabled': False,
            'server_type': 'vm',
            'registry_enabled': False,
            'insecure_registry': '10.0.0.1:5000',
            'master_lb_enabled': False,
            'floating_ip_enabled': False,
        }
        self.cluster_dict = {
            'uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'cluster_template_id': 'xx-xx-xx-xx',
            'name': 'cluster1',
            'stack_id': 'xx-xx-xx-xx',
            'api_address': '172.17.2.3',
            'node_addresses': ['172.17.2.4'],
            'node_count': 1,
            'master_count': 1,
            'discovery_url': 'https://discovery.etcd.io/test',
            'master_addresses': ['172.17.2.18'],
            'ca_cert_ref': 'http://barbican/v1/containers/xx-xx-xx-xx',
            'magnum_cert_ref': 'http://barbican/v1/containers/xx-xx-xx-xx',
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'coe_version': 'fake-version',
        }
        self.context.auth_url = 'http://192.168.10.10:5000/v3'
        self.context.user_name = 'fake_user'
        self.context.tenant = 'fake_tenant'
        osc_patcher = mock.patch('magnum.common.clients.OpenStackClients')
        self.mock_osc_class = osc_patcher.start()
        self.addCleanup(osc_patcher.stop)
        self.mock_osc = mock.MagicMock()
        self.mock_osc.magnum_url.return_value = 'http://127.0.0.1:9511/v1'
        self.mock_osc.cinder_region_name.return_value = 'RegionOne'
        self.mock_keystone = mock.MagicMock()
        self.mock_keystone.trustee_domain_id = 'trustee_domain_id'
        self.mock_osc.keystone.return_value = self.mock_keystone
        self.mock_osc_class.return_value = self.mock_osc

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid, mock_get)

    def _test_extract_template_definition(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr=None):
        if missing_attr in self.cluster_template_dict:
            self.cluster_template_dict[missing_attr] = None
        elif missing_attr in self.cluster_dict:
            self.cluster_dict[missing_attr] = None
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        (template_path,
         definition,
         env_files) = cluster_conductor._extract_template_definition(
            self.context, cluster)

        mapping = {
            'dns_nameserver': 'dns_nameserver',
            'image_id': 'server_image',
            'flavor_id': 'minion_flavor',
            'docker_volume_size': 'docker_volume_size',
            'docker_storage_driver': 'docker_storage_driver',
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'master_flavor_id': 'master_flavor',
            'apiserver_port': '',
            'node_count': 'number_of_minions',
            'master_count': 'number_of_masters',
            'discovery_url': 'discovery_url',
            'labels': {'flannel_network_cidr': '10.101.0.0/16',
                       'flannel_network_subnetlen': '26',
                       'flannel_backend': 'vxlan'},
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'tls_disabled': False,
            'insecure_registry': '10.0.0.1:5000',
        }
        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': 1,
            'number_of_masters': 1,
            'docker_volume_size': 20,
            'docker_storage_driver': 'devicemapper',
            'discovery_url': 'https://discovery.etcd.io/test',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'tenant_name': 'fake_tenant',
            'username': 'fake_user',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'tls_disabled': False,
            'registry_enabled': False,
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
        }
        if missing_attr is not None:
            expected.pop(mapping[missing_attr], None)

        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml'],
            env_files)

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_with_registry(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self.cluster_template_dict['registry_enabled'] = True
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        cfg.CONF.set_override('swift_region',
                              'RegionOne',
                              group='docker_registry')

        (template_path,
         definition,
         env_files) = cluster_conductor._extract_template_definition(
            self.context, cluster)

        expected = {
            'auth_url': 'http://192.168.10.10:5000/v3',
            'cluster_uuid': '5d12f6fd-a196-4bf0-ae4c-1f639a523a52',
            'discovery_url': 'https://discovery.etcd.io/test',
            'dns_nameserver': 'dns_nameserver',
            'docker_storage_driver': 'devicemapper',
            'docker_volume_size': 20,
            'external_network': 'external_network_id',
            'flannel_backend': 'vxlan',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'magnum_url': 'http://127.0.0.1:9511/v1',
            'master_flavor': 'master_flavor_id',
            'minion_flavor': 'flavor_id',
            'network_driver': 'network_driver',
            'no_proxy': 'no_proxy',
            'number_of_masters': 1,
            'number_of_minions': 1,
            'region_name': 'RegionOne',
            'registry_container': 'docker_registry',
            'registry_enabled': True,
            'server_image': 'image_id',
            'ssh_key_name': 'keypair_id',
            'swift_region': 'RegionOne',
            'tenant_name': 'fake_tenant',
            'tls_disabled': False,
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trustee_username': 'fake_trustee',
            'username': 'fake_user',
            'volume_driver': 'volume_driver',
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
        }

        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml'],
            env_files)

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_coreos_with_disovery(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self.cluster_template_dict['cluster_distro'] = 'coreos'
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        expected_result = str('{"action":"get","node":{"key":"test","value":'
                              '"1","modifiedIndex":10,"createdIndex":10}}')
        mock_resp = mock.MagicMock()
        mock_resp.text = expected_result
        mock_get.return_value = mock_resp
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        (template_path,
         definition,
         env_files) = cluster_conductor._extract_template_definition(
            self.context, cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': 1,
            'number_of_masters': 1,
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'discovery_url': 'https://discovery.etcd.io/test',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'tls_disabled': False,
            'registry_enabled': False,
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_master_lb.yaml'],
            env_files)

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_coreos_no_discoveryurl(
            self,
            mock_objects_cluster_template_get_by_uuid,
            reqget):
        self.cluster_template_dict['cluster_distro'] = 'coreos'
        self.cluster_dict['discovery_url'] = None
        mock_req = mock.MagicMock(text='http://tokentest/h1/h2/h3')
        reqget.return_value = mock_req
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        cluster = objects.Cluster(self.context, **self.cluster_dict)

        (template_path,
         definition,
         env_files) = cluster_conductor._extract_template_definition(
            self.context, cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'minion_flavor': 'flavor_id',
            'master_flavor': 'master_flavor_id',
            'number_of_minions': 1,
            'number_of_masters': 1,
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'discovery_url': 'http://tokentest/h1/h2/h3',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'tls_disabled': False,
            'registry_enabled': False,
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_master_lb.yaml'],
            env_files)

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_dns(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='dns_nameserver')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_server_image(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='image_id')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_minion_flavor(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='flavor_id')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_docker_volume_size(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='docker_volume_size')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_docker_storage_driver(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='docker_storage_driver')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_master_flavor(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='master_flavor_id')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_apiserver_port(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='apiserver_port')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_node_count(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='node_count')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_master_count(
            self,
            mock_objects_cluster_template_get_by_uuid,
            mock_get):
        self._test_extract_template_definition(
            mock_objects_cluster_template_get_by_uuid,
            mock_get,
            missing_attr='master_count')

    @patch('requests.get')
    @patch('magnum.objects.ClusterTemplate.get_by_uuid')
    def test_extract_template_definition_without_discovery_url(
            self,
            mock_objects_cluster_template_get_by_uuid,
            reqget):
        cluster_template = objects.ClusterTemplate(
            self.context, **self.cluster_template_dict)
        mock_objects_cluster_template_get_by_uuid.return_value = \
            cluster_template
        cluster_dict = self.cluster_dict
        cluster_dict['discovery_url'] = None
        cluster = objects.Cluster(self.context, **cluster_dict)

        cfg.CONF.set_override('etcd_discovery_service_endpoint_format',
                              'http://etcd/test?size=%(size)d',
                              group='cluster')
        mock_req = mock.MagicMock(text='https://address/token')
        reqget.return_value = mock_req

        (template_path,
         definition,
         env_files) = cluster_conductor._extract_template_definition(
            self.context, cluster)

        expected = {
            'ssh_key_name': 'keypair_id',
            'external_network': 'external_network_id',
            'dns_nameserver': 'dns_nameserver',
            'server_image': 'image_id',
            'master_flavor': 'master_flavor_id',
            'minion_flavor': 'flavor_id',
            'number_of_minions': 1,
            'number_of_masters': 1,
            'network_driver': 'network_driver',
            'volume_driver': 'volume_driver',
            'docker_volume_size': 20,
            'docker_storage_driver': 'devicemapper',
            'discovery_url': 'https://address/token',
            'http_proxy': 'http_proxy',
            'https_proxy': 'https_proxy',
            'no_proxy': 'no_proxy',
            'flannel_network_cidr': '10.101.0.0/16',
            'flannel_network_subnetlen': '26',
            'flannel_backend': 'vxlan',
            'tenant_name': 'fake_tenant',
            'username': 'fake_user',
            'cluster_uuid': self.cluster_dict['uuid'],
            'magnum_url': self.mock_osc.magnum_url.return_value,
            'region_name': self.mock_osc.cinder_region_name.return_value,
            'tls_disabled': False,
            'registry_enabled': False,
            'trustee_domain_id': self.mock_keystone.trustee_domain_id,
            'trustee_username': 'fake_trustee',
            'trustee_password': 'fake_trustee_password',
            'trustee_user_id': '7b489f04-b458-4541-8179-6a48a553e656',
            'trust_id': 'bd11efc5-d4e2-4dac-bbce-25e348ddf7de',
            'auth_url': 'http://192.168.10.10:5000/v3',
            'insecure_registry_url': '10.0.0.1:5000',
            'kube_version': 'fake-version',
        }
        self.assertEqual(expected, definition)
        self.assertEqual(
            ['../../common/templates/environments/no_master_lb.yaml',
             '../../common/templates/environments/disable_floating_ip.yaml'],
            env_files)
        reqget.assert_called_once_with('http://etcd/test?size=1')

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.cluster_conductor'
           '._extract_template_definition')
    def test_create_stack(self,
                          mock_extract_template_definition,
                          mock_get_template_contents,
                          mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        dummy_cluster_name = 'expected_stack_name'
        expected_timeout = 15

        mock_tpl_files = {}
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {}, [])
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_cluster = mock.MagicMock()
        mock_cluster.name = dummy_cluster_name

        cluster_conductor._create_stack(self.context, mock_osc,
                                        mock_cluster, expected_timeout)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': {},
            'environment_files': [],
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.cluster_conductor'
           '._extract_template_definition')
    def test_create_stack_no_timeout_specified(
            self,
            mock_extract_template_definition,
            mock_get_template_contents,
            mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        dummy_cluster_name = 'expected_stack_name'
        expected_timeout = cfg.CONF.cluster_heat.create_timeout

        mock_tpl_files = {}
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {}, [])
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_cluster = mock.MagicMock()
        mock_cluster.name = dummy_cluster_name

        cluster_conductor._create_stack(self.context, mock_osc,
                                        mock_cluster, None)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': {},
            'environment_files': [],
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('magnum.common.short_id.generate_id')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.cluster_conductor'
           '._extract_template_definition')
    def test_create_stack_timeout_is_zero(
            self,
            mock_extract_template_definition,
            mock_get_template_contents,
            mock_generate_id):

        mock_generate_id.return_value = 'xx-xx-xx-xx'
        expected_stack_name = 'expected_stack_name-xx-xx-xx-xx'
        expected_template_contents = 'template_contents'
        dummy_cluster_name = 'expected_stack_name'
        cluster_timeout = 0
        expected_timeout = cfg.CONF.cluster_heat.create_timeout

        mock_tpl_files = {}
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {}, [])
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_cluster = mock.MagicMock()
        mock_cluster.name = dummy_cluster_name

        cluster_conductor._create_stack(self.context, mock_osc,
                                        mock_cluster, cluster_timeout)

        expected_args = {
            'stack_name': expected_stack_name,
            'parameters': {},
            'template': expected_template_contents,
            'files': {},
            'environment_files': [],
            'timeout_mins': expected_timeout
        }
        mock_heat_client.stacks.create.assert_called_once_with(**expected_args)

    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.cluster_conductor'
           '._extract_template_definition')
    def test_update_stack(self,
                          mock_extract_template_definition,
                          mock_get_template_contents):

        mock_stack_id = 'xx-xx-xx-xx'
        expected_template_contents = 'template_contents'

        mock_tpl_files = {}
        mock_get_template_contents.return_value = [
            mock_tpl_files, expected_template_contents]
        mock_extract_template_definition.return_value = ('template/path',
                                                         {}, [])
        mock_heat_client = mock.MagicMock()
        mock_osc = mock.MagicMock()
        mock_osc.heat.return_value = mock_heat_client
        mock_cluster = mock.MagicMock()
        mock_cluster.stack_id = mock_stack_id

        cluster_conductor._update_stack({}, mock_osc, mock_cluster)

        expected_args = {
            'parameters': {},
            'template': expected_template_contents,
            'files': {},
            'environment_files': [],
            'disable_rollback': True
        }
        mock_heat_client.stacks.update.assert_called_once_with(mock_stack_id,
                                                               **expected_args)
