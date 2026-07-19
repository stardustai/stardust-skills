apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
subjects:
  - kind: ServiceAccount
    name: __NAME__
    namespace: __NAMESPACE__
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: __NAME__
