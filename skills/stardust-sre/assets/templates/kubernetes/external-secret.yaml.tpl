apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: __OPERATIONS_ASSIGNED_SECRET_STORE__
  target:
    name: __NAME__
    creationPolicy: Owner
  data: __CONFIRMED_SECRET_MAPPINGS__
