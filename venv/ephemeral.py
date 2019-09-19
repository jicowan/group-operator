import kopf
import kubernetes
import yaml
import os

@kopf.on.create('zalando.org', 'v1', 'ephemeralvolumeclaims')
def create_fn(meta, spec, namespace, logger, **kwargs):

    name = meta.get('name')
    size = spec.get('size')
    if not size:
        raise kopf.PermanentError(f"Size must be set. Got {size!r}.")
    path = os.path.join(os.path.dirname(__file__), 'pvc.yaml')
    tmpl = open(path, 'rt').read()
    text = tmpl.format(name=name, size=size)
    data = yaml.safe_load(text)

    api = kubernetes.client.CoreV1Api()
    obj = api.create_namespaced_persistent_volume_claim(
        namespace=namespace,
        body=data,
    )
    logger.info(f"PVC child is created: %s", obj)