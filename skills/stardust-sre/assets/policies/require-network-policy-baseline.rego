package main

deny[msg] {
  input.kind == "NetworkPolicy"
  not input.spec.policyTypes
  msg := sprintf("NetworkPolicy/%s 缺少 policyTypes", [input.metadata.name])
}

deny[msg] {
  input.kind == "NetworkPolicy"
  not input.spec.podSelector
  msg := sprintf("NetworkPolicy/%s 缺少 podSelector", [input.metadata.name])
}
