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

import time

from oslo_config import cfg
from requests import exceptions as req_exceptions

from magnum.common import docker_utils
from magnum.tests.functional.python_client_base import BayTest
from magnumclient.common.apiclient import exceptions


CONF = cfg.CONF
CONF.import_opt('docker_remote_api_version', 'magnum.common.docker_utils',
                group='docker')
CONF.import_opt('default_timeout', 'magnum.common.docker_utils',
                group='docker')


class TestSwarmAPIs(BayTest):
    """This class will cover swarm bay basic functional testing.

       Will test all kinds of container action with tls_disabled=False mode.
    """

    coe = "swarm"
    baymodel_kwargs = {
        "tls_disabled": False,
        "network_driver": None,
        "volume_driver": None,
        "fixed_network": '192.168.0.0/24',
        "dns_nameserver": '8.8.8.8',
        "labels": {}
    }

    @classmethod
    def setUpClass(cls):
        super(TestSwarmAPIs, cls).setUpClass()
        cls.bay_is_ready = None

    def setUp(self):
        super(TestSwarmAPIs, self).setUp()
        if self.bay_is_ready is True:
            return
        # Note(eliqiao): In our test cases, docker client or magnum client will
        # try to connect to swarm service which is running on master node,
        # the endpoint is bay.api_address(listen port is included), but the
        # service is not ready right after the bay was created, sleep for an
        # acceptable time to wait for service being started.
        # This is required, without this any api call will fail as
        # 'ConnectionError: [Errno 111] Connection refused'.
        msg = ("If you see this error in the functional test, it means "
               "the docker service took too long to come up. This may not "
               "be an actual error, so an option is to rerun the "
               "functional test.")
        if self.bay_is_ready is False:
            # In such case, no need to test below cases on gate, raise a
            # meanful exception message to indicate ca setup failed after
            # bay creation, better to do a `recheck`
            # We don't need to test since bay is not ready.
            raise Exception(msg)

        # We don't set bay_is_ready in such case
        self.bay_is_ready = False

        url = self.cs.bays.get(self.bay.uuid).api_address

        # Note(eliqiao): docker_utils.CONF.docker.default_timeout is 10,
        # tested this default configure option not works on gate, it will
        # cause container creation failed due to time out.
        # Debug more found that we need to pull image when the first time to
        # create a container, set it as 180s.

        docker_api_time_out = 180
        self.docker_client = docker_utils.DockerHTTPClient(
            url,
            CONF.docker.docker_remote_api_version,
            docker_api_time_out,
            client_key=self.key_file,
            client_cert=self.cert_file,
            ca_cert=self.ca_file)

        self.docker_client_non_tls = docker_utils.DockerHTTPClient(
            url,
            CONF.docker.docker_remote_api_version,
            docker_api_time_out)

        for i in range(150):
            try:
                self.docker_client.containers()
                # Note(eliqiao): Right after the connection is ready, wait
                # for a while (at least 5s) to aovid this error:
                # docker.errors.APIError: 500 Server Error: Internal
                # Server Error ("No healthy node available in the cluster")
                time.sleep(10)
                self.bay_is_ready = True
                break
            except req_exceptions.ConnectionError:
                time.sleep(2)

        if self.bay_is_ready is False:
            raise Exception(msg)

    def _create_container(self, **kwargs):
        name = kwargs.get('name', 'test_container')
        image = kwargs.get('image', 'docker.io/cirros')
        command = kwargs.get('command', 'ping -c 1000 8.8.8.8')
        return self.docker_client.create_container(name=name,
                                                   image=image,
                                                   command=command)

    def test_start_stop_container_from_api(self):
        # Leverage docker client to create a container on the bay we created,
        # and try to start and stop it then delete it.

        resp = self._create_container(name="test_api_start_stop",
                                      image="docker.io/cirros",
                                      command="ping -c 1000 8.8.8.8")

        self.assertIsNotNone(resp)
        container_id = resp.get('Id')
        self.docker_client.start(container=container_id)

        resp = self.docker_client.containers()
        self.assertIsNotNone(resp)
        resp = self.docker_client.inspect_container(container=container_id)
        self.assertTrue(resp['State']['Running'])

        self.docker_client.stop(container=container_id)
        resp = self.docker_client.inspect_container(container=container_id)
        self.assertFalse(resp['State']['Running'])

        self.docker_client.remove_container(container=container_id)
        resp = self.docker_client.containers()
        self.assertEqual([], resp)

    def test_access_with_non_tls_client(self):
        self.assertRaises(req_exceptions.SSLError,
                          self.docker_client_non_tls.containers)

    def test_start_stop_container_from_cs(self):
        # Leverage Magnum client to create a container on the bay we created,
        # and try to start and stop it then delete it.

        container = self.cs.containers.create(name="test_cs_start_stop",
                                              image="docker.io/cirros",
                                              bay_uuid=self.bay.uuid,
                                              command='ping -c 1000 8.8.8.8')
        self.assertIsNotNone(container)
        container_uuid = container.uuid

        resp = self.cs.containers.start(container_uuid)
        self.assertEqual(200, resp[0].status_code)

        container = self.cs.containers.get(container_uuid)
        self.assertEqual('Running', container.status)

        resp = self.cs.containers.stop(container_uuid)
        container = self.cs.containers.get(container_uuid)
        self.assertEqual('Stopped', container.status)

        container = self.cs.containers.delete(container_uuid)
        self.assertRaises(exceptions.NotFound,
                          self.cs.containers.get, container_uuid)
