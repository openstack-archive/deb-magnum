# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest import clients
from tempest.common import credentials_factory as common_creds

from magnum.tests.functional.api.v1.clients import bay_client
from magnum.tests.functional.api.v1.clients import baymodel_client
from magnum.tests.functional.api.v1.clients import cert_client
from magnum.tests.functional.api.v1.clients import magnum_service_client
from magnum.tests.functional.common import client
from magnum.tests.functional.common import config


class Manager(clients.Manager):
    def __init__(self, credentials=None, request_type=None):
        if not credentials:
            credentials = common_creds.get_configured_credentials(
                'identity_admin')
        super(Manager, self).__init__(credentials, 'container')
        self.auth_provider.orig_base_url = self.auth_provider.base_url
        self.auth_provider.base_url = self.bypassed_base_url
        if request_type == 'baymodel':
            self.client = baymodel_client.BayModelClient(self.auth_provider)
        elif request_type == 'bay':
            self.client = bay_client.BayClient(self.auth_provider)
        elif request_type == 'cert':
            self.client = cert_client.CertClient(self.auth_provider)
        elif request_type == 'service':
            self.client = magnum_service_client.MagnumServiceClient(
                self.auth_provider)
        else:
            self.client = client.MagnumClient(self.auth_provider)

    def bypassed_base_url(self, filters, auth_data=None):
        if config.Config.magnum_url and filters['service'] == 'container':
            return config.Config.magnum_url
        return self.auth_provider.orig_base_url(filters, auth_data=auth_data)


class DefaultManager(Manager):
    def __init__(self, credentials, request_type=None):
        super(DefaultManager, self).__init__(credentials, request_type)


class AltManager(Manager):
    def __init__(self, credentials, request_type=None):
        super(AltManager, self).__init__(credentials, request_type)


class AdminManager(Manager):
    def __init__(self, credentials, request_type=None):
        super(AdminManager, self).__init__(credentials, request_type)
