.. _quickstart:

=====================
Developer Quick-Start
=====================

This is a quick walkthrough to get you started developing code for magnum.
This assumes you are already familiar with submitting code reviews to an
OpenStack project.

.. seealso::

   http://docs.openstack.org/infra/manual/developers.html

Setup Dev Environment
=====================

Install OS-specific prerequisites::

    # Ubuntu/Debian:
    sudo apt-get update
    sudo apt-get install -y python-dev libssl-dev libxml2-dev \
                            libmysqlclient-dev libxslt-dev libpq-dev git \
                            libffi-dev gettext build-essential python3.4-dev

    # Fedora/RHEL:
    sudo yum install -y python-devel openssl-devel mysql-devel \
                        libxml2-devel libxslt-devel postgresql-devel git \
                        libffi-devel gettext gcc

    # openSUSE/SLE 12:
    sudo zypper --non-interactive install git libffi-devel \
                        libmysqlclient-devel libopenssl-devel libxml2-devel \
                        libxslt-devel postgresql-devel python-devel \
                        gettext-runtime

Install pip::

    curl -s https://bootstrap.pypa.io/get-pip.py | sudo python

Install common prerequisites::

    sudo pip install virtualenv flake8 tox testrepository git-review

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv

Magnum source code should be pulled directly from git::

    # from your home or source directory
    cd ~
    git clone https://git.openstack.org/openstack/magnum
    cd magnum

All unit tests should be run using tox. To run magnum's entire test suite::

    # run all tests (unit and pep8)
    tox

To run a specific test, use a positional argument for the unit tests::

    # run a specific test for Python 2.7
    tox -epy27 -- test_conductor

You may pass options to the test programs using positional arguments::

    # run all the Python 2.7 unit tests (in parallel!)
    tox -epy27 -- --parallel

To run only the pep8/flake8 syntax and style checks::

    tox -epep8

To run unit test coverage and check percentage of code covered::

    tox -e cover

To discover and interact with templates, please refer to
`<http://docs.openstack.org/developer/magnum/dev/bay-template-example.html>`_

Exercising the Services Using Devstack
======================================

Devstack can be configured to enable magnum support. It is easy to develop
magnum with the devstack environment. Magnum depends on nova, glance, heat and
neutron to create and schedule virtual machines to simulate bare-metal (full
bare-metal support is under active development).

**NOTE:** Running devstack within a virtual machine with magnum enabled is not
recommended at this time.

This session has only been tested on Ubuntu 14.04 (Trusty) and Fedora 20/21.
We recommend users to select one of them if it is possible.

For in-depth guidance on adding magnum manually to a devstack instance, please
refer to the `<http://docs.openstack.org/developer/magnum/dev/manual-devstack.html>`_

Clone devstack::

    # Create a root directory for devstack if needed
    sudo mkdir -p /opt/stack
    sudo chown $USER /opt/stack

    git clone https://git.openstack.org/openstack-dev/devstack /opt/stack/devstack

We will run devstack with minimal local.conf settings required to enable
magnum, heat, and neutron (neutron is enabled by default in devstack since
Kilo, and heat must be enabled by yourself)::

    cat > /opt/stack/devstack/local.conf << END
    [[local|localrc]]
    DATABASE_PASSWORD=password
    RABBIT_PASSWORD=password
    SERVICE_TOKEN=password
    SERVICE_PASSWORD=password
    ADMIN_PASSWORD=password
    # magnum requires the following to be set correctly
    PUBLIC_INTERFACE=eth1

    # Enable barbican service and use it to store TLS certificates
    # For details http://docs.openstack.org/developer/magnum/dev/tls.html
    enable_plugin barbican https://git.openstack.org/openstack/barbican
    enable_plugin heat https://git.openstack.org/openstack/heat
    enable_plugin neutron-lbaas https://git.openstack.org/openstack/neutron-lbaas
    enable_plugin octavia https://git.openstack.org/openstack/octavia

    # Enable magnum plugin after dependent plugins
    enable_plugin magnum https://git.openstack.org/openstack/magnum

    # Optional:  uncomment to enable the Magnum UI plugin in Horizon
    #enable_plugin magnum-ui https://github.com/openstack/magnum-ui

    # Disable LBaaS(v1) service
    disable_service q-lbaas
    # Enable LBaaS(v2) services
    enable_service q-lbaasv2
    enable_service octavia
    enable_service o-cw
    enable_service o-hk
    enable_service o-hm
    enable_service o-api
    VOLUME_BACKING_FILE_SIZE=20G
    END

