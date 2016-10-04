# Copyright 2015 Huawei Technologies Co.,LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
from oslo_config import cfg
from six.moves import reload_module

from magnum.api import validation as v
from magnum.common import exception
from magnum import objects
from magnum.tests import base
from magnum.tests.unit.objects import utils as obj_utils


class TestValidation(base.BaseTestCase):

    def _test_enforce_cluster_types(
            self,
            mock_cluster_get_by_uuid,
            mock_pecan_request,
            cluster_type,
            allowed_cluster_types,
            assert_raised=False,
            *args):

        @v.enforce_cluster_types(*allowed_cluster_types)
        def test(self, *args):
            if hasattr(args[0], 'cluster_uuid'):
                return args[0].name
            else:
                return args[1]

        context = mock_pecan_request.context
        cluster = mock.MagicMock()
        cluster.cluster_template_id = 'cluster_template_id'
        cluster_template = obj_utils.get_test_cluster_template(
            context, uuid='cluster_template_id', coe=cluster_type)
        cluster.cluster_template = cluster_template

        mock_cluster_get_by_uuid.return_value = cluster

        if assert_raised:
            self.assertRaises(
                exception.InvalidParameterValue, test, self, *args)
        else:
            ret = test(self, *args)
            if hasattr(args[0], 'cluster_uuid'):
                mock_cluster_get_by_uuid.assert_called_once_with(
                    context, args[0].cluster_uuid)
                self.assertEqual(args[0].name, ret)
            else:
                mock_cluster_get_by_uuid.assert_called_once_with(
                    context, args[1])
                self.assertEqual(args[1], ret)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    def test_enforce_cluster_types_one_allowed(
            self,
            mock_cluster_get_by_uuid,
            mock_pecan_request):

        obj = mock.MagicMock()
        obj.name = 'test_object'
        obj.cluster_uuid = 'cluster_uuid'
        cluster_type = 'swarm'
        allowed_cluster_types = ['swarm']
        self._test_enforce_cluster_types(
            mock_cluster_get_by_uuid, mock_pecan_request,
            cluster_type, allowed_cluster_types, False, obj)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    def test_enforce_cluster_types_two_allowed(
            self,
            mock_cluster_get_by_uuid,
            mock_pecan_request):

        obj = mock.MagicMock()
        obj.name = 'test_object'
        obj.cluster_uuid = 'cluster_uuid'
        cluster_type = 'swarm'
        allowed_cluster_types = ['swarm', 'mesos']
        self._test_enforce_cluster_types(
            mock_cluster_get_by_uuid, mock_pecan_request,
            cluster_type, allowed_cluster_types, False, obj)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    def test_enforce_cluster_types_not_allowed(
            self,
            mock_cluster_get_by_uuid,
            mock_pecan_request):

        obj = mock.MagicMock()
        obj.name = 'test_object'
        obj.cluster_uuid = 'cluster_uuid'
        cluster_type = 'swarm'
        allowed_cluster_types = ['mesos']
        self._test_enforce_cluster_types(
            mock_cluster_get_by_uuid, mock_pecan_request,
            cluster_type, allowed_cluster_types,
            True, obj)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    def test_enforce_cluster_types_with_cluster_uuid(self,
                                                     mock_cluster_get_by_uuid,
                                                     mock_pecan_request):

        cluster_ident = 'e74c40e0-d825-11e2-a28f-0800200c9a66'

        cluster_type = 'swarm'
        allowed_cluster_types = ['swarm']
        self._test_enforce_cluster_types(
            mock_cluster_get_by_uuid, mock_pecan_request,
            cluster_type, allowed_cluster_types, False,
            None, cluster_ident)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_uuid')
    def test_enforce_cluster_types_with_cluster_uuid_not_allowed(
            self, mock_cluster_get_by_uuid, mock_pecan_request):

        cluster_ident = 'e74c40e0-d825-11e2-a28f-0800200c9a66'

        cluster_type = 'swarm'
        allowed_cluster_types = ['mesos']
        self._test_enforce_cluster_types(
            mock_cluster_get_by_uuid, mock_pecan_request,
            cluster_type, allowed_cluster_types, True,
            None, cluster_ident)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_name')
    def test_enforce_cluster_types_with_cluster_name(
            self, mock_cluster_get_by_uuid, mock_pecan_request):

        cluster_ident = 'cluster_name'
        cluster_type = 'swarm'
        allowed_cluster_types = ['swarm']
        self._test_enforce_cluster_types(
            mock_cluster_get_by_uuid, mock_pecan_request,
            cluster_type, allowed_cluster_types, False,
            None, cluster_ident)

    @mock.patch('pecan.request')
    @mock.patch('magnum.objects.Cluster.get_by_name')
    def test_enforce_cluster_types_with_cluster_name_not_allowed(
            self, mock_cluster_get_by_uuid, mock_pecan_request):

        cluster_ident = 'cluster_name'
        cluster_type = 'swarm'
        allowed_cluster_types = ['mesos']
        self._test_enforce_cluster_types(
            mock_cluster_get_by_uuid, mock_pecan_request,
            cluster_type, allowed_cluster_types, True,
            None, cluster_ident)

    def _test_enforce_network_driver_types_create(
            self,
            network_driver_type,
            network_driver_config_dict,
            coe='kubernetes',
            assert_raised=False):

        @v.enforce_network_driver_types_create()
        def test(self, cluster_template):
            pass

        for key, val in network_driver_config_dict.items():
            cfg.CONF.set_override(key, val, 'cluster_template')

        cluster_template = mock.MagicMock()
        cluster_template.name = 'test_cluster_template'
        cluster_template.network_driver = network_driver_type
        cluster_template.coe = coe

        # Reload the validator module so that ClusterTemplate configs are
        # re-evaluated.
        reload_module(v)
        validator = v.K8sValidator
        validator.supported_network_drivers = ['flannel', 'type1', 'type2']

        if assert_raised:
            self.assertRaises(exception.InvalidParameterValue,
                              test, self, cluster_template)
        else:
            test(self, cluster_template)
        return cluster_template

    def test_enforce_network_driver_types_one_allowed_create(self):
        self._test_enforce_network_driver_types_create(
            network_driver_type='type1',
            network_driver_config_dict={
                'kubernetes_allowed_network_drivers': ['type1']})

    def test_enforce_network_driver_types_two_allowed_create(self):
        self._test_enforce_network_driver_types_create(
            network_driver_type='type1',
            network_driver_config_dict={
                'kubernetes_allowed_network_drivers': ['type1', 'type2']})

    def test_enforce_network_driver_types_not_allowed_create(self):
        self._test_enforce_network_driver_types_create(
            network_driver_type='type1',
            network_driver_config_dict={
                'kubernetes_allowed_network_drivers': ['type2']},
            assert_raised=True)

    def test_enforce_network_driver_types_all_allowed_create(self):
        for driver in ['flannel', 'type1', 'type2']:
            self._test_enforce_network_driver_types_create(
                network_driver_type=driver,
                network_driver_config_dict={
                    'kubernetes_allowed_network_drivers': ['all']})

    def test_enforce_network_driver_types_invalid_coe_create(self):
        self._test_enforce_network_driver_types_create(
            network_driver_type='flannel',
            network_driver_config_dict={},
            coe='invalid_coe_type',
            assert_raised=True)

    def test_enforce_network_driver_types_default_create(self):
        cluster_template = self._test_enforce_network_driver_types_create(
            network_driver_type=None,
            network_driver_config_dict={})
        self.assertEqual('flannel', cluster_template.network_driver)

    def test_enforce_network_driver_types_default_config_create(self):
        cluster_template = self._test_enforce_network_driver_types_create(
            network_driver_type=None,
            network_driver_config_dict={
                'kubernetes_default_network_driver': 'type1'})
        self.assertEqual('type1', cluster_template.network_driver)

    def test_enforce_network_driver_types_default_invalid_create(self):
        self._test_enforce_network_driver_types_create(
            network_driver_type=None,
            network_driver_config_dict={
                'kubernetes_default_network_driver': 'invalid_driver'},
            assert_raised=True)

    @mock.patch('pecan.request')
    @mock.patch('magnum.api.utils.get_resource')
    def _test_enforce_network_driver_types_update(
            self,
            mock_get_resource,
            mock_pecan_request,
            network_driver_type,
            network_driver_config_dict,
            assert_raised=False):

        @v.enforce_network_driver_types_update()
        def test(self, cluster_template_ident, patch):
            pass

        for key, val in network_driver_config_dict.items():
            cfg.CONF.set_override(key, val, 'cluster_template')

        cluster_template_ident = 'test_uuid_or_name'

        patch = [{'path': '/network_driver', 'value': network_driver_type,
                  'op': 'replace'}]
        context = mock_pecan_request.context
        cluster_template = obj_utils.get_test_cluster_template(
            context, uuid=cluster_template_ident, coe='kubernetes')
        cluster_template.network_driver = network_driver_type
        mock_get_resource.return_value = cluster_template

        # Reload the validator module so that ClusterTemplate configs are
        # re-evaluated.
        reload_module(v)
        validator = v.K8sValidator
        validator.supported_network_drivers = ['flannel', 'type1', 'type2']

        if assert_raised:
            self.assertRaises(exception.InvalidParameterValue,
                              test, self, cluster_template_ident, patch)
        else:
            test(self, cluster_template_ident, patch)
            mock_get_resource.assert_called_once_with(
                'ClusterTemplate', cluster_template_ident)

    def test_enforce_network_driver_types_one_allowed_update(self):
        self._test_enforce_network_driver_types_update(
            network_driver_type='type1',
            network_driver_config_dict={
                'kubernetes_allowed_network_drivers': ['type1']})

    def test_enforce_network_driver_types_two_allowed_update(self):
        self._test_enforce_network_driver_types_update(
            network_driver_type='type1',
            network_driver_config_dict={
                'kubernetes_allowed_network_drivers': ['type1', 'type2']})

    def test_enforce_network_driver_types_not_allowed_update(self):
        self._test_enforce_network_driver_types_update(
            network_driver_type='type1',
            network_driver_config_dict={
                'kubernetes_allowed_network_drivers': ['type2']},
            assert_raised=True)

    def test_enforce_network_driver_types_all_allowed_update(self):
        for driver in ['flannel', 'type1', 'type2']:
            self._test_enforce_network_driver_types_update(
                network_driver_type=driver,
                network_driver_config_dict={
                    'kubernetes_allowed_network_drivers': ['all']})

    def _test_enforce_volume_driver_types_create(
            self,
            volume_driver_type,
            coe='kubernetes',
            assert_raised=False):

        @v.enforce_volume_driver_types_create()
        def test(self, cluster_template):
            pass

        cluster_template = obj_utils.get_test_cluster_template(
            {}, name='test_cluster_template', coe=coe,
            volume_driver=volume_driver_type)

        if assert_raised:
            self.assertRaises(exception.InvalidParameterValue,
                              test, self, cluster_template)
        else:
            test(self, cluster_template)

    def test_enforce_volume_driver_types_valid_create(self):
        self._test_enforce_volume_driver_types_create(
            volume_driver_type='cinder')

    def test_enforce_volume_driver_types_invalid_create(self):
        self._test_enforce_volume_driver_types_create(
            volume_driver_type='type',
            assert_raised=True)

    @mock.patch('pecan.request')
    @mock.patch('magnum.api.utils.get_resource')
    def _test_enforce_volume_driver_types_update(
            self,
            mock_get_resource,
            mock_pecan_request,
            volume_driver_type,
            op,
            assert_raised=False):

        @v.enforce_volume_driver_types_update()
        def test(self, cluster_template_ident, patch):
            pass

        cluster_template_ident = 'test_uuid_or_name'
        patch = [{'path': '/volume_driver', 'value': volume_driver_type,
                  'op': op}]
        context = mock_pecan_request.context
        cluster_template = obj_utils.get_test_cluster_template(
            context, uuid=cluster_template_ident, coe='kubernetes')
        mock_get_resource.return_value = cluster_template

        # Reload the validator module so that ClusterTemplate configs are
        # re-evaluated.
        reload_module(v)
        validator = v.K8sValidator
        validator.supported_volume_driver = ['cinder']

        if assert_raised:
            self.assertRaises(exception.InvalidParameterValue,
                              test, self, cluster_template_ident, patch)
        else:
            test(self, cluster_template_ident, patch)
            mock_get_resource.assert_called_once_with(
                'ClusterTemplate', cluster_template_ident)

    def test_enforce_volume_driver_types_supported_replace_update(self):
        self._test_enforce_volume_driver_types_update(
            volume_driver_type='cinder',
            op='replace')

    def test_enforce_volume_driver_types_not_supported_replace_update(self):
        self._test_enforce_volume_driver_types_update(
            volume_driver_type='type1',
            op='replace',
            assert_raised=True)

    def test_enforce_volume_driver_types_supported_add_update(self):
        self._test_enforce_volume_driver_types_update(
            volume_driver_type='cinder',
            op='add')

    def test_enforce_volume_driver_types_not_supported_add_update(self):
        self._test_enforce_volume_driver_types_update(
            volume_driver_type='type1',
            op='add',
            assert_raised=True)

    def test_enforce_volume_driver_types_remove_update(self):
        self._test_enforce_volume_driver_types_update(
            volume_driver_type='cinder',
            op='remove')

    def test_validate_cluster_properties(self):
        allowed_properties = v.cluster_update_allowed_properties
        for field in objects.Cluster.fields:
            if field in allowed_properties:
                v.validate_cluster_properties(set([field]))
            else:
                self.assertRaises(exception.InvalidParameterValue,
                                  v.validate_cluster_properties, set([field]))
