#!/usr/bin/env python3
"""根据 deploy-inputs.json 生成平台无关的域名申请草稿。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("deploy/domain-request.md"))
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    ports = ", ".join(str(s.get("port")) for s in data.get("services", []) if s.get("port")) or "待确认"
    text = f"""# 域名申请草稿

> 本草稿不创建 DNS、证书、WAF 或 CDN 配置，由运维流程分配正式值。

- 项目：`{data['project']}`
- 环境：`<ENVIRONMENT_REQUIRED>`
- 申请编号：`{data.get('domain_request', '<DOMAIN_REQUEST_REQUIRED>')}`
- 申请域名：`{data.get('domain', '<DOMAIN_PENDING_APPROVAL>')}`
- 内外网范围：`<NETWORK_SCOPE_REQUIRED>`
- 负责人：`<OWNER_REQUIRED>`
- 目标 Ingress/Gateway/LB：`<OPERATIONS_ASSIGNED_TARGET>`
- 应用端口：`{ports}`
- TLS Secret：`<OPERATIONS_ASSIGNED_TLS_SECRET>`
- DNS TTL：`<OPERATIONS_ASSIGNED_TTL>`

## 上线前确认

- [ ] 域名所有权和环境命名正确
- [ ] DNS 目标由运维分配并审批
- [ ] TLS SAN、有效期和自动续期验证通过
- [ ] 源站、访问控制及平台侧防护已由运维确认
- [ ] 解析、TLS 链、Ingress 路由和健康检查验证通过
- [ ] 已记录旧 DNS 值、回滚目标和传播等待时间
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"已生成 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
