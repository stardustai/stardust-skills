package main

workload_kind { input.kind == "Deployment" }
workload_kind { input.kind == "StatefulSet" }
workload_kind { input.kind == "DaemonSet" }
workload_kind { input.kind == "Job" }

deny[msg] {
  workload_kind
  container := input.spec.template.spec.containers[_]
  endswith(container.image, ":latest")
  msg := sprintf("%s/%s 容器 %s 禁止使用 latest", [input.kind, input.metadata.name, container.name])
}
