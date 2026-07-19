apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: __NAME__
  namespace: __NAMESPACE__
  annotations:
    sre.internal/domain-approval: __DOMAIN_APPROVAL__
spec:
  tls:
    - hosts: [__DOMAIN__]
      secretName: __TLS_SECRET__
  rules:
    - host: __DOMAIN__
      http:
        paths:
          - path: __INGRESS_PATH__
            pathType: Prefix
            backend:
              service:
                name: __NAME__
                port:
                  name: http
