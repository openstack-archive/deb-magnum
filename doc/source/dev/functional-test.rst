========================
Running functional tests
========================

This is a guide for developers who want to run functional tests in their local
machine.

Prerequisite
============

You need to have a Magnum instance running somewhere. If you are using
devstack, follow the developer quickstart guide to deploy Magnum in a devstack
environment

`<http://docs.openstack.org/developer/magnum/dev/quickstart.html>`_

Configuration
=============
The functional tests require a couple configuration files, so you'll need to
generate them yourself.

For devstack
------------
If you're using devstack, you can copy and modify the devstack configuration::

    cd /opt/stack/magnum
    cp /opt/stack/tempest/etc/tempest.conf /opt/stack/magnum/etc/tempest.conf
    cp functional_creds.conf.sample functional_creds.conf

    # update the IP address
    HOST=$(cat /etc/magnum/magnum.conf | awk '/^host = /{print $3}')
    sed -i "s/127.0.0.1/$HOST/" functional_creds.conf

    # update admin password
    source /opt/stack/devstack/openrc admin admin
    iniset functional_creds.conf admin pass $OS_PASSWORD

    # update demo password
    source /opt/stack/devstack/openrc demo demo
    iniset functional_creds.conf auth password $OS_PASSWORD

Create the necessary keypair and flavor::

    source /opt/stack/devstack/openrc admin admin
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub default
    nova flavor-create  m1.magnum 100 1024 8 1
    nova flavor-create  s1.magnum 200 512 8 1

    source /opt/stack/devstack/openrc demo demo
    nova keypair-add --pub-key ~/.ssh/id_rsa.pub default

You may need to explicitly upgrade required packages if you've installed them
before and their versions become too old::

    UPPER_CONSTRAINTS=/opt/stack/requirements/upper-constraints.txt
    sudo pip install -c $UPPER_CONSTRAINTS -U -r test-requirements.txt

Outside of devstack
-------------------
If you are not using devstack, you'll need to create the configuration files.
The /etc/tempest.conf configuration file is documented here

`<http://docs.openstack.org/developer/tempest/configuration.html#tempest-configuration>`_

Here's a reasonable sample of tempest.conf settings you might need::

    [auth]
    use_dynamic_credentials=False
    test_accounts_file=/tmp/etc/magnum/accounts.yaml
    admin_username=admin
    admin_password=password
    admin_tenant_name=admin

    [identity]
    disable_ssl_certificate_validation=True
    uri=https://identity.example.com/v2.0
    auth_version=v2
    region=EAST

    [identity-feature-enabled]
    api_v2 = true
    api_v3 = false
    trust = false

    [oslo_concurrency]
    lock_path = /tmp/

    [magnum]
    image_id=22222222-2222-2222-2222-222222222222
    nic_id=11111111-1111-1111-1111-111111111111
    keypair_id=default
    flavor_id=small
    magnum_url=https://magnum.example.com/v1

    [debug]
    trace_requests=true

A sample functional_creds.conf can be found in the root of this project named
functional_creds.conf.sample

When you run tox, be sure to specify the location of your tempest.conf using
TEMPEST_CONFIG_DIR::

    export TEMPEST_CONFIG_DIR=/tmp/etc/magnum/
    tox -e functional-api

Execution
=========

Magnum has different functional tests for each COE and for the API.
All the environments are detailed in Magnum's tox.ini::

    cat tox.ini | grep functional- | awk -F: '{print $2}' | sed s/]//

To run a particular subset of tests, specify that group as a tox environment.
For example, here is how you would run all of the kubernates tests::

    tox -e functional-k8s

To run a specific test or group of tests, specify the test path as a positional argument::

    tox -e functional-k8s -- magnum.tests.functional.k8s.v1.test_k8s_python_client.TestBayModelResource
