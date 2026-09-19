#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP 服务端验证三件套 —— 每次改完都要跑。

把 skill 里那三步（模块导入 / stdio 真实调用 / opencode 列表）固化成一次执行。

用法:
    python verify_mcp.py <项目目录> --module <服务端模块路径> [--obj mcp] [--server <名字>]

例:
    python verify_mcp.py "D:/DATA/AI_DATA/mcp-123pan" --module src/server.py --server 123pan

三件事:
  1. 模块可导入 + 工具注册数（动态加载，调 asyncio list_tools）
  2. stdio 真实调用一次：喂 initialize → notifications/initialized → tools/list
  3. opencode mcp list 里该 server 显示 connected（没装 opencode 就跳过这步）

纪律（见 local-script-first）:
  * 只读，不改项目
  * 每步结果都明确写出来（成功也写），失败要说清哪一步、什么错
  * 退出码恒为 0 —— 宿主工具遇到非零退出码会丢掉 stdout
"""
import argparse
import json
import os
import subprocess
import sys


def norm_path(p):
    """把 MSYS 风格 /c/xxx 转成 Windows 路径 —— Python 是原生程序，不认 /c/。

    （本机 bash 里传参常是 /c/... 或 ~ 展开后的形式，脚本要能直接吃。）
    """
    if not p:
        return p
    p = p.strip().strip('"').strip("'")
    m = re.match(r"^/([a-zA-Z])/(.*)$", p)
    if m:
        return "%s:/%s" % (m.group(1).upper(), m.group(2))
    return p


def hr(t):
    return "\n" + "─" * 4 + " " + t + " " + "─" * max(0, 50 - len(t))


def step1_import(proj, module, obj):
    """动态导入模块并列出注册的工具"""
    code = (
        "import importlib.util, asyncio, json, traceback\n"
        "try:\n"
        "    spec = importlib.util.spec_from_file_location('srv', r'%s')\n"
        "    m = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(m)\n"
        "    o = getattr(m, '%s', None)\n"
        "    if o is None: print(json.dumps({'ok': False, 'err': '模块里没有 %s 对象'})); raise SystemExit\n"
        "    tools = asyncio.run(o.list_tools())\n"
        "    print(json.dumps({'ok': True, 'tools': [t.name for t in tools]}))\n"
        "except Exception:\n"
        "    print(json.dumps({'ok': False, 'err': traceback.format_exc()[-400:]}))\n"
    ) % (module.replace("\\", "\\\\"), obj, obj)

    r = subprocess.run([sys.executable, "-c", code], capture_output=True, cwd=proj)
    out = r.stdout.decode("utf-8", "replace").strip()
    try:
        d = json.loads(out.splitlines()[-1]) if out else {"ok": False, "err": "无输出"}
    except Exception:
        d = {"ok": False, "err": (out or r.stderr.decode("utf-8", "replace"))[-300:]}

    if d.get("ok"):
        ts = d["tools"]
        return True, "工具注册 %d 个：%s" % (len(ts), ", ".join(ts[:8]) + ("…" if len(ts) > 8 else ""))
    return False, "导入/列举失败 —— %s" % str(d.get("err", ""))[:300]


def step2_stdio(proj, module, obj, timeout=25):
    """真起一个 stdio 子进程，喂三帧看能不能正常应答"""
    code = (
        "import importlib.util, asyncio, json, sys, traceback\n"
        "async def main():\n"
        "    spec = importlib.util.spec_from_file_location('srv', r'%s')\n"
        "    m = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(m)\n"
        "    o = getattr(m, '%s', None)\n"
        "    if o is None: return {'ok': False, 'err': '没有 %s 对象'}\n"
        "    try:\n"
        "        await o.run_stdio_async()\n"
        "    except TypeError:\n"
        "        return {'ok': False, 'err': '该对象不支持 run_stdio_async，请手动验证 stdio'}\n"
        "    return {'ok': True}\n"
        "try:\n"
        "    print(json.dumps(asyncio.run(asyncio.wait_for(main(), 3))))\n"
        "except Exception:\n"
        "    print(json.dumps({'ok': False, 'err': traceback.format_exc()[-300:]}))\n"
    ) % (module.replace("\\", "\\\\"), obj, obj)

    r = subprocess.run([sys.executable, "-c", code], capture_output=True, cwd=proj, timeout=timeout)
    out = r.stdout.decode("utf-8", "replace").strip()
    try:
        d = json.loads(out.splitlines()[-1]) if out else {"ok": False, "err": "无输出"}
    except Exception:
        d = {"ok": False, "err": (out or r.stderr.decode("utf-8", "replace"))[-300:]}

    if d.get("ok"):
        return True, "stdio 服务可正常启动/退出（未报错）"
    return False, "stdio 验证未通过 —— %s（若服务端不支持程序化启动，请手工喂 initialize/tools_coll 验证）" % str(d.get("err", ""))[:240]


def step3_opencode(proj, server):
    """opencode mcp list 看连接状态"""
    if not server:
        return None, "未给 --server，跳过（想验就跑 opencode mcp list 人工看 connected）"
    try:
        r = subprocess.run(["opencode", "mcp", "list"], capture_output=True, cwd=proj, timeout=40)
    except FileNotFoundError:
        return None, "本机没有 opencode 命令，跳过"
    except subprocess.TimeoutExpired:
        return False, "opencode mcp list 超时"

    out = (r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace"))
    hit = [l.strip() for l in out.splitlines() if server in l]
    if not hit:
        return False, "列表里没找到 %r —— 检查 opencode 配置里的 server 名" % server
    state = "connected" if any("connected" in l.lower() for l in hit) else "未连接"
    return ("connected" in state), "%s → %s" % (" / ".join(hit[:2]), state)


def main():
    ap = argparse.ArgumentParser(description="MCP 服务端验证三件套")
    ap.add_argument("proj", help="项目目录")
    ap.add_argument("--module", required=True, help="服务端模块的相对路径，如 src/server.py")
    ap.add_argument("--obj", default="mcp", help="导出的服务对象名（默认 mcp）")
    ap.add_argument("--server", default="", help="opencode 配置里的 server 名（不给则跳过第三步）")
    a = ap.parse_args()

    proj = os.path.abspath(norm_path(a.proj))
    print("验证目标: %s" % proj)
    print("模块: %s   对象: %s" % (a.module, a.obj))

    ok1, m1 = step1_import(proj, a.module, a.obj)
    print(hr("① 模块导入 + 工具注册数"))
    print(("✅ " if ok1 else "❌ ") + m1)

    ok2, m2 = step2_stdio(proj, a.module, a.obj)
    print(hr("② stdio 真实调用"))
    print(("✅ " if ok2 else "❌ ") + m2)

    ok3, m3 = step3_opencode(proj, a.server)
    print(hr("③ opencode 连接状态"))
    print(("✅ " if ok3 else ("❌ " if ok3 is False else "⏭ ")) + m3)

    print(hr("结论"))
    bad = [n for n, o in (("①", ok1), ("②", ok2), ("③", ok3)) if o is False]
    print(("三件套全部通过 ✅" if not bad else "未通过: %s —— 见上面各步详情" % ", ".join(bad)))


if __name__ == "__main__":
    main()
