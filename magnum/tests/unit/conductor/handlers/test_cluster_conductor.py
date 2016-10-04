# -*- coding: utf-8 -*-

# Copyright 2014 NEC Corporation.  All rights reserved.
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

import six

from heatclient import exc
import mock
from mock import patch
from oslo_config import cfg
from oslo_service import loopingcall
from pycadf import cadftaxonomy as taxonomy

from magnum.common import exception
from magnum.conductor.handlers import cluster_conductor
from magnum import objects
from magnum.objects.fields import ClusterStatus as cluster_status
from magnum.tests import base
from magnum.tests import fake_notifier
from magnum.tests.unit.db import base as db_base
from magnum.tests.unit.db import utils


class TestHandler(db_base.DbTestCase):

    def setUp(self):
        super(TestHandler, self).setUp()
        self.handler = cluster_conductor.Handler()
        cluster_template_dict = utils.get_test_cluster_template()
        self.cluster_template = objects.ClusterTemplate(
            self.context, **cluster_template_dict)
        self.cluster_template.create()
        cluster_dict = utils.get_test_cluster(node_count=1)
        self.cluster = objects.Cluster(self.context, **cluster_dict)
        self.cluster.create()

    @patch('magnum.conductor.scale_manager.ScaleManager')
    @patch(
        'magnum.conductor.handlers.cluster_conductor.Handler._poll_and_check')
    @patch('magnum.conductor.handlers.cluster_conductor._update_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_update_node_count_success(
            self, mock_openstack_client_class,
            mock_update_stack, mock_poll_and_check,
            mock_scale_manager):
        def side_effect(*args, **kwargs):
            self.cluster.node_count = 2
            self.cluster.save()
        mock_poll_and_check.side_effect = side_effect
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = cluster_status.CREATE_COMPLETE
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.cluster.node_count = 2
        self.handler.cluster_update(self.context, self.cluster)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_update_stack.assert_called_once_with(
            self.context, mock_openstack_client, self.cluster,
            mock_scale_manager.return_value, False)
        cluster = objects.Cluster.get(self.context, self.cluster.uuid)
        self.assertEqual(2, cluster.node_count)

    @patch(
        'magnum.conductor.handlers.cluster_conductor.Handler._poll_and_check')
    @patch('magnum.conductor.handlers.cluster_conductor._update_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_update_node_count_failure(
            self, mock_openstack_client_class,
            mock_update_stack, mock_poll_and_check):
        def side_effect(*args, **kwargs):
            self.cluster.node_count = 2
            self.cluster.save()
        mock_poll_and_check.side_effect = side_effect
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.cluster.node_count = 2
        self.assertRaises(exception.NotSupported, self.handler.cluster_update,
                          self.context, self.cluster)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

        cluster = objects.Cluster.get(self.context, self.cluster.uuid)
        self.assertEqual(1, cluster.node_count)

    @patch('magnum.conductor.scale_manager.ScaleManager')
    @patch(
        'magnum.conductor.handlers.cluster_conductor.Handler._poll_and_check')
    @patch('magnum.conductor.handlers.cluster_conductor._update_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def _test_update_cluster_status_complete(
            self, expect_status, mock_openstack_client_class,
            mock_update_stack, mock_poll_and_check,
            mock_scale_manager):
        def side_effect(*args, **kwargs):
            self.cluster.node_count = 2
            self.cluster.save()
        mock_poll_and_check.side_effect = side_effect
        mock_heat_stack = mock.MagicMock()
        mock_heat_stack.stack_status = expect_status
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client = mock_openstack_client_class.return_value
        mock_openstack_client.heat.return_value = mock_heat_client

        self.cluster.node_count = 2
        self.handler.cluster_update(self.context, self.cluster)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.update', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_update_stack.assert_called_once_with(
            self.context, mock_openstack_client, self.cluster,
            mock_scale_manager.return_value, False)
        cluster = objects.Cluster.get(self.context, self.cluster.uuid)
        self.assertEqual(2, cluster.node_count)

    def test_update_cluster_status_update_compelete(self):
        self._test_update_cluster_status_complete(
            cluster_status.UPDATE_COMPLETE)

    def test_update_cluster_status_resume_compelete(self):
        self._test_update_cluster_status_complete(
            cluster_status.RESUME_COMPLETE)

    def test_update_cluster_status_restore_compelete(self):
        self._test_update_cluster_status_complete(
            cluster_status.RESTORE_COMPLETE)

    def test_update_cluster_status_rollback_compelete(self):
        self._test_update_cluster_status_complete(
            cluster_status.ROLLBACK_COMPLETE)

    def test_update_cluster_status_snapshot_compelete(self):
        self._test_update_cluster_status_complete(
            cluster_status.SNAPSHOT_COMPLETE)

    def test_update_cluster_status_check_compelete(self):
        self._test_update_cluster_status_complete(
            cluster_status.CHECK_COMPLETE)

    def test_update_cluster_status_adopt_compelete(self):
        self._test_update_cluster_status_complete(
            cluster_status.ADOPT_COMPLETE)

    @patch('magnum.conductor.handlers.cluster_conductor.HeatPoller')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.conductor.handlers.cluster_conductor._create_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create(self, mock_openstack_client_class,
                    mock_create_stack, mock_cm, mock_trust_manager,
                    mock_heat_poller_class):
        timeout = 15
        mock_poller = mock.MagicMock()
        mock_poller.poll_and_check.return_value = loopingcall.LoopingCallDone()
        mock_heat_poller_class.return_value = mock_poller
        osc = mock.sentinel.osc
        mock_openstack_client_class.return_value = osc

        def create_stack_side_effect(context, osc, cluster, timeout):
            return {'stack': {'id': 'stack-id'}}

        mock_create_stack.side_effect = create_stack_side_effect

        # FixMe(eliqiao): cluster_create will call cluster.create()
        # again, this so bad because we have already called it in setUp
        # since other test case will share the codes in setUp()
        # But in self.handler.cluster_create, we update cluster.uuid and
        # cluster.stack_id so cluster.create will create a new recored with
        # clustermodel_id None, this is bad because we load clusterModel
        # object in cluster object by clustermodel_id. Here update
        # self.cluster.clustermodel_id so cluster.obj_get_changes will get
        # notice that clustermodel_id is updated and will update it
        # in db.
        self.cluster.cluster_template_id = self.cluster_template.uuid
        cluster = self.handler.cluster_create(self.context,
                                              self.cluster, timeout)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])

        mock_create_stack.assert_called_once_with(self.context,
                                                  mock.sentinel.osc,
                                                  self.cluster, timeout)
        mock_cm.generate_certificates_to_cluster.assert_called_once_with(
            self.cluster, context=self.context)
        self.assertEqual(cluster_status.CREATE_IN_PROGRESS, cluster.status)
        mock_trust_manager.create_trustee_and_trust.assert_called_once_with(
            osc, self.cluster)

    def _test_create_failed(self,
                            mock_openstack_client_class,
                            mock_cert_manager,
                            mock_trust_manager,
                            mock_cluster_create,
                            expected_exception,
                            is_create_cert_called=True,
                            is_create_trust_called=True):
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        timeout = 15

        self.assertRaises(
            expected_exception,
            self.handler.cluster_create,
            self.context,
            self.cluster, timeout
        )

        gctb = mock_cert_manager.generate_certificates_to_cluster
        if is_create_cert_called:
            gctb.assert_called_once_with(self.cluster, context=self.context)
        else:
            gctb.assert_not_called()
        ctat = mock_trust_manager.create_trustee_and_trust
        if is_create_trust_called:
            ctat.assert_called_once_with(osc, self.cluster)
        else:
            ctat.assert_not_called()
        mock_cluster_create.assert_called_once_with()

    @patch('magnum.objects.Cluster.create')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.conductor.handlers.cluster_conductor._create_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_handles_bad_request(self, mock_openstack_client_class,
                                        mock_create_stack,
                                        mock_cert_manager,
                                        mock_trust_manager,
                                        mock_cluster_create):
        mock_create_stack.side_effect = exc.HTTPBadRequest

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            mock_cluster_create,
            exception.InvalidParameterValue
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])

    @patch('magnum.objects.Cluster.create')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_cert_failed(self, mock_openstack_client_class,
                                     mock_cert_manager,
                                     mock_trust_manager,
                                     mock_cluster_create):
        e = exception.CertificatesToClusterFailed(cluster_uuid='uuid')
        mock_cert_manager.generate_certificates_to_cluster.side_effect = e

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            mock_cluster_create,
            exception.CertificatesToClusterFailed
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

    @patch('magnum.objects.Cluster.create')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.conductor.handlers.cluster_conductor._create_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_trust_failed(self, mock_openstack_client_class,
                                      mock_create_stack,
                                      mock_cert_manager,
                                      mock_trust_manager,
                                      mock_cluster_create):
        e = exception.TrusteeOrTrustToClusterFailed(cluster_uuid='uuid')
        mock_trust_manager.create_trustee_and_trust.side_effect = e

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            mock_cluster_create,
            exception.TrusteeOrTrustToClusterFailed,
            False
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(1, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[0].payload['outcome'])

    @patch('magnum.objects.Cluster.create')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.conductor.handlers.cluster_conductor._create_stack')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_invalid_unicode_name(self,
                                              mock_openstack_client_class,
                                              mock_create_stack,
                                              mock_cert_manager,
                                              mock_trust_manager,
                                              mock_cluster_create):
        error_message = six.u("""Invalid stack name 测试集群-zoyh253geukk
                              must contain only alphanumeric or "_-."
                              characters, must start with alpha""")
        mock_create_stack.side_effect = exc.HTTPBadRequest(error_message)

        self._test_create_failed(
            mock_openstack_client_class,
            mock_cert_manager,
            mock_trust_manager,
            mock_cluster_create,
            exception.InvalidParameterValue
        )

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])

    @patch('magnum.conductor.handlers.cluster_conductor.HeatPoller')
    @patch('heatclient.common.template_utils'
           '.process_multiple_environments_and_files')
    @patch('heatclient.common.template_utils.get_template_contents')
    @patch('magnum.conductor.handlers.cluster_conductor'
           '._extract_template_definition')
    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.short_id')
    @patch('magnum.common.clients.OpenStackClients')
    def test_create_with_environment(self,
                                     mock_openstack_client_class,
                                     mock_short_id,
                                     mock_cert_manager,
                                     mock_trust_manager,
                                     mock_extract_tmpl_def,
                                     mock_get_template_contents,
                                     mock_process_mult,
                                     mock_heat_poller_class):
        timeout = 15
        self.cluster.cluster_template_id = self.cluster_template.uuid
        cluster_name = self.cluster.name
        mock_short_id.generate_id.return_value = 'short_id'
        mock_poller = mock.MagicMock()
        mock_poller.poll_and_check.return_value = loopingcall.LoopingCallDone()
        mock_heat_poller_class.return_value = mock_poller

        mock_extract_tmpl_def.return_value = (
            'the/template/path.yaml',
            {'heat_param_1': 'foo', 'heat_param_2': 'bar'},
            ['env_file_1', 'env_file_2'])

        mock_get_template_contents.return_value = (
            {'tmpl_file_1': 'some content',
             'tmpl_file_2': 'some more content'},
            'some template yaml')

        def do_mock_process_mult(env_paths=None, env_list_tracker=None):
            self.assertEqual(env_list_tracker, [])
            for f in env_paths:
                env_list_tracker.append('file:///' + f)
            env_map = {path: 'content of ' + path for path in env_list_tracker}
            return (env_map, None)

        mock_process_mult.side_effect = do_mock_process_mult

        mock_hc = mock.Mock()
        mock_hc.stacks.create.return_value = {'stack': {'id': 'stack-id'}}

        osc = mock.Mock()
        osc.heat.return_value = mock_hc
        mock_openstack_client_class.return_value = osc

        self.handler.cluster_create(self.context, self.cluster, timeout)

        mock_extract_tmpl_def.assert_called_once_with(self.context,
                                                      self.cluster)
        mock_get_template_contents.assert_called_once_with(
            'the/template/path.yaml')
        mock_process_mult.assert_called_once_with(
            env_paths=['the/template/env_file_1', 'the/template/env_file_2'],
            env_list_tracker=mock.ANY)
        mock_hc.stacks.create.assert_called_once_with(
            environment_files=['file:///the/template/env_file_1',
                               'file:///the/template/env_file_2'],
            files={
                'tmpl_file_1': 'some content',
                'tmpl_file_2': 'some more content',
                'file:///the/template/env_file_1':
                    'content of file:///the/template/env_file_1',
                'file:///the/template/env_file_2':
                    'content of file:///the/template/env_file_2'
            },
            parameters={'heat_param_1': 'foo', 'heat_param_2': 'bar'},
            stack_name=('%s-short_id' % cluster_name),
            template='some template yaml',
            timeout_mins=timeout)

    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.common.clients.OpenStackClients')
    def test_cluster_delete(self, mock_openstack_client_class, cert_manager):
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        osc.heat.side_effect = exc.HTTPNotFound
        self.handler.cluster_delete(self.context, self.cluster.uuid)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.cluster.delete', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.delete', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[1].payload['outcome'])
        self.assertEqual(
            1, cert_manager.delete_certificates_from_cluster.call_count)
        # The cluster has been destroyed
        self.assertRaises(exception.ClusterNotFound,
                          objects.Cluster.get, self.context, self.cluster.uuid)

    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    @patch('magnum.common.clients.OpenStackClients')
    def test_cluster_delete_conflict(self, mock_openstack_client_class,
                                     cert_manager):
        osc = mock.MagicMock()
        mock_openstack_client_class.return_value = osc
        osc.heat.side_effect = exc.HTTPConflict
        self.assertRaises(exception.OperationInProgress,
                          self.handler.cluster_delete,
                          self.context,
                          self.cluster.uuid)

        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(2, len(notifications))
        self.assertEqual(
            'magnum.cluster.delete', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_PENDING, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.delete', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])
        self.assertEqual(
            0, cert_manager.delete_certificates_from_cluster.call_count)


class TestHeatPoller(base.TestCase):

    @patch('magnum.conductor.utils.retrieve_cluster_template')
    @patch('oslo_config.cfg')
    @patch('magnum.common.clients.OpenStackClients')
    def setup_poll_test(self, mock_openstack_client, cfg,
                        mock_retrieve_cluster_template):
        cfg.CONF.cluster_heat.max_attempts = 10

        cluster = mock.MagicMock()
        cluster_template_dict = utils.get_test_cluster_template(
            coe='kubernetes')
        mock_heat_stack = mock.MagicMock()
        mock_heat_client = mock.MagicMock()
        mock_heat_client.stacks.get.return_value = mock_heat_stack
        mock_openstack_client.heat.return_value = mock_heat_client
        cluster_template = objects.ClusterTemplate(self.context,
                                                   **cluster_template_dict)
        mock_retrieve_cluster_template.return_value = cluster_template
        poller = cluster_conductor.HeatPoller(mock_openstack_client, cluster)
        poller.get_version_info = mock.MagicMock()
        return (mock_heat_stack, cluster, poller)

    def test_poll_and_check_send_notification(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = cluster_status.CREATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.DELETE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        mock_heat_stack.stack_status = cluster_status.UPDATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(6, poller.attempts)
        notifications = fake_notifier.NOTIFICATIONS
        self.assertEqual(6, len(notifications))
        self.assertEqual(
            'magnum.cluster.create', notifications[0].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[0].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.create', notifications[1].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[1].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.delete', notifications[2].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[2].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.delete', notifications[3].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[3].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.update', notifications[4].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_SUCCESS, notifications[4].payload['outcome'])
        self.assertEqual(
            'magnum.cluster.update', notifications[5].event_type)
        self.assertEqual(
            taxonomy.OUTCOME_FAILURE, notifications[5].payload['outcome'])

    def test_poll_no_save(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        cluster.status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(0, cluster.save.call_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_save(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        cluster.status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        mock_heat_stack.stack_status_reason = 'Create failed'
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.save.call_count)
        self.assertEqual(cluster_status.CREATE_FAILED, cluster.status)
        self.assertEqual('Create failed', cluster.status_reason)
        self.assertEqual(1, poller.attempts)

    def test_poll_done(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        self.assertEqual(2, poller.attempts)

    def test_poll_done_by_update(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.UPDATE_COMPLETE
        mock_heat_stack.parameters = {'number_of_minions': 2}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(1, cluster.save.call_count)
        self.assertEqual(cluster_status.UPDATE_COMPLETE, cluster.status)
        self.assertEqual(2, cluster.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_done_by_update_failed(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.UPDATE_FAILED
        mock_heat_stack.parameters = {'number_of_minions': 2}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.save.call_count)
        self.assertEqual(cluster_status.UPDATE_FAILED, cluster.status)
        self.assertEqual(2, cluster.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_done_by_rollback_complete(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.ROLLBACK_COMPLETE
        mock_heat_stack.parameters = {'number_of_minions': 1}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.save.call_count)
        self.assertEqual(cluster_status.ROLLBACK_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_done_by_rollback_failed(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.ROLLBACK_FAILED
        mock_heat_stack.parameters = {'number_of_minions': 1}
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.save.call_count)
        self.assertEqual(cluster_status.ROLLBACK_FAILED, cluster.status)
        self.assertEqual(1, cluster.node_count)
        self.assertEqual(1, poller.attempts)

    def test_poll_destroy(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.DELETE_FAILED
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        # Destroy method is not called when stack delete failed
        self.assertEqual(0, cluster.destroy.call_count)

        mock_heat_stack.stack_status = cluster_status.DELETE_IN_PROGRESS
        poller.poll_and_check()
        self.assertEqual(0, cluster.destroy.call_count)
        self.assertEqual(cluster_status.DELETE_IN_PROGRESS, cluster.status)

        mock_heat_stack.stack_status = cluster_status.DELETE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)
        # The cluster status should still be DELETE_IN_PROGRESS, because
        # the destroy() method may be failed. If success, this cluster record
        # will delete directly, change status is meaningless.
        self.assertEqual(cluster_status.DELETE_IN_PROGRESS, cluster.status)
        self.assertEqual(1, cluster.destroy.call_count)

    def test_poll_delete_in_progress_timeout_set(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.DELETE_IN_PROGRESS
        mock_heat_stack.timeout_mins = 60
        # timeout only affects stack creation so expecting this
        # to process normally
        poller.poll_and_check()

    def test_poll_delete_in_progress_max_attempts_reached(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.DELETE_IN_PROGRESS
        poller.attempts = cfg.CONF.cluster_heat.max_attempts
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_reached_no_timeout(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.attempts = cfg.CONF.cluster_heat.max_attempts
        mock_heat_stack.timeout_mins = None
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_reached_timeout_set(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.attempts = cfg.CONF.cluster_heat.max_attempts
        mock_heat_stack.timeout_mins = 60
        # since the timeout is set the max attempts gets ignored since
        # the timeout will eventually stop the poller either when
        # the stack gets created or the timeout gets reached
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_reached_timed_out(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        poller.attempts = cfg.CONF.cluster_heat.max_attempts
        mock_heat_stack.timeout_mins = 60
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_create_in_prog_max_att_not_reached_no_timeout(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.timeout.mins = None
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_not_reached_timeout_set(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.timeout_mins = 60
        poller.poll_and_check()

    def test_poll_create_in_prog_max_att_not_reached_timed_out(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.stack_status = cluster_status.CREATE_FAILED
        mock_heat_stack.timeout_mins = 60
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

    def test_poll_node_count(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_minions': 1}
        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        poller.poll_and_check()

        self.assertEqual(1, cluster.node_count)

    def test_poll_node_count_by_update(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()

        mock_heat_stack.parameters = {'number_of_minions': 2}
        mock_heat_stack.stack_status = cluster_status.UPDATE_COMPLETE
        self.assertRaises(loopingcall.LoopingCallDone, poller.poll_and_check)

        self.assertEqual(2, cluster.node_count)

    @patch('magnum.conductor.handlers.cluster_conductor.trust_manager')
    @patch('magnum.conductor.handlers.cluster_conductor.cert_manager')
    def test_delete_complete(self, cert_manager, trust_manager):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        poller._delete_complete()
        self.assertEqual(1, cluster.destroy.call_count)
        self.assertEqual(
            1, cert_manager.delete_certificates_from_cluster.call_count)
        self.assertEqual(1,
                         trust_manager.delete_trustee_and_trust.call_count)

    def test_create_or_complete(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = cluster_status.CREATE_COMPLETE
        mock_heat_stack.stack_status_reason = 'stack complete'
        poller._sync_cluster_and_template_status(mock_heat_stack)
        self.assertEqual('stack complete', cluster.status_reason)
        self.assertEqual(cluster_status.CREATE_COMPLETE, cluster.status)
        self.assertEqual(1, cluster.save.call_count)

    def test_sync_cluster_status(self):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        mock_heat_stack.stack_status = cluster_status.CREATE_IN_PROGRESS
        mock_heat_stack.stack_status_reason = 'stack incomplete'
        poller._sync_cluster_status(mock_heat_stack)
        self.assertEqual('stack incomplete', cluster.status_reason)
        self.assertEqual(cluster_status.CREATE_IN_PROGRESS, cluster.status)

    @patch('magnum.conductor.handlers.cluster_conductor.LOG')
    def test_cluster_failed(self, logger):
        mock_heat_stack, cluster, poller = self.setup_poll_test()
        poller._sync_cluster_and_template_status(mock_heat_stack)
        poller._cluster_failed(mock_heat_stack)
        self.assertEqual(1, logger.error.call_count)