**NOTE:** Update PUBLIC_INTERFACE as appropriate for your system.
**NOTE:** Enable heat plugin is necessary.

Optionally, you can enable ceilometer in devstack. If ceilometer is enabled,
magnum will periodically send metrics to ceilometer::

    cat >> /opt/stack/devstack/local.conf << END
    enable_plugin ceilometer https://git.openstack.org/openstack/ceilometer
    END

If you want to deploy Docker Registry 2.0 in your cluster, you should enable
swift in devstack::

    cat >> /opt/stack/devstack/local.conf << END
    enable_service s-proxy
    enable_service s-object
    enable_service s-container
    enable_service s-account
    END

More devstack configuration information can be found at
http://docs.openstack.org/developer/devstack/configuration.html

More neutron configuration information can be found at
http://docs.openstack.org/developer/devstack/guides/neutron.html

Run devstack::

    cd /opt/stack/devstack
    ./stack.sh

**NOTE:** This will take a little extra time when the Fedora Atomic micro-OS
image is downloaded for the first time.

At this point, two magnum process (magnum-api and magnum-conductor) will be
running on devstack screens. If you make some code changes and want to
test their effects, just stop and restart magnum-api and/or magnum-conductor.

Prepare your session to be able to use the various openstack clients including
magnum, neutron, and glance. Create a new shell, and source the devstack openrc
script::

    source /opt/stack/devstack/openrc admin admin

Magnum has been tested with the Fedora Atomic micro-OS and CoreOS. Magnum will
likely work with other micro-OS platforms, but each requires individual
support in the heat template.

The Fedora Atomic micro-OS image will automatically be added to glance.  You
can add additional images manually through glance. To verify the image created
when installing devstack use::

    glance -v image-list

    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+----------------------------------+
    | ID                                   | Name                            | Disk_format | Container_format | Size      | Status | Owner                            |
    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+----------------------------------+
    | 090de3a2-2c0c-42d5-b5a3-cfcddd6d011b | cirros-0.3.4-x86_64-uec         | ami         | ami              | 25165824  | active | f98b9727094d40c78b1ed40e3bc91e80 |
    | 9501d296-f0aa-4c0e-bc24-2a680f8741f0 | cirros-0.3.4-x86_64-uec-kernel  | aki         | aki              | 4979632   | active | f98b9727094d40c78b1ed40e3bc91e80 |
    | 01478d1a-59e0-4f36-b69e-0eaf5821ee46 | cirros-0.3.4-x86_64-uec-ramdisk | ari         | ari              | 3740163   | active | f98b9727094d40c78b1ed40e3bc91e80 |
    | f14d6ee3-9e53-4f22-ba42-44e95810c294 | fedora-atomic-newton            | qcow2       | bare             | 507928064 | active | f98b9727094d40c78b1ed40e3bc91e80 |
    +--------------------------------------+---------------------------------+-------------+------------------+-----------+--------+----------------------------------+

To list the available commands and resources for magnum, use::

    magnum help

