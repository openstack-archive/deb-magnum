.. _install:

Install and configure
~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service, code-named magnum, on the controller node.

This section assumes that you already have a working OpenStack environment with
at least the following components installed: Identity service, Image service,
Compute service, Networking service, Block Storage service and Orchestration
service. See `OpenStack Install Guides <http://docs.openstack.org/
#install-guides>`__.

To provide access to Docker Swarm or Kubernetes using the native clients
(docker or kubectl, respectively) magnum uses TLS certificates. To store the
certificates, it is recommended to use the `Key Manager service, code-named
barbican <http://docs.openstack.org/project-install-guide/key-manager/
draft/>`__, or you can save them in magnum's database.

Optionally, you can install the following components:

- `Load Balancer as a Service (LBaaS v2) <http://docs.openstack.org/
  networking-guide/config-lbaas.html>`__ to create clusters with multiple
  masters
- `Bare Metal service <http://docs.openstack.org/project-install-guide/
  baremetal/draft/>`__ to create baremetal clusters
- `Object Storage service <http://docs.openstack.org/project-install-guide/
  object-storage/draft/>`__ to make private Docker registries available to
  users
- `Telemetry Data Collection service <http://docs.openstack.org/
  project-install-guide/telemetry/draft/>`__ to periodically send
  magnum-related metrics

.. note::

   Installation and configuration vary by distribution.

.. important::

   Magnum creates clusters of compute instances on the Compute service (nova).
   These instances must have basic Internet connectivity and must be able to
   reach magnum's API server. Make sure that the Compute and Network services
   are configured accordingly.

.. toctree::
   :maxdepth: 2

   install-debian-manual.rst
   install-obs.rst
   install-rdo.rst
   install-ubuntu.rst
