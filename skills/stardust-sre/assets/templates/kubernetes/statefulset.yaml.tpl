apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: __NAME__
spec:
  serviceName: __NAME__-headless
  replicas: 1
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
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
        fsGroup: __GID__
        fsGroupChangePolicy: OnRootMismatch
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: app
          image: __IMAGE__
          imagePullPolicy: IfNotPresent
          ports:
            - {name: http, containerPort: __PORT__, protocol: TCP}
          envFrom:
            - configMapRef: {name: __NAME__}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: [ALL]}
          resources:
            requests: {cpu: 250m, memory: 512Mi, ephemeral-storage: 64Mi}
            limits: {cpu: "1", memory: 512Mi, ephemeral-storage: 256Mi}
          startupProbe:
            httpGet: {path: __HEALTH_PATH__, port: http}
            periodSeconds: 2
            timeoutSeconds: 2
            failureThreshold: 60
          readinessProbe:
            httpGet: {path: __READY_PATH__, port: http}
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          livenessProbe:
            httpGet: {path: __HEALTH_PATH__, port: http}
            periodSeconds: 20
            timeoutSeconds: 3
            failureThreshold: 3
          volumeMounts:
            - {name: data, mountPath: __DATA_PATH__}
            - {name: tmp, mountPath: /tmp}
      volumes:
        - name: tmp
          emptyDir: {sizeLimit: 64Mi}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ReadWriteOnce]
        resources:
          requests: {storage: __STORAGE_SIZE__}
