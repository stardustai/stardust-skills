#!/usr/bin/env python3
"""公司工作总结：采集证据，不自动替用户认领成果或发布。"""

import argparse
import concurrent.futures
import copy
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

from work_summary import __version__
from work_summary.common import json_text, make_window, private_write, safe_text
from work_summary.config import DEFAULTS, load_config
from work_summary.report import render, validate_bundle, validate_findings


SKILL_ROOT = Path(__file__).resolve().parents[1]


def outside_repository(path):
    resolved = Path(path).expanduser().resolve()
    if resolved == SKILL_ROOT or SKILL_ROOT in resolved.parents:
        raise ValueError("真实配置与运行数据必须保存到 Skill 仓库外")
    for parent in [resolved] + list(resolved.parents):
        if (parent / ".git").exists():
            raise ValueError("真实配置与运行数据不得写入 Git 工作树")
    return resolved


def load_bundle(path):
    path = Path(path).expanduser()
    if path.stat().st_size > 150000000:
        raise ValueError("证据包过大，请缩小采集范围")
    return validate_bundle(json.loads(path.read_text(encoding="utf-8")))


def collect_all(config, window, offline=False):
    from work_summary import git_source, local_source, dingtalk_source
    tasks = {"git": git_source.collect, "local": local_source.collect, "dingtalk": dingtalk_source.collect}
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        for name, collector in tasks.items():
            if name == "dingtalk" and offline:
                results[name] = {"source": name, "status": "unavailable", "scope": [], "items": [], "gaps": ["本次 --offline 主动跳过钉钉，未核查云端材料"]}
            else:
                futures[pool.submit(collector, config, window)] = name
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                if result.get("gaps") and result.get("status") == "complete":
                    result["status"] = "partial"
                results[name] = result
            except Exception as exc:
                results[name] = {"source": name, "status": "unavailable", "scope": [], "items": [],
                                 "gaps": ["采集失败（%s），请检查范围、工具版本和配置；未保存原始异常以避免泄露内容" % type(exc).__name__]}
    bundle = {"schema_version": 1, "tool_version": __version__, "company": config["company"]["name"],
              "window": window, "sources": [results[name] for name in ("git", "dingtalk", "local")]}
    return validate_bundle(bundle)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="生成仓库外的本地配置，不自动读取数据")
    init.add_argument("--config", required=True)
    init.add_argument("--company", required=True)
    init.add_argument("--name", default="")
    doctor = commands.add_parser("doctor", help="检查配置和工具，不采集正文")
    doctor.add_argument("--config", required=True)
    collect = commands.add_parser("collect", help="只读采集三类来源，生成私有证据包与待核对草稿")
    collect.add_argument("--config", required=True)
    collect.add_argument("--start", help="起始日期（含）或带时区 ISO 时间")
    collect.add_argument("--end", help="结束日期（含）或带时区 ISO 时间（不含）")
    collect.add_argument("--output-dir", help="新的仓库外目录；默认用户私有状态目录")
    collect.add_argument("--offline", action="store_true")
    for name in ("render", "check", "prepare-review"):
        command = commands.add_parser(name, help="生成报告" if name == "render" else "校验证据与整理结果的引用、日期和结构")
        command.add_argument("--bundle", required=True)
        command.add_argument("--findings")
        if name in ("render", "prepare-review"):
            command.add_argument("--output", help="仓库外新文件；不提供则输出到终端")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            config = copy.deepcopy(DEFAULTS)
            config["company"]["name"], config["identity"]["name"] = args.company, args.name
            path = outside_repository(args.config)
            private_write(path, json_text(config))
            print("配置已创建：%s\n请填写公司仓库、本人 Git 邮箱、本地目录和钉钉查询范围，再运行 doctor。" % path)
            return 0
        if args.command == "doctor":
            config = load_config(args.config)
            checks = [{"item": "配置与公司范围", "ok": True}, {"item": "Git", "ok": bool(shutil.which("git"))},
                      {"item": "钉钉 CLI（启用时必需）", "ok": bool(shutil.which("dws")) or not config["dingtalk"]["enabled"]},
                      {"item": "PDF 正文提取（可选）", "ok": bool(shutil.which("pdftotext")), "optional": True}]
            for section, field in (("git", "repositories"), ("local", "roots")):
                for entry in config[section][field]:
                    checks.append({"item": section + "：" + entry["path"], "ok": Path(entry["path"]).is_dir()})
            print(json_text({"checks": checks, "notice": "仅本地检查；未验证钉钉授权、正文权限或业务成果"}))
            return 0 if all(c["ok"] or c.get("optional") for c in checks) else 2
        if args.command == "collect":
            config = load_config(args.config)
            window = make_window(args.start, args.end, config["timezone"])
            name = window["observed_at"].replace(":", "").replace("+", "_") + "-" + uuid.uuid4().hex[:8]
            destination = outside_repository(args.output_dir or str(Path.home() / ".local/state/daily-work-summary/runs" / name))
            if destination.exists():
                raise ValueError("输出目录已存在；请指定新的目录，避免覆盖历史证据")
            for root in config["local"]["roots"] + config["git"]["repositories"]:
                source_path = Path(root["path"]).resolve()
                if source_path == destination or source_path in destination.parents:
                    raise ValueError("输出不得位于采集目录中，避免重复采集和泄露")
            destination.mkdir(parents=True, mode=0o700)
            os.chmod(destination, 0o700)
            bundle = collect_all(config, window, args.offline)
            private_write(destination / "evidence.json", json_text(bundle))
            private_write(destination / "draft.md", render(bundle))
            summary = {"output_dir": str(destination), "sources": [{"source": s["source"], "status": s["status"],
                       "evidence_count": len(s["items"]), "gap_count": len(s["gaps"])} for s in bundle["sources"]],
                       "notice": "记录数不是工作量；draft.md 须核对后才能作为日报。"}
            private_write(destination / "manifest.json", json_text(summary))
            print(json_text(summary))
            return 0 if all(s["status"] == "complete" for s in bundle["sources"]) else 2
        bundle = load_bundle(args.bundle)
        if args.command == "prepare-review":
            if not args.output:
                raise ValueError("prepare-review 需要 --output 指定新的私有 findings.json")
            template = {"items": [{"project": item.get("project", "待确认"), "title": item.get("title", "待确认"),
                       "action": "", "result": "", "status": "待核对", "attribution": "待核对",
                       "time_scope": "uncertain", "event_time": None, "event_date": None,
                       "evidence_ids": [item["id"]], "risks": [], "next_steps": []}
                       for source in bundle["sources"] for item in source["items"]]}
            private_write(outside_repository(args.output), json_text(template))
            print("私有整理模板已生成；请按工作事项合并并核对正文，补全 action/result 后执行 check。")
            return 0
        findings = None
        if args.findings:
            findings_path = Path(args.findings).expanduser()
            if findings_path.stat().st_size > 5000000:
                raise ValueError("整理结果文件过大")
            findings = validate_findings(json.loads(findings_path.read_text(encoding="utf-8")), bundle)
        if args.command == "check":
            print("结构、日期和证据引用检查通过；这不代表业务事实已由程序验证。")
        else:
            report = render(bundle, findings)
            if args.output:
                private_write(outside_repository(args.output), report)
                print("报告已生成：" + str(Path(args.output).expanduser()))
            else:
                print(report)
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc:
        print("错误：" + safe_text(str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
