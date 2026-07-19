apiVersion: v1
kind: Service
metadata:
  name: __NAME__-headless
  namespace: __NAMESPACE__
spec:
  clusterIP: None
  selector:
    app.kubernetes.io/name: __NAME__
  ports:
    - name: http
      port: __PORT__
      targetPort: http