To list out the health of the internal services, namely conductor, of magnum,
use::

    magnum service-list

    +----+---------------------------------------+------------------+-------+----------+-----------------+---------------------------+---------------------------+
    | id | host                                  | binary           | state | disabled | disabled_reason | created_at                | updated_at                |
    +----+---------------------------------------+------------------+-------+----------+-----------------+---------------------------+---------------------------+
    | 1  | oxy-dev.hq1-0a5a3c02.hq1.abcde.com    | magnum-conductor | up    |          | -               | 2016-08-31T10:03:36+00:00 | 2016-08-31T10:11:41+00:00 |
    +----+---------------------------------------+------------------+-------+----------+-----------------+---------------------------+---------------------------+

Create a keypair for use with the ClusterTemplate::

    test -f ~/.ssh/id_rsa.pub || ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub testkey

Building a Kubernetes Cluster - Based on Fedora Atomic
======================================================

Create a ClusterTemplate. This is similar in nature to a flavor and describes
to magnum how to construct the cluster. The ClusterTemplate specifies a Fedora
Atomic image so the clusters which use this ClusterTemplate will be based on
Fedora Atomic. The COE (Container Orchestration Engine) and keypair need to
be specified as well::

    magnum cluster-template-create --name k8s-cluster-template \
                           --image-id fedora-atomic-newton \
                           --keypair-id testkey \
                           --external-network-id public \
                           --dns-nameserver 8.8.8.8 \
                           --flavor-id m1.small \
                           --docker-volume-size 5 \
                           --network-driver flannel \
                           --coe kubernetes

Create a cluster. Use the ClusterTemplate name as a template for cluster
creation. This cluster will result in one master kubernetes node and one minion
node::

    magnum cluster-create --name k8s-cluster \
                          --cluster-template k8s-cluster-template \
                          --node-count 1

Clusters will have an initial status of CREATE_IN_PROGRESS.  Magnum will update
the status to CREATE_COMPLETE when it is done creating the cluster.  Do not
create containers, pods, services, or replication controllers before magnum
finishes creating the cluster. They will likely not be created, and may cause
magnum to become confused.

The existing clusters can be listed as follows::

    magnum cluster-list

    +--------------------------------------+-------------+------------+--------------+-----------------+
    | uuid                                 | name        | node_count | master_count | status          |
    +--------------------------------------+-------------+------------+--------------------------------+
    | 9dccb1e6-02dc-4e2b-b897-10656c5339ce | k8s-cluster | 1          | 1            | CREATE_COMPLETE |
    +--------------------------------------+-------------+------------+--------------+-----------------+

More detailed information for a given cluster is obtained via::

    magnum cluster-show k8s-cluster

After a cluster is created, you can dynamically add/remove node(s) to/from the
cluster by updating the node_count attribute. For example, to add one more
node::

    magnum cluster-update k8s-cluster replace node_count=2

Clusters in the process of updating will have a status of UPDATE_IN_PROGRESS.
Magnum will update the status to UPDATE_COMPLETE when it is done updating
the cluster.

**NOTE:** Reducing node_count will remove all the existing pods on the nodes
that are deleted. If you choose to reduce the node_count, magnum will first
try to remove empty nodes with no pods running on them. If you reduce
node_count by more than the number of empty nodes, magnum must remove nodes
that have running pods on them. This action will delete those pods. We
strongly recommend using a replication controller before reducing the
node_count so any removed pods can be automatically recovered on your
remaining nodes.

Heat can be used to see detailed information on the status of a stack or
specific cluster:

To check the list of all cluster stacks::

    openstack stack list

To check an individual cluster's stack::

    openstack stack show <stack-name or stack_id>

Monitoring cluster status in detail (e.g., creating, updating)::

    CLUSTER_HEAT_NAME=$(openstack stack list | \
                        awk "/\sk8s-cluster-/{print \$4}")
    echo ${CLUSTER_HEAT_NAME}
    openstack stack resource list ${CLUSTER_HEAT_NAME}

Building a Kubernetes Cluster - Based on CoreOS
===============================================

You can create a Kubernetes cluster based on CoreOS as an alternative to
Atomic. First, download the official CoreOS image::

    wget http://beta.release.core-os.net/amd64-usr/1153.4.0/coreos_production_openstack_image.img.bz2
    bunzip2 coreos_production_openstack_image.img.bz2

