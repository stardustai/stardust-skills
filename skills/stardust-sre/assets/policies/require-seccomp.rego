package main

workload_kind { input.kind == "Deployment" }
workload_kind { input.kind == "StatefulSet" }
workload_kind { input.kind == "DaemonSet" }
workload_kind { input.kind == "Job" }

deny[msg] {
  workload_kind
  not input.spec.template.spec.securityContext.seccompProfile.type == "RuntimeDefault"
  msg := sprintf("%s/%s 必须使用 RuntimeDefault seccomp", [input.kind, input.metadata.name])
}
