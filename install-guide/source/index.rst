===========================================
Container Infrastructure Management service
===========================================

.. toctree::
   :maxdepth: 2

   get_started.rst
   install.rst
   verify.rst
   launch-instance.rst
   next-steps.rst

The Container Infrastructure Management service codenamed (magnum) is an
OpenStack API service developed by the OpenStack Containers Team making
container orchestration engines (COE) such as Docker Swarm, Kubernetes
and Mesos available as first class resources in OpenStack. Magnum uses
Heat to orchestrate an OS image which contains Docker and Kubernetes and
runs that image in either virtual machines or bare metal in a cluster
configuration.

This chapter assumes a working setup of OpenStack following `OpenStack
Installation Tutorial <http://docs.openstack.org/#install-guides>`_.