Upload the image to glance::

    glance image-create --name CoreOS  \
                        --visibility public \
                        --disk-format=qcow2 \
                        --container-format=bare \
                        --os-distro=coreos \
                        --file=coreos_production_openstack_image.img

Create a CoreOS Kubernetes ClusterTemplate, which is similar to the Atomic
Kubernetes ClusterTemplate, except for pointing to a different image::

    magnum cluster-template-create --name k8s-cluster-template-coreos \
                           --image-id CoreOS \
                           --keypair-id testkey \
                           --external-network-id public \
                           --dns-nameserver 8.8.8.8 \
                           --flavor-id m1.small \
                           --network-driver flannel \
                           --coe kubernetes

Create a CoreOS Kubernetes cluster. Use the CoreOS ClusterTemplate as a
template for cluster creation::

    magnum cluster-create --name k8s-cluster \
                      --cluster-template k8s-cluster-template-coreos \
                      --node-count 2

Using a Kubernetes Cluster
==========================

**NOTE:** For the following examples, only one minion node is required in the
k8s cluster created previously.

Kubernetes provides a number of examples you can use to check that things are
working. You may need to clone kubernetes using::

    wget https://github.com/kubernetes/kubernetes/releases/download/v1.0.1/kubernetes.tar.gz
    tar -xvzf kubernetes.tar.gz
    sudo cp -a kubernetes/platforms/linux/amd64/kubectl /usr/bin/kubectl

We first need to setup the certs to allow Kubernetes to authenticate our
connection.   Please refer to
`<http://docs.openstack.org/developer/magnum/userguide.html#transport-layer-security>`_
for more info on using TLS keys/certs which are setup below.

To generate an RSA key, you will use the 'genrsa' command of the 'openssl'
tool.::

    openssl genrsa -out client.key 4096

To generate a CSR for client authentication, openssl requires a config file
that specifies a few values.::

    $ cat > client.conf << END
    [req]
    distinguished_name = req_distinguished_name
    req_extensions     = req_ext
    prompt = no
    [req_distinguished_name]
    CN = Your Name
    [req_ext]
    extendedKeyUsage = clientAuth
    END

Once you have client.conf, you can run the openssl 'req' command to generate
the CSR.::

    openssl req -new -days 365 \
        -config client.conf \
        -key client.key \
        -out client.csr

Now that you have your client CSR, you can use the Magnum CLI to send it off
to Magnum to get it signed and also download the signing cert.::

    magnum ca-sign --cluster k8s-cluster --csr client.csr > client.crt
    magnum ca-show --cluster k8s-cluster > ca.crt

Here's how to set up the replicated redis example. Now we create a pod for the
redis-master::

    KUBERNETES_URL=$(magnum cluster-show k8s-cluster |
                     awk '/ api_address /{print $4}')

    # Set kubectl to use the correct certs
    kubectl config set-cluster k8s-cluster --server=${KUBERNETES_URL} \
        --certificate-authority=$(pwd)/ca.crt
    kubectl config set-credentials client --certificate-authority=$(pwd)/ca.crt \
        --client-key=$(pwd)/client.key --client-certificate=$(pwd)/client.crt
    kubectl config set-context k8s-cluster --cluster=k8s-cluster --user=client
    kubectl config use-context k8s-cluster

    # Test the cert and connection works
    kubectl version

    cd kubernetes/examples/redis
    kubectl create -f ./redis-master.yaml

Now create a service to provide a discoverable endpoint for the redis
sentinels in the cluster::

    kubectl create -f ./redis-sentinel-service.yaml

To make it a replicated redis cluster create replication controllers for the
redis slaves and sentinels::

    sed -i 's/\(replicas: \)1/\1 2/' redis-controller.yaml
    kubectl create -f ./redis-controller.yaml

    sed -i 's/\(replicas: \)1/\1 2/' redis-sentinel-controller.yaml
    kubectl create -f ./redis-sentinel-controller.yaml

