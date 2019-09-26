# group-operator
The group-operator is a Kubernetes operator that enumerates the members of an IAM group and adds them to the mapUsers 
list in the aws-auth ConfigMap. It utilizes Zalando's kopf, a framework for writing Kubernetes operators in Python.  
The operator watches for the creation, modification, or deletion of a iamgroup object.  The iamgroup object is 
implemented as a Custom Resource Definition (CRD) that specifies the IAM group you want to add to the aws-auth ConfigMap 
and the RBAC role/group to associate with the users of that group.  

## Installing the operator

### Creating a IAM role and service account
Since the operator needs to get the members of an IAM group, it needs a Kubernetes service account that allows it to
assume an IAM role that grants it permission to call get_group API.  This is accomplished using the new IAM 
Roles for Service Accounts (IRSA) feature for EKS which requires Kubernetes v1.13 or higher.  

`eksctl` is far and away the easiest way to create the IAM role and corresponding Kubernetes service account.  Start by
running the following command: 

```bash
insert commands here
```

### Creating the RBAC roles
In addition to calling IAM API, the operator calls several Kubernetes APIs.  For example, the operator reads iamgroup 
objects and updates the aws-auth ConfigMap.  There are also a set of permissions required for the kopf framework.  All 
of these permissions are packaged in the rbac.yaml manifest.  You can apply these permissions to the cluster by running:

```bash
kubectl apply -f rbac.yaml
```

### Creating the iamgroups CRD
the group-operator relies on a CRD that specifies the IAM group to add to the aws-auth ConfigMap and the Kubernetes RBAC 
role, e.g. `system:masters` that should be assigned to the members of that group.  Create the CRD by running:

```bash
kubectl apply -f crd.yaml 
```

After the CRD has been created you can create iamgroup objects.  Below is an example of a iamgroup that adds the members
of newgroup to the aws-auth ConfigMap and assigns them the `system:masters` role.  

```yaml
apiVersion: jicomusic.com/v1
kind: IAMGroup
metadata:
  name: newgroup
spec:
  groupName: newgroup
  rbacRole: system:masters
```

### Deploying the operator
The `deployment.yaml` manifest in this repository references a `serviceAccountName` that has to be set to the service 
account created in the [Creating an IAM role and service account](#Creating a IAM role and service account) step above.  
Once that's done, the operator can be deployed by running: 

```bash
kubectl apply -f deployment.yaml 
```

## Create a iamgroup object
With the operator running, create a new iamgroup manifest and apply it to the cluster.  For an example, see the 
`obj.yaml` in this repository. 

After the object has been applied to the cluster, get the aws-auth ConfigMap by running: 

```bash
kubectl get configmap aws-auth -n kube-system -o yaml
```

If the operator is working properly, you should see output resembling this: 

```yaml
apiVersion: v1
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/grateful-banana-nodegroup-ng-bc4be-NodeInstanceRole-10RG7REOWCU6G
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
  mapUsers: |
    - groups:
      - system:masters
      userarn: arn:aws:iam::123456789012:user/rex-ray
      username: rex-ray
    - groups:
      - system:masters
      userarn: arn:aws:iam::123456789012:user/kube-logger
      username: kube-logger
    - groups:
      - view
      userarn: arn:aws:iam::123456789012:user/heptio-ark
      username: heptio-ark
    - groups:
      - view
      userarn: arn:aws:iam::123456789012:user/eks-user
      username: eks-user
kind: ConfigMap
```