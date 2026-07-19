package main

deny[msg] {
  input.kind == "Secret"
  input.data
  msg := sprintf("Secret/%s 含 data；禁止提交真实 Secret", [input.metadata.name])
}

deny[msg] {
  input.kind == "Secret"
  input.stringData
  msg := sprintf("Secret/%s 含 stringData；禁止提交真实 Secret", [input.metadata.name])
}
