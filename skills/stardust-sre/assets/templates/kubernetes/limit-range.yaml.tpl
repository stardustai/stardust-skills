apiVersion: v1
kind: LimitRange
metadata:
  name: __PROJECT__-limits
  namespace: __NAMESPACE__
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: __DEFAULT_REQUEST_CPU__
        memory: __DEFAULT_REQUEST_MEMORY__
      default:
        cpu: __DEFAULT_LIMIT_CPU__
        memory: __DEFAULT_LIMIT_MEMORY__
