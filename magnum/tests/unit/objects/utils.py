# Copyright 2014 Rackspace Hosting
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Magnum object test utilities."""


from magnum.common import exception
from magnum import objects
from magnum.tests.unit.db import utils as db_utils


def get_test_baymodel(context, **kw):
    """Return a BayModel object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_baymodel = db_utils.get_test_baymodel(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_baymodel['id']
    baymodel = objects.BayModel(context)
    for key in db_baymodel:
        setattr(baymodel, key, db_baymodel[key])
    return baymodel


def create_test_baymodel(context, **kw):
    """Create and return a test baymodel object.

    Create a baymodel in the DB and return a BayModel object with appropriate
    attributes.
    """
    baymodel = get_test_baymodel(context, **kw)
    try:
        baymodel.create()
    except exception.BayModelAlreadyExists:
        baymodel = objects.BayModel.get(context, baymodel.uuid)
    return baymodel


def get_test_bay(context, **kw):
    """Return a Bay object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_bay = db_utils.get_test_bay(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_bay['id']
    bay = objects.Bay(context)
    for key in db_bay:
        setattr(bay, key, db_bay[key])
    return bay


def create_test_bay(context, **kw):
    """Create and return a test bay object.

    Create a bay in the DB and return a Bay object with appropriate
    attributes.
    """
    bay = get_test_bay(context, **kw)
    create_test_baymodel(context, uuid=bay['baymodel_id'],
                         coe=kw.get('coe', 'swarm'))
    bay.create()
    return bay


def get_test_pod(context, **kw):
    """Return a Pod object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_pod = db_utils.get_test_pod(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_pod['id']
    pod = objects.Pod(context)
    for key in db_pod:
        setattr(pod, key, db_pod[key])
    return pod


def create_test_pod(context, **kw):
    """Create and return a test pod object.

    Create a pod in the DB and return a Pod object with appropriate
    attributes.
    """
    pod = get_test_pod(context, **kw)
    pod.manifest = '{"foo": "bar"}'
    return pod


def get_test_service(context, **kw):
    """Return a Service object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_service = db_utils.get_test_service(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_service['id']
    service = objects.Service(context)
    for key in db_service:
        setattr(service, key, db_service[key])
    return service


def create_test_service(context, **kw):
    """Create and return a test service object.

    Create a service in the DB and return a Service object with appropriate
    attributes.
    """
    service = get_test_service(context, **kw)
    service.manifest = '{"foo": "bar"}'
    return service


def get_test_rc(context, **kw):
    """Return a ReplicationController object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_rc = db_utils.get_test_rc(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_rc['id']
    rc = objects.ReplicationController(context)
    for key in db_rc:
        setattr(rc, key, db_rc[key])
    return rc


def create_test_rc(context, **kw):
    """Create and return a test ReplicationController object.

    Create a replication controller in the DB and return a
    ReplicationController object with appropriate attributes.
    """
    rc = get_test_rc(context, **kw)
    rc.manifest = '{"foo": "bar"}'
    return rc


def get_test_x509keypair(context, **kw):
    """Return a X509KeyPair object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_x509keypair = db_utils.get_test_x509keypair(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_x509keypair['id']
    x509keypair = objects.X509KeyPair(context)
    for key in db_x509keypair:
        setattr(x509keypair, key, db_x509keypair[key])
    return x509keypair


def create_test_x509keypair(context, **kw):
    """Create and return a test x509keypair object.

    Create a x509keypair in the DB and return a X509KeyPair object with
    appropriate attributes.
    """
    x509keypair = get_test_x509keypair(context, **kw)
    x509keypair.create()
    return x509keypair


def get_test_magnum_service_object(context, **kw):
    """Return a test magnum_service object.

    Get a magnum_service from DB layer and return an object with
    appropriate attributes.
    """
    db_magnum_service = db_utils.get_test_magnum_service(**kw)
    magnum_service = objects.MagnumService(context)
    for key in db_magnum_service:
        setattr(magnum_service, key, db_magnum_service[key])
    return magnum_service


def create_test_container(context, **kw):
    """Create and return a test container object.

    Create a container in the DB and return a container object with
    appropriate attributes.
    """
    container = get_test_container(context, **kw)
    container.create()
    return container


def get_test_container(context, **kw):
    """Return a test container object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_container = db_utils.get_test_container(**kw)
    container = objects.Container(context)
    for key in db_container:
        setattr(container, key, db_container[key])
    return container
