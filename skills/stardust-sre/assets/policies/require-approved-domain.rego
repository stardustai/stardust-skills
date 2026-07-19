package main

deny[msg] {
  input.kind == "Ingress"
  input.metadata.annotations["sre.internal/domain-approval"] != "approved"
  msg := sprintf("Ingress/%s 的域名尚未审批", [input.metadata.name])
}

deny[msg] {
  input.kind == "Ingress"
  host := input.spec.rules[_].host
  endswith(host, ".invalid")
  msg := sprintf("Ingress/%s 仍使用阻断占位域名 %s", [input.metadata.name, host])
}
