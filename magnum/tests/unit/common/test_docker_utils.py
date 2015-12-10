# Copyright 2015 Huawei Technologies Co.,LTD.
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
from oslo_config import cfg

from magnum.common import docker_utils
from magnum.tests import base


CONF = cfg.CONF


class TestDockerUtils(base.BaseTestCase):
    @mock.patch.object(docker_utils, 'docker_client')
    @mock.patch.object(docker_utils, 'cert_manager')
    @mock.patch.object(docker_utils.objects.BayModel, 'get_by_uuid')
    @mock.patch.object(docker_utils.objects.Bay, 'get_by_uuid')
    def test_docker_for_container(self, mock_get_bay_by_uuid,
                                  mock_get_baymodel_by_uuid,
                                  mock_cert_manager,
                                  mock_docker_client):
        mock_container = mock.MagicMock()
        mock_bay = mock.MagicMock()
        mock_bay.api_address = 'https://1.2.3.4:2376'
        mock_get_bay_by_uuid.return_value = mock_bay
        mock_baymodel = mock.MagicMock()
        mock_baymodel.tls_disabled = False
        mock_get_baymodel_by_uuid.return_value = mock_baymodel
        mock_ca_cert = mock.MagicMock()
        mock_magnum_key = mock.MagicMock()
        mock_magnum_cert = mock.MagicMock()
        mock_cert_manager.create_client_files.return_value = (
            mock_ca_cert, mock_magnum_key, mock_magnum_cert
        )

        mock_docker = mock.MagicMock()
        mock_docker_client.DockerHTTPClient.return_value = mock_docker

        with docker_utils.docker_for_container(mock.sentinel.context,
                                               mock_container) as docker:
            self.assertEqual(mock_docker, docker)

        mock_get_bay_by_uuid.assert_called_once_with(mock.sentinel.context,
                                                     mock_container.bay_uuid)
        mock_get_baymodel_by_uuid.assert_called_once_with(
            mock.sentinel.context, mock_bay.baymodel_id)
        mock_docker_client.DockerHTTPClient.assert_called_once_with(
            'https://1.2.3.4:2376',
            CONF.docker.docker_remote_api_version,
            CONF.docker.default_timeout,
            ca_cert=mock_ca_cert.name,
            client_key=mock_magnum_key.name,
            client_cert=mock_magnum_cert.name)

    @mock.patch.object(docker_utils, 'docker_client')
    @mock.patch.object(docker_utils, 'cert_manager')
    @mock.patch.object(docker_utils.objects.BayModel, 'get_by_uuid')
    @mock.patch.object(docker_utils.objects.Bay, 'get_by_uuid')
    @mock.patch.object(docker_utils.objects.Container, 'get_by_uuid')
    def test_docker_for_container_uuid(self, mock_get_container_by_uuid,
                                       mock_get_bay_by_uuid,
                                       mock_get_baymodel_by_uuid,
                                       mock_cert_manager,
                                       mock_docker_client):
        mock_container = mock.MagicMock()
        mock_container.uuid = '8e48ffb1-754d-4f21-bdd0-1a39bf796389'
        mock_get_container_by_uuid.return_value = mock_container
        mock_bay = mock.MagicMock()
        mock_bay.api_address = 'https://1.2.3.4:2376'
        mock_get_bay_by_uuid.return_value = mock_bay
        mock_baymodel = mock.MagicMock()
        mock_baymodel.tls_disabled = False
        mock_get_baymodel_by_uuid.return_value = mock_baymodel
        mock_ca_cert = mock.MagicMock()
        mock_magnum_key = mock.MagicMock()
        mock_magnum_cert = mock.MagicMock()
        mock_cert_manager.create_client_files.return_value = (
            mock_ca_cert, mock_magnum_key, mock_magnum_cert
        )

        mock_docker = mock.MagicMock()
        mock_docker_client.DockerHTTPClient.return_value = mock_docker

        with docker_utils.docker_for_container(
                mock.sentinel.context, mock_container.uuid) as docker:
            self.assertEqual(mock_docker, docker)

        mock_get_container_by_uuid.assert_called_once_with(
            mock.sentinel.context, mock_container.uuid
        )
        mock_get_bay_by_uuid.assert_called_once_with(mock.sentinel.context,
                                                     mock_container.bay_uuid)
        mock_get_baymodel_by_uuid.assert_called_once_with(
            mock.sentinel.context, mock_bay.baymodel_id)
        mock_docker_client.DockerHTTPClient.assert_called_once_with(
            'https://1.2.3.4:2376',
            CONF.docker.docker_remote_api_version,
            CONF.docker.default_timeout,
            ca_cert=mock_ca_cert.name,
            client_key=mock_magnum_key.name,
            client_cert=mock_magnum_cert.name)

    @mock.patch.object(docker_utils, 'docker_client')
    @mock.patch.object(docker_utils.objects.BayModel, 'get_by_uuid')
    @mock.patch.object(docker_utils.objects.Bay, 'get_by_uuid')
    def test_docker_for_container_tls_disabled(self, mock_get_bay_by_uuid,
                                               mock_get_baymodel_by_uuid,
                                               mock_docker_client):
        mock_container = mock.MagicMock()
        mock_bay = mock.MagicMock()
        mock_bay.api_address = 'tcp://1.2.3.4:2376'
        mock_get_bay_by_uuid.return_value = mock_bay
        mock_baymodel = mock.MagicMock()
        mock_baymodel.tls_disabled = True
        mock_get_baymodel_by_uuid.return_value = mock_baymodel
        mock_docker = mock.MagicMock()
        mock_docker_client.DockerHTTPClient.return_value = mock_docker

        with docker_utils.docker_for_container(mock.sentinel.context,
                                               mock_container) as docker:
            self.assertEqual(mock_docker, docker)

        mock_get_bay_by_uuid.assert_called_once_with(mock.sentinel.context,
                                                     mock_container.bay_uuid)
        mock_get_baymodel_by_uuid.assert_called_once_with(
            mock.sentinel.context, mock_bay.baymodel_id)
        mock_docker_client.DockerHTTPClient.assert_called_once_with(
            'tcp://1.2.3.4:2376',
            CONF.docker.docker_remote_api_version,
            CONF.docker.default_timeout)
