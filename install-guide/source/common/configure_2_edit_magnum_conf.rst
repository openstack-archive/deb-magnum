2. Edit the ``/etc/magnum/magnum.conf`` file:

   * In the ``[api]`` section, configure the host:

     .. code-block:: ini

        [api]
        ...
        host = controller

   * In the ``[certificates]`` section, select ``barbican`` (or ``x509keypair`` if
     you don't have barbican installed):

     * Use barbican to store certificates:

       .. code-block:: ini

          [certificates]
          ...
          cert_manager_type = barbican

     .. important::

        Barbican is recommended for production environments.

     * To store x509 certificates in magnum's database:

       .. code-block:: ini

          [certificates]
          ...
          cert_manager_type = x509keypair

   * In the ``[cinder_client]`` section, configure the region name:

     .. code-block:: ini

        [cinder_client]
        ...
        region_name = RegionOne

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        ...
        connection = mysql+pymysql://magnum:MAGNUM_DBPASS@controller/magnum

     Replace ``MAGNUM_DBPASS`` with the password you chose for
     the magnum database.

   * In the ``[keystone_authtoken]`` and ``[trust]`` sections, configure
     Identity service access:

     .. code-block:: ini

        [keystone_authtoken]
        ...
        memcached_servers = controller:11211
        auth_version = v3
        auth_uri = http://controller:5000/v3
        project_domain_id = default
        project_name = service
        user_domain_id = default
        password = MAGNUM_PASS
        username = magnum
        auth_url = http://controller:35357
        auth_type = password

        [trust]
        ...
        trustee_domain_name = magnum
        trustee_domain_admin_name = magnum_domain_admin
        trustee_domain_admin_password = DOMAIN_ADMIN_PASS

     Replace MAGNUM_PASS with the password you chose for the magnum user in the
     Identity service and DOMAIN_ADMIN_PASS with the password you chose for the
     ``magnum_domain_admin`` user.

   * In the ``[oslo_messaging_notifications]`` section, configure the
     ``driver``:

     .. code-block:: ini

        [oslo_messaging_notifications]
        ...
        driver = messaging

   * In the ``[oslo_messaging_rabbit]`` section, configure RabbitMQ message
     queue access:

     .. code-block:: ini

        [oslo_messaging_rabbit]
        ...
        rabbit_host = controller
        rabbit_userid = openstack
        rabbit_password = RABBIT_PASS

     Replace RABBIT_PASS with the password you chose for the openstack account
     in RabbitMQ.


