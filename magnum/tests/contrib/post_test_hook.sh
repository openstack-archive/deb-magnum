#!/bin/bash -x
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

# This script is executed inside post_test_hook function in devstack gate.

# Sleep some time until all services are starting
sleep 5

# Check if a function already exists
function function_exists {
    declare -f -F $1 > /dev/null
}

# Set up all necessary test data
function create_test_data {
    # First we test Magnum's command line to see if we can stand up
    # a baymodel, bay and a pod

    coe=$1
    special=$2
    if [ $coe == 'mesos' ]; then
        local image_name="ubuntu-14.04"
        local container_format="bare"
    elif [ $coe == 'k8s-coreos' ]; then
        local image_name="coreos"
        local container_format="bare"
    elif [ "${coe}${special}" == 'k8s-ironic' ]; then
        local bm_flavor_id=$(openstack flavor show baremetal -f value -c id)
        die_if_not_set $LINENO bm_flavor_id "Failed to get id of baremetal flavor"

        # NOTE(yuanying): Workaround fix for ironic issue
        # cf. https://bugs.launchpad.net/ironic/+bug/1596421
        echo "alter table ironic.nodes modify instance_info LONGTEXT;" | mysql -uroot -p${MYSQL_PASSWORD} ironic
        # NOTE(yuanying): Ironic instances need to connect to Internet
        neutron subnet-update private-subnet --dns-nameserver 8.8.8.8

        local container_format="ami"
    else
        local image_name="atomic"
        local container_format="bare"
    fi

    # if we have the MAGNUM_IMAGE_NAME setting, use it instead
    # of the default one. In combination with MAGNUM_GUEST_IMAGE_URL
    # setting, it allows to perform testing on custom images.
    image_name=${MAGNUM_IMAGE_NAME:-$image_name}

    export NIC_ID=$(neutron net-show public | awk '/ id /{print $4}')

    # We need to filter by container_format to get the appropriate
    # image. Specifically, when we provide kernel and ramdisk images
    # we need to select the 'ami' image. Otherwise, when we have
    # qcow2 images, the format is 'bare'.
    export IMAGE_ID=$(glance --os-image-api-version 1 image-list | grep $container_format | grep -i $image_name | awk '{print $2}')

    # pass the appropriate variables via a config file
    CREDS_FILE=$MAGNUM_DIR/functional_creds.conf
    cat <<EOF > $CREDS_FILE
# Credentials for functional testing

[auth]
auth_url = $OS_AUTH_URL
magnum_url = $BYPASS_URL
username = $OS_USERNAME
tenant_name = $OS_TENANT_NAME
password = $OS_PASSWORD
auth_version = v2
[admin]
user = $OS_USERNAME
tenant = $OS_TENANT_NAME
pass = $OS_PASSWORD
region_name = $OS_REGION_NAME
[magnum]
image_id = $IMAGE_ID
nic_id = $NIC_ID
keypair_id = default
flavor_id = ${bm_flavor_id:-s1.magnum}
master_flavor_id = ${bm_flavor_id:-m1.magnum}
copy_logs = true
dns_nameserver = 8.8.8.8
EOF

    # Note(eliqiao): Let's keep this only for debugging on gate.
    echo_summary $CREDS_FILE
    cat $CREDS_FILE

    # Create a keypair for use in the functional tests.
    echo_summary "Generate a key-pair"
    ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa
    nova keypair-add  --pub-key ~/.ssh/id_rsa.pub default
}

function add_flavor {
    # because of policy.json change in nova, flavor-create is now an admin-only feature
    # moving this out to only be used by admins

    # Get admin credentials
    pushd ../devstack
    source openrc admin admin
    # NOTE(hongbin): This is a temporary work around. These variables are for
    # keystone v3, but magnum is using v2 API. Therefore, unset them to make the
    # keystoneclient work.
    # Bug: #1473600
    unset OS_PROJECT_DOMAIN_ID
    unset OS_USER_DOMAIN_ID
    unset OS_AUTH_TYPE
    popd

    # Due to keystone defaulting everything to v3, we need to update to make func tests
    # work in our gates back to v2
    export OS_AUTH_URL=http://127.0.0.1:5000/v2.0
    export OS_IDENTITY_API_VERSION=2.0

    # Create magnum specific flavor for use in functional tests.
    echo_summary "Create a flavor"
    nova flavor-create  m1.magnum 100 1024 10 1
    nova flavor-create  s1.magnum 200 512 10 1
}

