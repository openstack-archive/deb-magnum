#!/bin/sh

. /etc/sysconfig/heat-params

echo "configuring kubernetes (minion)"

ETCD_SERVER_IP=${ETCD_SERVER_IP:-$KUBE_MASTER_IP}
KUBE_PROTOCOL="https"
KUBE_CONFIG=""
if [ "$TLS_DISABLED" == "True" ]; then
    KUBE_PROTOCOL="http"
else
    KUBE_CONFIG="--kubeconfig=/srv/kubernetes/kubeconfig.yaml"
fi
KUBE_MASTER_URI="$KUBE_PROTOCOL://$KUBE_MASTER_IP:$KUBE_API_PORT"

sed -i '
  /^KUBE_ALLOW_PRIV=/ s/=.*/="--allow_privileged='"$KUBE_ALLOW_PRIV"'"/
  /^KUBE_ETCD_SERVERS=/ s|=.*|="--etcd_servers=http://'"$ETCD_SERVER_IP"':2379"|
  /^KUBE_MASTER=/ s|=.*|="--master='"$KUBE_MASTER_URI"'"|
' /etc/kubernetes/config

sed -i '
  /^KUBELET_ADDRESS=/ s/=.*/="--address=0.0.0.0"/
  /^KUBELET_HOSTNAME=/ s/=.*/=""/
  /^KUBELET_API_SERVER=/ s|=.*|="--api_servers='"$KUBE_MASTER_URI"'"|
  /^KUBELET_ARGS=/ s|=.*|='"$KUBE_CONFIG"'|
' /etc/kubernetes/kubelet

sed -i '
  /^KUBE_PROXY_ARGS=/ s|=.*|='"$KUBE_CONFIG"'|
' /etc/kubernetes/proxy

if [ "$NETWORK_DRIVER" == "flannel" ]; then
    sed -i '
      /^FLANNEL_ETCD=/ s|=.*|="http://'"$ETCD_SERVER_IP"':2379"|
    ' /etc/sysconfig/flanneld
fi

cat >> /etc/environment <<EOF
KUBERNETES_MASTER=$KUBE_MASTER_URI
EOF

sed -i '/^DOCKER_STORAGE_OPTIONS=/ s/=.*/=--storage-driver devicemapper --storage-opt dm.fs=xfs --storage-opt dm.thinpooldev=\/dev\/mapper\/docker-docker--pool --storage-opt dm.use_deferred_removal=true/' /etc/sysconfig/docker-storage

hostname `hostname | sed 's/.novalocal//'`