Full lifecycle and introspection operations for each object are supported.
For example, magnum cluster-create, magnum cluster-template-delete.

Now there are four redis instances (one master and three slaves) running
across the cluster, replicating data between one another.

Run the cluster-show command to get the IP of the cluster host on which the
redis-master is running::

    magnum cluster-show k8s-cluster

    +--------------------+------------------------------------------------------------+
    | Property           | Value                                                      |
    +--------------------+------------------------------------------------------------+
    | status             | CREATE_COMPLETE                                            |
    | uuid               | cff82cd0-189c-4ede-a9cb-2c0af6997709                       |
    | stack_id           | 7947844a-8e18-4c79-b591-ecf0f6067641                       |
    | status_reason      | Stack CREATE completed successfully                        |
    | created_at         | 2016-05-26T17:45:57+00:00                                  |
    | updated_at         | 2016-05-26T17:50:02+00:00                                  |
    | create_timeout     | 60                                                         |
    | api_address        | https://172.24.4.4:6443                                    |
    | coe_version        | v1.2.0                                                     |
    | cluster_template_id| e73298e7-e621-4d42-b35b-7a1952b97158                       |
    | master_addresses   | ['172.24.4.6']                                             |
    | node_count         | 1                                                          |
    | node_addresses     | ['172.24.4.5']                                             |
    | master_count       | 1                                                          |
    | container_version  | 1.9.1                                                      |
    | discovery_url      | https://discovery.etcd.io/4caaa65f297d4d49ef0a085a7aecf8e0 |
    | name               | k8s-cluster                                                |
    +--------------------+------------------------------------------------------------+

The output here indicates the redis-master is running on the cluster host with
IP address 172.24.4.5. To access the redis master::

    ssh fedora@172.24.4.5
    REDIS_ID=$(sudo docker ps | grep redis:v1 | grep k8s_master | awk '{print $1}')
    sudo docker exec -i -t $REDIS_ID redis-cli

    127.0.0.1:6379> set replication:test true
    OK
    ^D

    exit  # Log out of the host

Log into one of the other container hosts and access a redis slave from it.
You can use `nova list` to enumerate the kube-minions. For this example we
will use the same host as above::

    ssh fedora@172.24.4.5
    REDIS_ID=$(sudo docker ps | grep redis:v1 | grep k8s_redis | awk '{print $1}')
    sudo docker exec -i -t $REDIS_ID redis-cli

    127.0.0.1:6379> get replication:test
    "true"
    ^D

    exit  # Log out of the host

Additional useful commands from a given minion::

    sudo docker ps  # View Docker containers on this minion
    kubectl get pods  # Get pods
    kubectl get rc  # Get replication controllers
    kubectl get svc  # Get services
    kubectl get nodes  # Get nodes

After you finish using the cluster, you want to delete it. A cluster can be
deleted as follows::

    magnum cluster-delete k8s-cluster

Building and Using a Swarm Cluster
==================================

Create a ClusterTemplate. It is very similar to the Kubernetes ClusterTemplate,
except for the absence of some Kubernetes-specific arguments and the use of
'swarm' as the COE::

    magnum cluster-template-create --name swarm-cluster-template \
                           --image-id fedora-atomic-newton \
                           --keypair-id testkey \
                           --external-network-id public \
                           --dns-nameserver 8.8.8.8 \
                           --flavor-id m1.small \
                           --docker-volume-size 5 \
                           --coe swarm

**NOTE:** If you are using Magnum behind a firewall then see:

.. _Using_Magnum_Behind_Firewall:

http://docs.openstack.org/developer/magnum/magnum-proxy.html

Finally, create the cluster. Use the ClusterTemplate 'swarm-cluster-template'
as a template for cluster creation. This cluster will result in one swarm
manager node and two extra agent nodes::

    magnum cluster-create --name swarm-cluster \
                          --cluster-template swarm-cluster-template \
                          --node-count 2

