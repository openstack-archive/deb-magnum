#!/bin/sh

. /etc/sysconfig/heat-params

echo "stopping docker"
systemctl stop docker
ip link del docker0

if [ "$NETWORK_DRIVER" == "flannel" ]; then
    FLANNEL_ENV=/run/flannel/subnet.env

    attempts=60
    while [[ ! -f $FLANNEL_ENV && $attempts != 0 ]]; do
        echo "waiting for file $FLANNEL_ENV"
        sleep 1
        let attempts--
    done

    source $FLANNEL_ENV

    if ! [ "\$FLANNEL_SUBNET" ] && [ "\$FLANNEL_MTU" ] ; then
      echo "ERROR: missing required environment variables." >&2
      exit 1
    fi

    sed -i '
      /^DOCKER_OPTS=/ s/=.*/="--storage-driver=btrfs"/
      /^DOCKER_NETWORK_OPTIONS=/ s|=.*|="--bip='"$FLANNEL_SUBNET"' --mtu='"$FLANNEL_MTU"'"|
    ' /etc/sysconfig/docker
fi

DOCKER_DEV=/dev/disk/by-id/virtio-${DOCKER_VOLUME:0:20}

attempts=60
while [[ ! -b $DOCKER_DEV && $attempts != 0 ]]; do
    echo "waiting for disk $DOCKER_DEV"
    sleep 0.5
    udevadm trigger
    let attempts--
done

if ! [ -b $DOCKER_DEV ]; then
    echo "ERROR: device $DOCKER_DEV does not exist" >&2
    exit 1
fi

mkfs.btrfs $DOCKER_DEV

mount $DOCKER_DEV /var/lib/docker

# make sure we pick up any modified unit files
systemctl daemon-reload

echo "activating docker service"
systemctl enable docker

echo "starting docker service"
systemctl --no-block start docker
