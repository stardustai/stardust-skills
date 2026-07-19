apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: __NAME__-default-deny
  namespace: __NAMESPACE__
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: __NAME__
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              sre.internal/ingress-enabled: "true"
      ports:
        - protocol: TCP
          port: __PORT__
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
