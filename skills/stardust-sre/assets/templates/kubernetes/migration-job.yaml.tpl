apiVersion: batch/v1
kind: Job
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
  labels:
    app.kubernetes.io/name: __NAME__
    app.kubernetes.io/component: database-migration
spec:
  backoffLimit: 1
  activeDeadlineSeconds: 900
  ttlSecondsAfterFinished: 86400
  template:
    metadata:
      labels:
        app.kubernetes.io/name: __NAME__
    spec:
      restartPolicy: Never
      serviceAccountName: __NAME__
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: __UID__
        runAsGroup: __GID__
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: migration
          image: __IMAGE__
          imagePullPolicy: IfNotPresent
          command: __MIGRATION_COMMAND__
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: {drop: [ALL]}
          resources:
            requests: {cpu: 100m, memory: 128Mi, ephemeral-storage: 64Mi}
            limits: {cpu: "1", memory: 256Mi, ephemeral-storage: 256Mi}
          volumeMounts:
            - {name: tmp, mountPath: /tmp}
      volumes:
        - name: tmp
          emptyDir: {sizeLimit: 64Mi}
