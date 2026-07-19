apiVersion: apps/v1
kind: Deployment
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: __NAME__
spec:
  replicas: 2
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate: {maxSurge: 1, maxUnavailable: 0}
  selector:
    matchLabels:
      app.kubernetes.io/name: __NAME__
  template:
    metadata:
      labels:
        app.kubernetes.io/name: __NAME__
    spec:
      serviceAccountName: __NAME__
      automountServiceAccountToken: false
      enableServiceLinks: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: __UID__
        runAsGroup: __GID__
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: worker
          image: __IMAGE__
          imagePullPolicy: IfNotPresent
          envFrom:
            - configMapRef: {name: __NAME__}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: [ALL]}
          resources:
            requests: {cpu: 100m, memory: 256Mi, ephemeral-storage: 64Mi}
            limits: {cpu: "1", memory: 256Mi, ephemeral-storage: 256Mi}
          startupProbe:
            exec: {command: __PROBE_COMMAND__}
            periodSeconds: 2
            timeoutSeconds: 2
            failureThreshold: 30
          readinessProbe:
            exec: {command: __PROBE_COMMAND__}
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          livenessProbe:
            exec: {command: __PROBE_COMMAND__}
            periodSeconds: 20
            timeoutSeconds: 3
            failureThreshold: 3
          volumeMounts:
            - {name: tmp, mountPath: /tmp}
      volumes:
        - name: tmp
          emptyDir: {sizeLimit: 64Mi}