Now that we have a swarm cluster we can start interacting with it::

    magnum cluster-show swarm-cluster

    +--------------------+------------------------------------------------------------+
    | Property           | Value                                                      |
    +--------------------+------------------------------------------------------------+
    | status             | CREATE_COMPLETE                                            |
    | uuid               | eda91c1e-6103-45d4-ab09-3f316310fa8e                       |
    | stack_id           | 7947844a-8e18-4c79-b591-ecf0f6067641                       |
    | status_reason      | Stack CREATE completed successfully                        |
    | created_at         | 2015-04-20T19:05:27+00:00                                  |
    | updated_at         | 2015-04-20T19:06:08+00:00                                  |
    | create_timeout     | 60                                                         |
    | api_address        | https://172.24.4.4:6443                                    |
    | coe_version        | 1.0.0                                                      |
    | cluster_template_id| e73298e7-e621-4d42-b35b-7a1952b97158                       |
    | master_addresses   | ['172.24.4.6']                                             |
    | node_count         | 2                                                          |
    | node_addresses     | ['172.24.4.5']                                             |
    | master_count       | 1                                                          |
    | container_version  | 1.9.1                                                      |
    | discovery_url      | https://discovery.etcd.io/4caaa65f297d4d49ef0a085a7aecf8e0 |
    | name               | swarm-cluster                                              |
    +--------------------+------------------------------------------------------------+

We now need to setup the docker CLI to use the swarm cluster we have created
with the appropriate credentials.

Create a dir to store certs and cd into it. The `DOCKER_CERT_PATH` env variable
is consumed by docker which expects ca.pem, key.pem and cert.pem to be in that
directory.::

    export DOCKER_CERT_PATH=~/.docker
    mkdir -p ${DOCKER_CERT_PATH}
    cd ${DOCKER_CERT_PATH}

Generate an RSA key.::

    openssl genrsa -out key.pem 4096

Create openssl config to help generated a CSR.::

    $ cat > client.conf << END
    [req]
    distinguished_name = req_distinguished_name
    req_extensions     = req_ext
    prompt = no
    [req_distinguished_name]
    CN = Your Name
    [req_ext]
    extendedKeyUsage = clientAuth
    END

Run the openssl 'req' command to generate the CSR.::

    openssl req -new -days 365 \
        -config client.conf \
        -key key.pem \
        -out client.csr

Now that you have your client CSR use the Magnum CLI to get it signed and also
download the signing cert.::

    magnum ca-sign --cluster swarm-cluster --csr client.csr > cert.pem
    magnum ca-show --cluster swarm-cluster > ca.pem

Set the CLI to use TLS . This env var is consumed by docker.::

    export DOCKER_TLS_VERIFY="1"

Set the correct host to use which is the public ip address of swarm API server
endpoint. This env var is consumed by docker.::

    export DOCKER_HOST=$(magnum cluster-show swarm-cluster | awk '/ api_address /{print substr($4,7)}')

Next we will create a container in this swarm cluster. This container will ping
the address 8.8.8.8 four times::

    docker run --rm -it cirros:latest ping -c 4 8.8.8.8

You should see a similar output to::

    PING 8.8.8.8 (8.8.8.8): 56 data bytes
    64 bytes from 8.8.8.8: seq=0 ttl=40 time=25.513 ms
    64 bytes from 8.8.8.8: seq=1 ttl=40 time=25.348 ms
    64 bytes from 8.8.8.8: seq=2 ttl=40 time=25.226 ms
    64 bytes from 8.8.8.8: seq=3 ttl=40 time=25.275 ms

    --- 8.8.8.8 ping statistics ---
    4 packets transmitted, 4 packets received, 0% packet loss
    round-trip min/avg/max = 25.226/25.340/25.513 ms

Building and Using a Mesos Cluster
==================================

