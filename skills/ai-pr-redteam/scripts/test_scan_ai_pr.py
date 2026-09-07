#!/usr/bin/env python3
import json
import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("scan_ai_pr.py")


def run_scan(repo: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(repo), "--format", "json"],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def categories(report: dict) -> set[str]:
    return {signal["category"] for signal in report["signals"]}


def messages(report: dict) -> str:
    return "\n".join(signal["message"] for signal in report["signals"])


def test_typescript_react_redteam_signals() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write(
            repo / "package.json",
            """
            {
              "name": "bad-ai-pr",
              "private": true,
              "dependencies": {
                "react": "latest",
                "typescript": "latest"
              }
            }
            """,
        )
        write(repo / ".env.example", "API_BASE_URL=http://localhost:3000")
        write(
            repo / "src/api/tasks.ts",
            """
            export async function loadTasks() {
              try {
                await fetch(process.env.REMOTE_TASK_URL!);
              } catch (error) {
                console.warn("remote failed, using fallback", error);
                return [{ id: "demo", title: "sample task" }];
              }
              return [];
            }
            """,
        )
        write(
            repo / "src/components/TaskPanel.tsx",
            """
            import React from "react";
            import { prisma } from "../db";

            export function TaskPanel() {
              const tasks = prisma.task.findMany();
              return <pre>{JSON.stringify(tasks)}</pre>;
            }
            """,
        )
        write(
            repo / "tests/tasks.test.ts",
            """
            it("loads tasks", async () => {
              const response = await request(app).get("/api/tasks");
              expect(response.status).toBe(200);
            });
            """,
        )

        report = run_scan(repo)

        assert "TypeScript" in report["language_inventory"]["primary_languages"]
        assert {"fake-fallback", "env-drift", "weak-test", "engineering-quality"} <= categories(report)
        assert any(signal["severity"] == "BLOCKER" for signal in report["signals"])
        assert "React UI code should not reach database clients directly" in messages(report)


def test_python_language_specific_quality_signals() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        write(repo / "pyproject.toml", "[project]\nname = 'bad-ai-python-pr'")
        write(
            repo / "service.py",
            """
            def append_user(user, users=[]):
                users.append(user)
                return users

            def fetch_records(client):
                try:
                    return client.fetch()
                except Exception:
                    return []
            """,
        )

        report = run_scan(repo)

        assert "Python" in report["language_inventory"]["primary_languages"]
        assert {"fake-fallback", "engineering-quality"} <= categories(report)
        assert "Python functions should not use mutable default arguments" in messages(report)
        assert "Python broad exception fallback hides operational failure" in messages(report)


if __name__ == "__main__":
    test_typescript_react_redteam_signals()
    test_python_language_specific_quality_signals()
    print("scan_ai_pr tests passed")
