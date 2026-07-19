apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: __NAME__
  minReplicas: __MIN_REPLICAS__
  maxReplicas: __MAX_REPLICAS__
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: __TARGET_CPU_PERCENT__
