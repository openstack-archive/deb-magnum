#!/bin/sh

. /etc/sysconfig/heat-params

function init_templates {
    local KUBE_PROTOCOL="https"
    local KUBE_CONFIG="/srv/kubernetes/kubeconfig.yaml"
    if [ "${TLS_DISABLED}" == "True" ]; then
        KUBE_PROTOCOL="http"
        KUBE_CONFIG=
    fi

    local MASTER="${KUBE_PROTOCOL}://${KUBE_MASTER_IP}:${KUBE_API_PORT}"
    local TEMPLATE=/etc/kubernetes/manifests/kube-proxy.yaml
    [ -f ${TEMPLATE} ] || {
        echo "TEMPLATE: $TEMPLATE"
        mkdir -p $(dirname ${TEMPLATE})
        cat << EOF > ${TEMPLATE}
apiVersion: v1
kind: Pod
metadata:
  name: kube-proxy
  namespace: kube-system
spec:
  hostNetwork: true
  containers:
  - name: kube-proxy
    image: gcr.io/google_containers/hyperkube:v1.0.6
    command:
    - /hyperkube
    - proxy
    - --master=${MASTER}
    - --kubeconfig=${KUBE_CONFIG}
    - --logtostderr=true
    - --v=0
    securityContext:
      privileged: true
    volumeMounts:
    - mountPath: /etc/ssl/certs
      name: ssl-certs-host
      readOnly: true
    - mountPath: /srv/kubernetes
      name: "srv-kube"
      readOnly: true
  volumes:
  - hostPath:
      path: /etc/ssl/certs
    name: ssl-certs-host
  - hostPath:
        path: "/srv/kubernetes"
    name: "srv-kube"
EOF
    }
}

init_templates
