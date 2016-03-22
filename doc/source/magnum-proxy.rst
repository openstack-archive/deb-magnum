=================================================
Using Proxies in magnum if running under firewall
=================================================

If you are running magnum behind a firewall then you may need a proxy
for using services like docker, kubernetes and mesos. Use these steps
when your firewall will not allow you to use those services without a
proxy.

**NOTE:** This feature has only been tested with the supported bay type
and associated image: Kubernetes and Swarm bay using the Fedora Atomic
image, and Mesos bay using the Ubuntu image.

Proxy Parameters to define before use
=====================================

1. http-proxy

Address of a proxy that will receive all HTTP requests and relay
them. The format is a URL including a port number. For example:
http://10.11.12.13:8000 or http://abcproxy.com:8000

2. https-proxy

Address of a proxy that will receive all HTTPS requests and relay
them. The format is a URL including a port number. For example:
https://10.11.12.13:8000 or https://abcproxy.com:8000

3. no-proxy

A comma separated list of IP addresses or hostnames that should bypass
your proxy, and make conenctions directly.

**NOTE:** You may not express networks/subnets. It only accepts names
and ip addresses. Bad example: 192.168.0.0/28.

Steps to configure proxies.
==============================

You can specify all three proxy parameteres while creating baymodel of any
coe type. All of proxy parameters are optional.

    magnum baymodel-create --name k8sbaymodel \
                       --image-id fedora-21-atomic-5 \
                       --keypair-id testkey \
                       --external-network-id public \
                       --dns-nameserver 8.8.8.8 \
                       --flavor-id m1.small \
                       --coe kubernetes \
                       --http-proxy <http://abc-proxy.com:8080> \
                       --https-proxy <https://abc-proxy.com:8080> \
                       --no-proxy <172.24.4.4,172.24.4.9,172.24.4.8>
    magnum baymodel-create --name swarmbaymodel \
                       --image-id fedora-21-atomic-5 \
                       --keypair-id testkey \
                       --external-network-id public \
                       --dns-nameserver 8.8.8.8 \
                       --flavor-id m1.small \
                       --coe swarm \
                       --http-proxy <http://abc-proxy.com:8080> \
                       --https-proxy <https://abc-proxy.com:8080> \
                       --no-proxy <172.24.4.4,172.24.4.9,172.24.4.8>
    magnum baymodel-create --name mesosbaymodel \
                       --image-id ubuntu-mesos \
                       --keypair-id testkey \
                       --external-network-id public \
                       --dns-nameserver 8.8.8.8 \
                       --flavor-id m1.small \
                       --coe mesos \
                       --http-proxy <http://abc-proxy.com:8080> \
                       --https-proxy <https://abc-proxy.com:8080> \
                       --no-proxy <172.24.4.4,172.24.4.9,172.24.4.8>
