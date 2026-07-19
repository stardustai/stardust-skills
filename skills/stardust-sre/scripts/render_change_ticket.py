#!/usr/bin/env python3
"""根据 deploy-inputs.json 生成运维变更工单草稿。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("deploy/change-ticket.md"))
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    services = "\n".join(
        f"- `{s['name']}`：{s['workload']}，镜像 `{s['image']}`，端口 `{s.get('port', 'N/A')}`"
        for s in data.get("services", [])
    )
    text = f"""# 运维变更工单草稿

> 本文件是平台无关草稿，由项目组复制到实际工单系统。不得直接作为审批结果。

- 项目：`{data['project']}`
- Namespace：`{data['namespace']}`
- 变更工单编号：`{data.get('change_ticket', '<CHANGE_TICKET_REQUIRED>')}`
- 域名申请编号：`{data.get('domain_request', '<DOMAIN_REQUEST_REQUIRED>')}`
- 计划域名：`{data.get('domain', '<DOMAIN_PENDING_APPROVAL>')}`
- 审查人：于海龙或其正式授权的 SRE 代理人

## 工作负载

{services or '- 尚未识别服务'}

## 项目组必须填写

- [ ] 环境、负责人和计划窗口
- [ ] 架构、上下游依赖及端口
- [ ] 数据分类、Secret 来源及日志脱敏
- [ ] CPU、内存、临时存储和容量依据
- [ ] 持久化、备份、RTO/RPO 和恢复测试
- [ ] 镜像 Digest、SBOM、签名和漏洞扫描结果
- [ ] 验证步骤、观察指标、停止条件和回滚方案
- [ ] 域名申请、TLS 与 DNS 回滚目标
- [ ] 于海龙或授权代理人审查结论
- [ ] 首次 CI/CD 灰度范围和观察结果
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"已生成 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
