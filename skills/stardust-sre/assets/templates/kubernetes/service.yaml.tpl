apiVersion: v1
kind: Service
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: __NAME__
  ports:
    - name: http
      port: 80
      targetPort: http
