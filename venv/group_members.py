import kubernetes
from kubernetes import client
import yaml
import kopf
import os
import boto3
from botocore import errorfactory
iam = boto3.client('iam')

@kopf.on.create('jicomusic.com', 'v1', 'iamgroups')
def create_fn(meta, spec, namespace, logger, **kwargs):

    name = meta.get('name')
    group_name = spec.get('groupName')
    if not group_name:
        raise kopf.PermanentError(f"groupName must be set. Got {group_name!r}.")

    users_arns = get_group_membership(group_name)
    configmap_data = create_patch(users_arns)
    configmap_obj = create_configmap_object(configmap_data)
    api = kubernetes.client.CoreV1Api()

    try:
        api.patch_namespaced_config_map(name="aws-auth", namespace="kube-system", body=configmap_obj)
    except ApiException as e:
        print("Exception when calling CoreV1API->patch_namespaced_config_map: %s\n" % e)

def get_group_membership(group_name):
    try:
        group_members = iam.get_group(GroupName=group_name)['Users']
    except errorfactory.ClientError:
        return Exception('No matching group found.')
    if group_members == []:
        return Exception('Group has no members.')
    user_arns = map(lambda x: x['Arn'], group_members)
    return(list(user_arns))

def create_configmap_object(configmap_data):
    configmap = client.V1ConfigMap(
        api_version="core/v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(name="aws-auth"),
        data=configmap_data
    )
    return configmap

def create_patch(user_arns):
    configmap_data = []
    for user_arn in user_arns:
        configmap_data.append("- groups:\n  - system:masters\n  userarn: " + user_arn + "\n  username: " + user_arn[str(user_arn).find("/") + 1:len(str(user_arn))] + "\n")
    return {'mapUsers': ''.join(configmap_data)}