# Copyright 2015 NEC Corporation.  All rights reserved.
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

from magnum.common import exception
from magnum.conductor.handlers.common import cert_manager
from magnum.tests import base


class CertManagerTestCase(base.BaseTestCase):
    def setUp(self):
        super(CertManagerTestCase, self).setUp()

        cert_manager_patcher = mock.patch.object(cert_manager, 'cert_manager')
        self.cert_manager = cert_manager_patcher.start()
        self.addCleanup(cert_manager_patcher.stop)

        self.cert_manager_backend = mock.MagicMock()
        self.cert_manager.get_backend.return_value = self.cert_manager_backend

        self.cert_manager_backend.CertManager = mock.MagicMock()
        self.CertManager = self.cert_manager_backend.CertManager

    @mock.patch('magnum.common.x509.operations.generate_ca_certificate')
    @mock.patch('magnum.common.short_id.generate_id')
    def test_generate_ca_cert(self, mock_generate_id, mock_generate_ca_cert):
        expected_ca_name = 'ca-name'
        expected_ca_password = 'password'
        expected_ca_cert = {
            'private_key': 'private_key', 'certificate': 'certificate'}
        expected_ca_cert_ref = 'ca_cert_ref'

        mock_generate_id.return_value = expected_ca_password
        mock_generate_ca_cert.return_value = expected_ca_cert

        self.CertManager.store_cert.return_value = expected_ca_cert_ref
        self.assertEqual((expected_ca_cert_ref, expected_ca_cert,
                          expected_ca_password),
                         cert_manager._generate_ca_cert(expected_ca_name))

        mock_generate_ca_cert.assert_called_once_with(
            expected_ca_name, encryption_password=expected_ca_password)
        self.CertManager.store_cert.assert_called_once_with(
            certificate=expected_ca_cert['certificate'],
            private_key=expected_ca_cert['private_key'],
            private_key_passphrase=expected_ca_password,
            name=expected_ca_name,
            context=None
        )

    @mock.patch('magnum.common.x509.operations.generate_client_certificate')
    @mock.patch('magnum.common.short_id.generate_id')
    def test_generate_client_cert(self, mock_generate_id, mock_generate_cert):
        expected_name = cert_manager.CONDUCTOR_CLIENT_NAME
        expected_ca_name = 'ca-name'
        expected_password = 'password'
        expected_ca_password = 'ca-password'
        expected_cert = {
            'private_key': 'private_key', 'certificate': 'certificate'}
        expected_ca_cert = {
            'private_key': 'ca_private_key', 'certificate': 'ca_certificate'}
        expected_cert_ref = 'cert_ref'

        mock_generate_id.return_value = expected_password
        mock_generate_cert.return_value = expected_cert

        self.CertManager.store_cert.return_value = expected_cert_ref

        self.assertEqual(
            expected_cert_ref,
            cert_manager._generate_client_cert(
                expected_ca_name,
                expected_ca_cert,
                expected_ca_password))

        mock_generate_cert.assert_called_once_with(
            expected_ca_name,
            expected_name,
            expected_ca_cert['private_key'],
            encryption_password=expected_password,
            ca_key_password=expected_ca_password,
        )
        self.CertManager.store_cert.assert_called_once_with(
            certificate=expected_cert['certificate'],
            private_key=expected_cert['private_key'],
            private_key_passphrase=expected_password,
            name=expected_name,
            context=None
        )

    def _test_generate_certificates(self,
                                    expected_ca_name,
                                    mock_cluster,
                                    mock_generate_ca_cert,
                                    mock_generate_client_cert):
        expected_ca_password = 'ca-password'
        expected_ca_cert = {
            'private_key': 'ca_private_key', 'certificate': 'ca_certificate'}
        expected_cert_ref = 'cert_ref'
        expected_ca_cert_ref = 'ca-cert-ref'

        mock_generate_ca_cert.return_value = (expected_ca_cert_ref,
                                              expected_ca_cert,
                                              expected_ca_password)
        mock_generate_client_cert.return_value = expected_cert_ref

        cert_manager.generate_certificates_to_cluster(mock_cluster)
        self.assertEqual(expected_ca_cert_ref, mock_cluster.ca_cert_ref)
        self.assertEqual(expected_cert_ref, mock_cluster.magnum_cert_ref)

        mock_generate_ca_cert.assert_called_once_with(expected_ca_name,
                                                      context=None)
        mock_generate_client_cert.assert_called_once_with(
            expected_ca_name, expected_ca_cert, expected_ca_password,
            context=None)

    @mock.patch('magnum.conductor.handlers.common.cert_manager.'
                '_generate_client_cert')
    @mock.patch('magnum.conductor.handlers.common.cert_manager.'
                '_generate_ca_cert')
    def test_generate_certificates(self, mock_generate_ca_cert,
                                   mock_generate_client_cert):
        expected_ca_name = 'ca-name'
        mock_cluster = mock.MagicMock()
        mock_cluster.name = expected_ca_name

        self._test_generate_certificates(expected_ca_name,
                                         mock_cluster,
                                         mock_generate_ca_cert,
                                         mock_generate_client_cert)

    @mock.patch('magnum.conductor.handlers.common.cert_manager.'
                '_generate_client_cert')
    @mock.patch('magnum.conductor.handlers.common.cert_manager.'
                '_generate_ca_cert')
    def test_generate_certificates_without_name(self, mock_generate_ca_cert,
                                                mock_generate_client_cert):
        expected_ca_name = 'ca-uuid'
        mock_cluster = mock.MagicMock()
        mock_cluster.name = None
        mock_cluster.uuid = expected_ca_name

        self._test_generate_certificates(expected_ca_name,
                                         mock_cluster,
                                         mock_generate_ca_cert,
                                         mock_generate_client_cert)

    @mock.patch('magnum.conductor.handlers.common.cert_manager.'
                '_get_issuer_name')
    def test_generate_certificates_with_error(self, mock_get_issuer_name):
        mock_cluster = mock.MagicMock()
        mock_get_issuer_name.side_effect = exception.MagnumException()

        self.assertRaises(exception.CertificatesToClusterFailed,
                          cert_manager.generate_certificates_to_cluster,
                          mock_cluster)

    @mock.patch('magnum.common.x509.operations.sign')
    def test_sign_node_certificate(self, mock_x509_sign):
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = "mock_cluster_uuid"
        mock_ca_cert = mock.MagicMock()
        mock_ca_cert.get_private_key.return_value = mock.sentinel.priv_key
        passphrase = mock.sentinel.passphrase
        mock_ca_cert.get_private_key_passphrase.return_value = passphrase
        self.CertManager.get_cert.return_value = mock_ca_cert
        mock_csr = mock.MagicMock()
        mock_x509_sign.return_value = mock.sentinel.signed_cert

        cluster_ca_cert = cert_manager.sign_node_certificate(mock_cluster,
                                                             mock_csr)

        self.CertManager.get_cert.assert_called_once_with(
            mock_cluster.ca_cert_ref, resource_ref=mock_cluster.uuid,
            context=None)
        mock_x509_sign.assert_called_once_with(mock_csr, mock_cluster.name,
                                               mock.sentinel.priv_key,
                                               passphrase)
        self.assertEqual(mock.sentinel.signed_cert, cluster_ca_cert)

    @mock.patch('magnum.common.x509.operations.sign')
    def test_sign_node_certificate_without_cluster_name(self, mock_x509_sign):
        mock_cluster = mock.MagicMock()
        mock_cluster.name = None
        mock_cluster.uuid = "mock_cluster_uuid"
        mock_ca_cert = mock.MagicMock()
        mock_ca_cert.get_private_key.return_value = mock.sentinel.priv_key
        passphrase = mock.sentinel.passphrase
        mock_ca_cert.get_private_key_passphrase.return_value = passphrase
        self.CertManager.get_cert.return_value = mock_ca_cert
        mock_csr = mock.MagicMock()
        mock_x509_sign.return_value = mock.sentinel.signed_cert

        cluster_ca_cert = cert_manager.sign_node_certificate(mock_cluster,
                                                             mock_csr)

        self.CertManager.get_cert.assert_called_once_with(
            mock_cluster.ca_cert_ref, resource_ref=mock_cluster.uuid,
            context=None)
        mock_x509_sign.assert_called_once_with(mock_csr, mock_cluster.uuid,
                                               mock.sentinel.priv_key,
                                               passphrase)
        self.assertEqual(mock.sentinel.signed_cert, cluster_ca_cert)

    def test_get_cluster_ca_certificate(self):
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = "mock_cluster_uuid"
        mock_ca_cert = mock.MagicMock()
        self.CertManager.get_cert.return_value = mock_ca_cert

        cluster_ca_cert = cert_manager.get_cluster_ca_certificate(mock_cluster)

        self.CertManager.get_cert.assert_called_once_with(
            mock_cluster.ca_cert_ref, resource_ref=mock_cluster.uuid,
            context=None)
        self.assertEqual(mock_ca_cert, cluster_ca_cert)

    def test_delete_certtificate(self):
        mock_delete_cert = self.CertManager.delete_cert
        expected_cert_ref = 'cert_ref'
        expected_ca_cert_ref = 'ca_cert_ref'
        mock_cluster = mock.MagicMock()
        mock_cluster.uuid = "mock_cluster_uuid"
        mock_cluster.ca_cert_ref = expected_ca_cert_ref
        mock_cluster.magnum_cert_ref = expected_cert_ref

        cert_manager.delete_certificates_from_cluster(mock_cluster)
        mock_delete_cert.assert_any_call(expected_ca_cert_ref,
                                         resource_ref=mock_cluster.uuid,
                                         context=None)
        mock_delete_cert.assert_any_call(expected_cert_ref,
                                         resource_ref=mock_cluster.uuid,
                                         context=None)

    def test_delete_certtificate_if_raise_error(self):
        mock_delete_cert = self.CertManager.delete_cert
        expected_cert_ref = 'cert_ref'
        expected_ca_cert_ref = 'ca_cert_ref'
        mock_cluster = mock.MagicMock()
        mock_cluster.ca_cert_ref = expected_ca_cert_ref
        mock_cluster.magnum_cert_ref = expected_cert_ref

        mock_delete_cert.side_effect = ValueError

        cert_manager.delete_certificates_from_cluster(mock_cluster)
        mock_delete_cert.assert_any_call(expected_ca_cert_ref,
                                         resource_ref=mock_cluster.uuid,
                                         context=None)
        mock_delete_cert.assert_any_call(expected_cert_ref,
                                         resource_ref=mock_cluster.uuid,
                                         context=None)

    def test_delete_certtificate_without_cert_ref(self):
        mock_delete_cert = self.CertManager.delete_cert
        mock_cluster = mock.MagicMock()
        mock_cluster.ca_cert_ref = None
        mock_cluster.magnum_cert_ref = None

        cert_manager.delete_certificates_from_cluster(mock_cluster)
        self.assertFalse(mock_delete_cert.called)
