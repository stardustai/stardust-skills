package main

workload_kind { input.kind == "Deployment" }
workload_kind { input.kind == "StatefulSet" }
workload_kind { input.kind == "DaemonSet" }
workload_kind { input.kind == "Job" }

deny[msg] {
  workload_kind
  container := input.spec.template.spec.containers[_]
  not container.securityContext.readOnlyRootFilesystem
  msg := sprintf("%s/%s 容器 %s 必须使用只读根文件系统", [input.kind, input.metadata.name, container.name])
}
