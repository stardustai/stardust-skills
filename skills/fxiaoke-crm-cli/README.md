# Fxiaoke CRM CLI Skill

`fxiaoke-crm-cli` 用于通过官方 `sharecrm` CLI 处理纷享销客 CRM 查询和写入任务。CRM 当前登录用户的权限是事实边界。

## 适用场景

- 查询客户、联系人、商机、合同、销售订单、回款、应收、跟进记录。
- 统计销售漏斗、成交周期、合同金额、回款或交付状态。
- 在用户确认后执行 CRM 创建、更新、删除、跟进或其他写操作。

## 前置条件

需要本机可用：

- `sharecrm`
- `jq`

先检查认证状态：

```bash
sharecrm auth status
```

不要询问或输出 token、cookie、密码、API key 或其他凭证。

## 使用原则

1. 用 `sharecrm --help` 和相关子命令 `--help` 确认当前命令面。
2. 查询前先读取对象 schema：

```bash
sharecrm data describe get -d '{"apiName":"ContractObj"}'
```

3. 使用实时对象名、字段名和枚举值查询，不凭记忆猜字段。
4. 默认只读。写操作前必须展示准确变更内容，并让用户立即确认。
5. 分页读取时使用 `LIMIT 50 OFFSET n`，直到 `.queryMeta.returnedCount` 和 `.queryMeta.totalNumber` 显示结果完整。

## 指标报告要求

任何 CRM 指标都要说明：

- 日期范围和时区
- 来源对象
- 日期字段
- 指标字段
- 状态字段和过滤条件
- 纳入的记录范围
- 公式
- 分子和分母

## 目录结构

```text
fxiaoke-crm-cli/
├── SKILL.md
├── evals/
│   └── evals.json
└── references/
    └── cli-reference.md
```

完整命令、指标 recipes 和排错说明见 [CLI reference](references/cli-reference.md)。
