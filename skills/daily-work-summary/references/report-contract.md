# 报告协议

## 证据包

evidence.json 的 schema_version 为 1，包含公司、时区区间、采集时刻和三个 sources。每个来源含 status、scope、gaps、items。

证据包含稳定 id、来源、类型、项目、标题、定位信息、事件时间、时间依据、贡献线索、正文、核验状态、警告及有限元数据。verification=record_only 仅指取得记录，不等于业务完成。

## 整理结果

Agent 阅读相关证据后，先执行以下命令生成 0600 权限模板，再按事项合并条目、填写真实动作和结果。模板的 action/result 为空，未经整理不能通过检查。示例 ID 必须替换成真实证据 ID，不把实际工作内容写进本模板。

```bash
python3 scripts/daily_summary.py prepare-review --bundle /本次私有输出/evidence.json --output /本次私有输出/findings.json
```

```json
{
  "items": [
    {
      "project": "示例项目",
      "title": "工具调用超时排查",
      "action": "定位重试边界并调整异常处理",
      "result": "形成代码改动；回归结果尚待核实",
      "status": "已实现待验证",
      "attribution": "本人开发，依据作者和实际差异核对",
      "time_scope": "uncertain",
      "event_time": null,
      "evidence_ids": ["替换为真实证据ID"],
      "risks": ["未取得对应版本回归结果"],
      "next_steps": ["补充回归验证"]
    }
  ]
}
```

time_scope 为 in_period、historical 或 uncertain。本期成果提供范围内带时区 event_time；证据只有日期时，可将 event_time 置 null 并使用 event_date（YYYY-MM-DD），表示日精度，不虚构时刻。event_date 必须落在统计区间涉及的本地日期内；日内更细归属无法证明时标 uncertain。历史和不确定事项单独展示。

check 校验结构、引用存在和日期区间，不验证语义支撑。Agent 仍须按 [证据判断标准](evidence-policy.md) 审核，不能把检查通过写成业务验收通过。

当前版本只接受已有证据 ID。用户补充、会话和截图可在对话总结中另行标注；不伪造 Git/DWS 记录来导入额外来源。
