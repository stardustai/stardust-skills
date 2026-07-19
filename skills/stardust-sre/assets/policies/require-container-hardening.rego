package main

workload_kind { input.kind == "Deployment" }
workload_kind { input.kind == "StatefulSet" }
workload_kind { input.kind == "DaemonSet" }
workload_kind { input.kind == "Job" }

deny[msg] {
  workload_kind
  container := input.spec.template.spec.containers[_]
  not container.securityContext.allowPrivilegeEscalation == false
  msg := sprintf("%s/%s 容器 %s 必须禁止提权", [input.kind, input.metadata.name, container.name])
}

deny[msg] {
  workload_kind
  container := input.spec.template.spec.containers[_]
  not drops_all(container)
  msg := sprintf("%s/%s 容器 %s 必须删除全部 Capability", [input.kind, input.metadata.name, container.name])
}

drops_all(container) {
  container.securityContext.capabilities.drop[_] == "ALL"
}