if ! function_exists echo_summary; then
    function echo_summary {
        echo $@
    }
fi

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "magnum's post_test_hook.sh was called..."
(set -o posix; set)

# source it to make sure to get REQUIREMENTS_DIR
source $BASE/new/devstack/stackrc

constraints="-c $REQUIREMENTS_DIR/upper-constraints.txt"
sudo -H pip install $constraints -U -r requirements.txt -r test-requirements.txt

export MAGNUM_DIR="$BASE/new/magnum"
sudo chown -R jenkins:stack $MAGNUM_DIR

# Run functional tests
# Currently we support functional-api, functional-k8s, will support swarm,
# mesos later.

echo "Running magnum functional test suite for $1"

# For api, we will run tempest tests

coe=$1
special=$2

if [[ "api" == "$coe" ]]; then
    # Import devstack functions 'iniset', 'iniget' and 'trueorfalse'
    source $BASE/new/devstack/functions
    echo "TEMPEST_SERVICES+=,magnum" >> $localrc_path
    pushd $BASE/new/tempest
    sudo chown -R jenkins:stack $BASE/new/tempest

    add_flavor

    # Set demo credentials
    source $BASE/new/devstack/accrc/demo/demo
    unset OS_AUTH_TYPE

    create_test_data $coe

    # Set up tempest config with magnum goodness
    iniset $BASE/new/tempest/etc/tempest.conf magnum image_id $IMAGE_ID
    iniset $BASE/new/tempest/etc/tempest.conf magnum nic_id $NIC_ID
    iniset $BASE/new/tempest/etc/tempest.conf magnum keypair_id default
    iniset $BASE/new/tempest/etc/tempest.conf magnum flavor_id s1.magnum
    iniset $BASE/new/tempest/etc/tempest.conf magnum master_flavor_id m1.magnum
    iniset $BASE/new/tempest/etc/tempest.conf magnum copy_logs True

    # show tempest config with magnum
    cat etc/tempest.conf

    # Set up concurrency and test regex
    export MAGNUM_TEMPEST_CONCURRENCY=${MAGNUM_TEMPEST_CONCURRENCY:-1}
    export MAGNUM_TESTS=${MAGNUM_TESTS:-'magnum.tests.functional.api.v1'}

    echo "Running tempest magnum test suites"
    sudo -H -u jenkins tox -eall-plugin -- $MAGNUM_TESTS --concurrency=$MAGNUM_TEMPEST_CONCURRENCY
else
    # Get admin credentials
    pushd ../devstack
    source openrc admin admin
    # NOTE(hongbin): This is a temporary work around. These variables are for
    # keystone v3, but magnum is using v2 API. Therefore, unset them to make the
    # keystoneclient work.
    # Bug: #1473600
    unset OS_PROJECT_DOMAIN_ID
    unset OS_USER_DOMAIN_ID
    unset OS_AUTH_TYPE
    popd

    add_flavor

    create_test_data $coe $special

    target="${coe}${special}"
    sudo -E -H -u jenkins tox -e functional-"$target" -- --concurrency=1
fi
EXIT_CODE=$?

# Delete the keypair used in the functional test.
echo_summary "Running keypair-delete"
nova keypair-delete default

# Delete the flavor used in the functional test.
echo_summary "Running flavor-delete"
nova flavor-delete m1.magnum

# Save functional testing log
sudo cp $MAGNUM_DIR/functional-tests.log /opt/stack/logs/

# Save functional_creds.conf
sudo cp $CREDS_FILE /opt/stack/logs/

# Restore xtrace
$XTRACE

exit $EXIT_CODE
