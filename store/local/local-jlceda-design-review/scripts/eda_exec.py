#!/usr/bin/env python3
"""通用"任意 eda.* JS"执行器 —— 经 easyeda-agent 的逃生口 `debug exec` 执行。

用法: python eda_exec.py <js文件> [--project NAME] [--window ID] [--timeout 秒]

语义：文件里的 JS 在 EDA 端执行，**最后必须 return**（`result.value` 即结果）。
**不会自动切前台**：`eda.sch_*` 要看原理图、`eda.pcb_*` 要看 PCB（先用 `easyeda doc open <名>` 切）。
返回的 result.value 会被打印（字符串原样、其余 JSON 缩进）。
用途：typed 命令覆盖不到的一次性取证（读导线坐标、量距离、复核异网接触…）。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eda_conn import run_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("js_file")
    ap.add_argument("--project", default=None)
    ap.add_argument("--window", default=None)
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()

    with open(args.js_file, encoding="utf-8") as fh:
        code = fh.read()

    cli_args = ["debug", "exec", "--code", code, "--timeout", str(args.timeout)]
    if args.project:
        cli_args += ["--project", args.project]
    if args.window:
        cli_args += ["--window", args.window]

    _proc, data = run_json(cli_args, timeout=args.timeout + 15)
    value = data.get("value") if isinstance(data, dict) and "value" in data else data
    print(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
