apiVersion: v1
kind: ResourceQuota
metadata:
  name: __PROJECT__-quota
  namespace: __NAMESPACE__
spec:
  hard:
    requests.cpu: __QUOTA_REQUESTS_CPU__
    requests.memory: __QUOTA_REQUESTS_MEMORY__
    limits.cpu: __QUOTA_LIMITS_CPU__
    limits.memory: __QUOTA_LIMITS_MEMORY__
    pods: "__QUOTA_PODS__"