Provisioning a mesos cluster requires a Ubuntu-based image with some packages
pre-installed. To build and upload such image, please refer to
`<http://docs.openstack.org/developer/magnum/userguide.html#building-mesos-image>`_

Alternatively, you can download and upload a pre-built image::

    wget https://fedorapeople.org/groups/magnum/ubuntu-mesos-newton.qcow2
    glance image-create --name ubuntu-mesos --visibility public \
                        --disk-format=qcow2 --container-format=bare \
                        --os-distro=ubuntu --file=ubuntu-mesos-newton.qcow2

Then, create a ClusterTemplate by using 'mesos' as the COE, with the rest of
arguments similar to the Kubernetes ClusterTemplate::

    magnum cluster-template-create --name mesos-cluster-template --image-id ubuntu-mesos \
                           --keypair-id testkey \
                           --external-network-id public \
                           --dns-nameserver 8.8.8.8 \
                           --flavor-id m1.small \
                           --coe mesos

Finally, create the cluster. Use the ClusterTemplate 'mesos-cluster-template'
as a template for cluster creation. This cluster will result in one mesos
master node and two mesos slave nodes::

    magnum cluster-create --name mesos-cluster \
                          --cluster-template mesos-cluster-template \
                          --node-count 2

Now that we have a mesos cluster we can start interacting with it. First we
need to make sure the cluster's status is 'CREATE_COMPLETE'::

    $ magnum cluster-show mesos-cluster

    +--------------------+------------------------------------------------------------+
    | Property           | Value                                                      |
    +--------------------+------------------------------------------------------------+
    | status             | CREATE_COMPLETE                                            |
    | uuid               | ff727f0d-72ca-4e2b-9fef-5ec853d74fdf                       |
    | stack_id           | 7947844a-8e18-4c79-b591-ecf0f6067641                       |
    | status_reason      | Stack CREATE completed successfully                        |
    | created_at         | 2015-06-09T20:21:43+00:00                                  |
    | updated_at         | 2015-06-09T20:28:18+00:00                                  |
    | create_timeout     | 60                                                         |
    | api_address        | https://172.24.4.115:6443                                  |
    | coe_version        | -                                                          |
    | cluster_template_id| 92dbda62-32d4-4435-88fc-8f42d514b347                       |
    | master_addresses   | ['172.24.4.115']                                           |
    | node_count         | 2                                                          |
    | node_addresses     | ['172.24.4.116', '172.24.4.117']                           |
    | master_count       | 1                                                          |
    | container_version  | 1.9.1                                                      |
    | discovery_url      | None                                                       |
    | name               | mesos-cluster                                              |
    +--------------------+------------------------------------------------------------+

Next we will create a container in this cluster by using the REST API of
Marathon. This container will ping the address 8.8.8.8::

    $ cat > mesos.json << END
    {
      "container": {
        "type": "DOCKER",
        "docker": {
          "image": "cirros"
        }
      },
      "id": "ubuntu",
      "instances": 1,
      "cpus": 0.5,
      "mem": 512,
      "uris": [],
      "cmd": "ping 8.8.8.8"
    }
    END
    $ MASTER_IP=$(magnum cluster-show mesos-cluster | awk '/ api_address /{print $4}')
    $ curl -X POST -H "Content-Type: application/json" \
        http://${MASTER_IP}:8080/v2/apps -d@mesos.json

To check application and task status::

    $ curl http://${MASTER_IP}:8080/v2/apps
    $ curl http://${MASTER_IP}:8080/v2/tasks

You can access to the Mesos web page at \http://<master>:5050/ and Marathon web
console at \http://<master>:8080/.

Building Developer Documentation
================================

To build the documentation locally (e.g., to test documentation changes
before uploading them for review) chdir to the magnum root folder and
run tox::

    tox -edocs

**NOTE:** The first time you run this will take some extra time as it
creates a virtual environment to run in.

When complete, the documentation can be accessed from::

    doc/build/html/index.html
