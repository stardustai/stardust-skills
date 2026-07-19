package main

workload_kind { input.kind == "Deployment" }
workload_kind { input.kind == "StatefulSet" }
workload_kind { input.kind == "DaemonSet" }
workload_kind { input.kind == "Job" }

deny[msg] {
  workload_kind
  container := input.spec.template.spec.containers[_]
  not container.resources.requests.cpu
  msg := sprintf("%s/%s 容器 %s 缺少 CPU request", [input.kind, input.metadata.name, container.name])
}

deny[msg] {
  workload_kind
  container := input.spec.template.spec.containers[_]
  not container.resources.limits.memory
  msg := sprintf("%s/%s 容器 %s 缺少内存 limit", [input.kind, input.metadata.name, container.name])
}
