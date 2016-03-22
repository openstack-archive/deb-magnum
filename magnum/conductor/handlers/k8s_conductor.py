#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


from oslo_log import log as logging

from magnum.common import exception
from magnum.common import k8s_manifest
from magnum.common.pythonk8sclient.swagger_client import rest
from magnum.common import utils
from magnum.conductor import k8s_api as k8s
from magnum.conductor import utils as conductor_utils
from magnum import objects

import ast


LOG = logging.getLogger(__name__)


class Handler(object):
    """Magnum Kubernetes RPC handler.

    These are the backend operations. They are executed by the backend service.
    API calls via AMQP (within the ReST API) trigger the handlers to be called.

    """

    def __init__(self):
        super(Handler, self).__init__()

    def service_create(self, context, service):
        LOG.debug("service_create")
        self.k8s_api = k8s.create_k8s_api(context, service.bay_uuid)
        manifest = k8s_manifest.parse(service.manifest)
        try:
            resp = self.k8s_api.create_namespaced_service(body=manifest,
                                                          namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ServiceCreationFailed(bay_uuid=service.bay_uuid)

        service['uuid'] = resp.metadata.uid
        service['name'] = resp.metadata.name
        service['labels'] = ast.literal_eval(resp.metadata.labels)
        service['selector'] = ast.literal_eval(resp.spec.selector)
        service['ip'] = resp.spec.cluster_ip
        service_value = []
        for p in resp.spec.ports:
            ports = p.to_dict()
            if not ports['name']:
                ports['name'] = 'k8s-service'
            service_value.append(ports)

        service['ports'] = service_value

        return service

    def service_update(self, context, service_ident, bay_ident, manifest):
        LOG.debug("service_update %s", service_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(service_ident):
            service = objects.Service.get_by_uuid(context,
                                                  service_ident,
                                                  bay_uuid,
                                                  self.k8s_api)
        else:
            service = objects.Service.get_by_name(context,
                                                  service_ident,
                                                  bay_uuid,
                                                  self.k8s_api)
        service_ident = service.name
        try:
            resp = self.k8s_api.replace_namespaced_service(
                name=str(service_ident),
                body=manifest,
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ServiceNotFound(service=service.uuid)

        service['uuid'] = resp.metadata.uid
        service['name'] = resp.metadata.name
        service['project_id'] = context.project_id
        service['user_id'] = context.user_id
        service['bay_uuid'] = bay_uuid
        service['labels'] = ast.literal_eval(resp.metadata.labels)
        if not resp.spec.selector:
            service['selector'] = {}
        else:
            service['selector'] = ast.literal_eval(resp.spec.selector)
        service['ip'] = resp.spec.cluster_ip
        service_value = []
        for p in resp.spec.ports:
            ports = p.to_dict()
            if not ports['name']:
                ports['name'] = 'k8s-service'
            service_value.append(ports)

        service['ports'] = service_value

        return service

    def service_delete(self, context, service_ident, bay_ident):
        LOG.debug("service_delete %s", service_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(service_ident):
            service = objects.Service.get_by_uuid(context, service_ident,
                                                  bay_uuid, self.k8s_api)
            service_name = service.name
        else:
            service_name = service_ident
        if conductor_utils.object_has_stack(context, bay_uuid):
            try:

                self.k8s_api.delete_namespaced_service(name=str(service_name),
                                                       namespace='default')
            except rest.ApiException as err:
                if err.status == 404:
                    pass
                else:
                    raise exception.KubernetesAPIFailed(err=err)

    def service_show(self, context, service_ident, bay_ident):
        LOG.debug("service_show %s", service_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(service_ident):
            service = objects.Service.get_by_uuid(context, service_ident,
                                                  bay_uuid, self.k8s_api)
        else:
            service = objects.Service.get_by_name(context, service_ident,
                                                  bay_uuid, self.k8s_api)

        return service

    def service_list(self, context, bay_ident):
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        try:
            resp = self.k8s_api.list_namespaced_service(namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ServiceListNotFound(bay_uuid=bay_uuid)

        services = []
        for service_entry in resp.items:
            service = {}
            service['uuid'] = service_entry.metadata.uid
            service['name'] = service_entry.metadata.name
            service['project_id'] = context.project_id
            service['user_id'] = context.user_id
            service['bay_uuid'] = bay_uuid
            service['labels'] = ast.literal_eval(
                service_entry.metadata.labels)
            if not service_entry.spec.selector:
                service['selector'] = {}
            else:
                service['selector'] = ast.literal_eval(
                    service_entry.spec.selector)
            service['ip'] = service_entry.spec.cluster_ip
            service_value = []
            for p in service_entry.spec.ports:
                ports = p.to_dict()
                if not ports['name']:
                    ports['name'] = 'k8s-service'
                service_value.append(ports)

            service['ports'] = service_value

            service_obj = objects.Service(context, **service)
            services.append(service_obj)

        return services

    # Pod Operations
    def pod_create(self, context, pod):
        LOG.debug("pod_create")
        self.k8s_api = k8s.create_k8s_api(context, pod.bay_uuid)
        manifest = k8s_manifest.parse(pod.manifest)
        try:
            resp = self.k8s_api.create_namespaced_pod(body=manifest,
                                                      namespace='default')
        except rest.ApiException as err:
            pod.status = 'failed'
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.PodCreationFailed(bay_uuid=pod.bay_uuid)

        pod['uuid'] = resp.metadata.uid
        pod['name'] = resp.metadata.name
        pod['images'] = [c.image for c in resp.spec.containers]
        pod['labels'] = ast.literal_eval(resp.metadata.labels)
        pod['status'] = resp.status.phase
        pod['host'] = resp.spec.node_name

        return pod

    def pod_update(self, context, pod_ident, bay_ident, manifest):
        LOG.debug("pod_update %s", pod_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(pod_ident):
            pod = objects.Pod.get_by_uuid(context, pod_ident,
                                          bay_uuid, self.k8s_api)
        else:
            pod = objects.Pod.get_by_name(context, pod_ident,
                                          bay_uuid, self.k8s_api)
        pod_ident = pod.name
        try:
            resp = self.k8s_api.replace_namespaced_pod(name=str(pod_ident),
                                                       body=manifest,
                                                       namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.PodNotFound(pod=pod.uuid)

        pod['uuid'] = resp.metadata.uid
        pod['name'] = resp.metadata.name
        pod['project_id'] = context.project_id
        pod['user_id'] = context.user_id
        pod['bay_uuid'] = bay_uuid
        pod['images'] = [c.image for c in resp.spec.containers]
        if not resp.metadata.labels:
            pod['labels'] = {}
        else:
            pod['labels'] = ast.literal_eval(resp.metadata.labels)
        pod['status'] = resp.status.phase
        pod['host'] = resp.spec.node_name

        return pod

    def pod_delete(self, context, pod_ident, bay_ident):
        LOG.debug("pod_delete %s", pod_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(pod_ident):
            pod = objects.Pod.get_by_uuid(context, pod_ident,
                                          bay_uuid, self.k8s_api)
            pod_name = pod.name
        else:
            pod_name = pod_ident
        if conductor_utils.object_has_stack(context, bay_uuid):
            try:
                self.k8s_api.delete_namespaced_pod(name=str(pod_name), body={},
                                                   namespace='default')
            except rest.ApiException as err:
                if err.status == 404:
                    pass
                else:
                    raise exception.KubernetesAPIFailed(err=err)

    def pod_show(self, context, pod_ident, bay_ident):
        LOG.debug("pod_show %s", pod_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(pod_ident):
            pod = objects.Pod.get_by_uuid(context, pod_ident,
                                          bay_uuid, self.k8s_api)
        else:
            pod = objects.Pod.get_by_name(context, pod_ident,
                                          bay_uuid, self.k8s_api)

        return pod

    def pod_list(self, context, bay_ident):
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        try:
            resp = self.k8s_api.list_namespaced_pod(namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.PodListNotFound(bay_uuid=bay_uuid)

        pods = []
        for pod_entry in resp.items:
            pod = {}
            pod['uuid'] = pod_entry.metadata.uid
            pod['name'] = pod_entry.metadata.name
            pod['project_id'] = context.project_id
            pod['user_id'] = context.user_id
            pod['bay_uuid'] = bay_uuid
            pod['images'] = [c.image for c in pod_entry.spec.containers]
            if not pod_entry.metadata.labels:
                pod['labels'] = {}
            else:
                pod['labels'] = ast.literal_eval(pod_entry.metadata.labels)
            pod['status'] = pod_entry.status.phase
            pod['host'] = pod_entry.spec.node_name

            pod_obj = objects.Pod(context, **pod)
            pods.append(pod_obj)

        return pods

    # Replication Controller Operations
    def rc_create(self, context, rc):
        LOG.debug("rc_create")
        self.k8s_api = k8s.create_k8s_api(context, rc.bay_uuid)
        manifest = k8s_manifest.parse(rc.manifest)
        try:
            resp = self.k8s_api.create_namespaced_replication_controller(
                body=manifest,
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerCreationFailed(
                bay_uuid=rc.bay_uuid)

        rc['uuid'] = resp.metadata.uid
        rc['name'] = resp.metadata.name
        rc['images'] = [c.image for c in resp.spec.template.spec.containers]
        rc['labels'] = ast.literal_eval(resp.metadata.labels)
        rc['replicas'] = resp.status.replicas
        return rc

    def rc_update(self, context, rc_ident, bay_ident, manifest):
        LOG.debug("rc_update %s", rc_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)
        else:
            rc = objects.ReplicationController.get_by_name(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)
        try:
            resp = self.k8s_api.replace_namespaced_replication_controller(
                name=str(rc.name),
                body=manifest,
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerNotFound(rc=rc.uuid)

        rc['uuid'] = resp.metadata.uid
        rc['name'] = resp.metadata.name
        rc['project_id'] = context.project_id
        rc['user_id'] = context.user_id
        rc['images'] = [c.image for c in resp.spec.template.spec.containers]
        rc['bay_uuid'] = bay_uuid
        rc['labels'] = ast.literal_eval(resp.metadata.labels)
        rc['replicas'] = resp.status.replicas

        return rc

    def rc_delete(self, context, rc_ident, bay_ident):
        LOG.debug("rc_delete %s", rc_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)
            rc_name = rc.name
        else:
            rc_name = rc_ident
        if conductor_utils.object_has_stack(context, bay_uuid):
            try:
                self.k8s_api.delete_namespaced_replication_controller(
                    name=str(rc_name),
                    body={},
                    namespace='default')
            except rest.ApiException as err:
                if err.status == 404:
                    pass
                else:
                    raise exception.KubernetesAPIFailed(err=err)

    def rc_show(self, context, rc_ident, bay_ident):
        LOG.debug("rc_show %s", rc_ident)
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        if utils.is_uuid_like(rc_ident):
            rc = objects.ReplicationController.get_by_uuid(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)
        else:
            rc = objects.ReplicationController.get_by_name(context, rc_ident,
                                                           bay_uuid,
                                                           self.k8s_api)

        return rc

    def rc_list(self, context, bay_ident):
        # Since bay identifier is specified verify whether its a UUID
        # or Name. If name is specified as bay identifier need to extract
        # the bay uuid since its needed to get the k8s_api object.
        bay_uuid = conductor_utils.retrieve_bay_uuid(context, bay_ident)
        self.k8s_api = k8s.create_k8s_api(context, bay_uuid)
        try:
            resp = self.k8s_api.list_namespaced_replication_controller(
                namespace='default')
        except rest.ApiException as err:
            raise exception.KubernetesAPIFailed(err=err)

        if resp is None:
            raise exception.ReplicationControllerListNotFound(
                bay_uuid=bay_uuid)

        rcs = []
        for entry in resp._items:
            rc = {}
            rc['uuid'] = entry.metadata.uid
            rc['name'] = entry.metadata.name
            rc['project_id'] = context.project_id
            rc['user_id'] = context.user_id
            rc['images'] = [
                c.image for c in entry.spec.template.spec.containers]
            rc['bay_uuid'] = bay_uuid
            # Convert string to dictionary
            rc['labels'] = ast.literal_eval(entry.metadata.labels)
            rc['replicas'] = entry.status.replicas

            rc_obj = objects.ReplicationController(context, **rc)
            rcs.append(rc_obj)

        return rcs
