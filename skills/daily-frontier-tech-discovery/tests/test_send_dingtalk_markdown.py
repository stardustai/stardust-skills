from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "send_dingtalk_markdown.py"
SPEC = importlib.util.spec_from_file_location("send_dingtalk_markdown", SCRIPT)
assert SPEC and SPEC.loader
sender = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sender)


def test_rejects_dingtalk_business_error() -> None:
    response = json.dumps({"errcode": 310000, "errmsg": "keywords not in content"})

    try:
        sender._validate_response(response)
    except RuntimeError as exc:
        assert "errcode=310000" in str(exc)
    else:
        raise AssertionError("non-zero DingTalk errcode must fail")


def test_accepts_success_response() -> None:
    assert sender._validate_response('{"errcode":0,"errmsg":"ok"}') == {
        "errcode": 0,
        "errmsg": "ok",
    }


def test_config_requires_mode_600(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text('{"webhook":"https://example.test","secret":"secret"}')
    config.chmod(0o644)

    try:
        sender._read_config(str(config))
    except RuntimeError as exc:
        assert "mode 600" in str(exc)
    else:
        raise AssertionError("overly broad config permissions must fail")


def test_dry_run_does_not_require_config(capsys) -> None:
    exit_code = sender.main(
        [
            "--title",
            "每日前沿技术洞察",
            "--text",
            "# 日报\n- 技术信号 [来源](https://example.test)",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
