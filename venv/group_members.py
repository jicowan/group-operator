from kubernetes import client
from kubernetes.client.rest import ApiException
import kopf
import boto3
import yaml
from botocore import errorfactory
iam = boto3.client('iam')
api = client.CoreV1Api()

@kopf.on.delete('jicomusic.com', 'v1', 'iamgroups')
def delete_fn(meta, spec, namespace, logger, **kwargs):
    group_name = spec.get('groupName')
    aws_auth_users = get_aws_auth_users()
    user_arns = get_group_membership(group_name)
    configmap_data = remove_users(aws_auth_users, user_arns)
    if configmap_data['mapUsers'] != "[]\n":
        configmap_obj = create_configmap_object(configmap_data)
        try:
            api.patch_namespaced_config_map(name="aws-auth", namespace="kube-system", body=configmap_obj)
        except ApiException as e:
            print("Exception when calling CoreV1API->patch_namespaced_config_map: %s\n" % e)
    else:
        configmap_data = api.read_namespaced_config_map(pretty=True, namespace="kube-system", name="aws-auth").data
        configmap_data.pop('mapUsers')
        configmap_obj = create_configmap_object(configmap_data)
        try:
            api.replace_namespaced_config_map(name='aws-auth', namespace='kube-system', body=configmap_obj)
        except ApiException as e:
            print("Exception when calling CoreV1API->replace_namespaced_config_map: %s\n" % e)

@kopf.on.create('jicomusic.com', 'v1', 'iamgroups')
def create_fn(meta, spec, namespace, logger, **kwargs):

    name = meta.get('name')
    group_name = spec.get('groupName')
    rbac_role = spec.get('rbacRole')

    if not group_name:
        raise kopf.PermanentError(f"groupName must be set. Got {group_name!r}.")
    if not rbac_role:
        raise kopf.PermanentError(f"rbacRole must be set. Got {rbac_role!r}.")

    users_arns = get_group_membership(group_name)
    if type(users_arns) is Exception:
        raise Exception("The group does not exist or the group membership is null.")
    else:
        aws_auth_users = get_aws_auth_users()
        if aws_auth_users != None:
            configmap_data = create_patch(users_arns, rbac_role, data=aws_auth_users)
        else:
            configmap_data = create_patch(users_arns, rbac_role)
        configmap_obj = create_configmap_object(configmap_data)

    try:
        api.patch_namespaced_config_map(name="aws-auth", namespace="kube-system", body=configmap_obj)
    except ApiException as e:
        print("Exception when calling CoreV1API->patch_namespaced_config_map: %s\n" % e)

def get_aws_auth_users():
    configmap_data = api.read_namespaced_config_map(pretty=True, namespace="kube-system", name="aws-auth").data
    if 'mapUsers' not in configmap_data:
        return
    else:
        aws_auth_users = configmap_data['mapUsers']
        return aws_auth_users

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
        api_version="v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(name="aws-auth"),
        data=configmap_data
    )
    return configmap

def create_patch(user_arns, rbac_role, data=""):
    configmap_data = []
    for user_arn in user_arns:
        configmap_data.append("- groups:\n  - " + rbac_role + "\n  userarn: " + user_arn + "\n  username: " + user_arn[str(user_arn).find("/") + 1:len(str(user_arn))] + "\n")
    if data != "":
        return {'mapUsers': ''.join(configmap_data) + data}
    else:
        return {'mapUsers': ''.join(configmap_data)}

def remove_users(aws_auth_users, user_arns):
    users = yaml.safe_load(aws_auth_users)
    for user_arn in user_arns:
        for idx, val in enumerate(users):
            if val['userarn'] == user_arn:
                users.pop(idx)
                break
        else:
            print('User not found')
    return {'mapUsers': yaml.safe_dump(users)}