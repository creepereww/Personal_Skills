"""共享层：定位并调用 easyeda-agent CLI（跨平台，不写死本机路径）。

取数通道由 skill `easyeda-agent-connector` 提供（CLI + daemon + Connector 扩展）；
本 skill 只当"取数"用，不重复它的方法论文档。

CLI 查找顺序：$EASYEDA_BIN > PATH > {HOME,USERPROFILE,~}/.local/bin/easyeda{,.exe}
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 控制台默认可能是 gbk，强制 UTF-8 输出，避免中文/希腊字母报错。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def find_cli():
    env = os.environ.get("EASYEDA_BIN")
    if env and Path(env).is_file():
        return env
    which = shutil.which("easyeda")
    if which:
        return which
    names = ["easyeda.exe", "easyeda"] if os.name == "nt" else ["easyeda"]
    homes = []
    for key in ("HOME", "USERPROFILE"):
        v = os.environ.get(key)
        if v:
            homes.append(v)
    try:
        homes.append(str(Path.home()))
    except Exception:
        pass
    seen = set()
    for home in homes:
        if home in seen:
            continue
        seen.add(home)
        for name in names:
            cand = Path(home) / ".local" / "bin" / name
            try:
                if cand.is_file():
                    return str(cand)
            except OSError:
                pass
    return None


def require_cli():
    bin_path = find_cli()
    if not bin_path:
        raise SystemExit(
            "easyeda CLI 未找到。请安装 easyeda-agent（CLI + daemon + Connector 扩展），"
            "或把可执行文件路径设进 $EASYEDA_BIN。\n"
            "  默认安装位置: ~/.local/bin/easyeda（Windows: ~/.local/bin/easyeda.exe）"
        )
    return bin_path


def run_cli(args, timeout=180):
    """直接执行 CLI，返回 CompletedProcess。"""
    bin_path = require_cli()
    try:
        return subprocess.run(
            [bin_path, *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("CLI 超时(%ss): %s" % (timeout, " ".join(args)))


def _extract_json(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    idxs = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if idxs:
        try:
            return json.loads(text[min(idxs):])
        except Exception:
            pass
    return None


def run_json(args, timeout=180):
    """执行并解析 JSON。已剥离 CLI 的 {id,type,ok,result} 信封；失败即抛错。

    返回 (CompletedProcess, data)。
    """
    proc = run_cli(args, timeout)
    data = _extract_json(proc.stdout or proc.stderr)
    if isinstance(data, dict) and "ok" in data and "result" in data:
        if data.get("ok") is False:
            err = data.get("error") or {}
            raise RuntimeError("CLI 执行失败[%s]: %s %s" % (
                err.get("code", "?"), err.get("message", ""), err.get("detail") or ""))
        data = data["result"]
    return proc, data


_DOC_ROW = re.compile(r"^\s*(★)?\s*(\S+)\s+(.+?)\s+([0-9a-fA-F]{8,})\s*$")


def list_docs(project=None):
    """解析 `easyeda doc ls` 的文本表（★=激活；列: [★] TYPE NAME UUID）。"""
    args = ["doc", "ls"]
    if project:
        args += ["--project", project]
    proc = run_cli(args)
    rows = []
    for line in (proc.stdout or "").splitlines():
        m = _DOC_ROW.match(line)
        if m:
            rows.append({
                "active": bool(m.group(1)),
                "type": m.group(2).lower(),
                "name": m.group(3).strip(),
                "uuid": m.group(4),
            })
    return rows


def activate_doc(project, dtype):
    """把前台文档切到指定类型（schematic|pcb）的第一个文档；返回该文档或 None。"""
    for doc in list_docs(project):
        if doc["type"] == dtype:
            args = ["doc", "open", doc["name"]]
            if project:
                args += ["--project", project]
            run_cli(args)
            return doc
    return None
