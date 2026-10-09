#!/usr/bin/env bash
# check-skillhub-update.sh —— 检查 SkillHub CLI 自身与 skillhub 装的 skill 是否有新版本
#
# 用法：bash <本脚本> [--dir <skill 安装根>]
# 前置：skillhub CLI 已安装（默认 $HOME/.local/bin/skillhub，可用 SKILLHUB_BIN 覆盖）
#       --dir 不传时，自动找 hub 的远程 skill 缓存槽位（store/cache）
#
# 输出约定：正文给人看，**最后一行固定是状态行**，供自动化解析：
#   STATUS=NO_UPDATE      已是最新，不必打扰用户
#   STATUS=HAS_UPDATE     有更新，细节见上文
#   STATUS=CHECK_FAILED   联网或命令失败，需要人工看一下
# 一律 exit 0 —— 状态一律走 stdout，避免宿主因非零退出码丢掉输出。
#
# 本脚本只读：不下载、不替换任何文件。
#
# 已装 skill 的检测为什么不走 `skillhub upgrade --check-only`：
#   该命令只读技能目录里的 config.json（内含上游 update manifest URL），而 skillhub 渠道
#   的安装**不写** config.json，实测一律 `skip: config.json not found`，等于空跑。
#   这里改为：读 lock 里的本地版本，与详情接口 /api/v1/skills/<slug> 的 latestVersion 比对。

set -uo pipefail

API_HOST="${SKILLHUB_API_HOST:-https://api.skillhub.cn}"
LOCK_NAME=".skills_store_lock.json"

# ---- 定位 CLI ----
CLI="${SKILLHUB_BIN:-}"
if [ -z "$CLI" ]; then
  if [ -x "$HOME/.local/bin/skillhub" ]; then
    CLI="$HOME/.local/bin/skillhub"
  elif command -v skillhub >/dev/null 2>&1; then
    CLI="$(command -v skillhub)"
  fi
fi

# ---- 参数 ----
SKILL_ROOT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dir)     SKILL_ROOT="${2:-}"; shift 2 ;;
    --dir=*)   SKILL_ROOT="${1#--dir=}"; shift ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "未知参数：$1（用 -h 看用法）"; exit 0 ;;
  esac
done

# hub 实体在 $USERPROFILE/.skills（本机 HOME 指向别处，两个都试）
if [ -z "$SKILL_ROOT" ]; then
  for h in "$USERPROFILE/.skills" "$HOME/.skills"; do
    if [ -d "$h/store/cache" ]; then SKILL_ROOT="$h/store/cache"; break; fi
  done
fi

# ---- 定位 python（仅用于解析 JSON，不用于联网）----
PY="${SKILLHUB_PY:-}"
if [ -z "$PY" ]; then
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$(command -v "$c")"; break; fi
  done
fi
if [ -z "$PY" ]; then
  for c in "$USERPROFILE"/.workbuddy/binaries/python/versions/*/python.exe \
             "$HOME"/.workbuddy/binaries/python/versions/*/python.exe; do
    if [ -x "$c" ]; then PY="$c"; break; fi
  done
fi

has_update=0
failed=0

# ---- 1. CLI 自身 ----
echo "== SkillHub CLI 自身 =="
if [ -z "$CLI" ] || [ ! -x "$CLI" ]; then
  echo "SkillHub CLI 未找到（找过 \$HOME/.local/bin/skillhub 与 PATH）"
  failed=1
else
  cli_out="$("$CLI" self-upgrade --check-only 2>&1)"
  if printf '%s' "$cli_out" | grep -qi 'Self-upgrade available'; then
    echo "$cli_out"; has_update=1
  elif printf '%s' "$cli_out" | grep -qi 'Error'; then
    echo "$cli_out"; failed=1
  else
    echo "已是最新（$("$CLI" --version 2>/dev/null | tr -d '\r')）"
  fi
fi

# ---- 2. 已装 skill ----
echo
echo "== 已装 skill（安装根：${SKILL_ROOT:-未找到}）=="
LOCK="${SKILL_ROOT:+$SKILL_ROOT/$LOCK_NAME}"
if [ -z "$SKILL_ROOT" ] || [ ! -f "$LOCK" ]; then
  echo "该目录没有 skillhub 的安装记录（无 $LOCK_NAME），跳过"
elif [ -z "$PY" ]; then
  echo "找不到 python，无法解析 lock / JSON，跳过"
  failed=1
else
  found=0
  while IFS=$'\t' read -r slug local_v; do
    [ -n "$slug" ] || continue
    found=1
    body="$(curl -sS --max-time 25 "$API_HOST/api/v1/skills/$slug" 2>/dev/null)"
    read -r latest state < <(printf '%s' "$body" | "$PY" -c "
import json, re, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('_\tERR'); raise SystemExit
lv = str(((d.get('latestVersion') or {}).get('version')) or '').strip()
def key(v):
    n = tuple(int(x) for x in re.findall(r'\d+', v))
    return n or (0,)
loc = '$local_v'
if not lv:              print('_\tNOVERSION')
elif key(lv) > key(loc): print(lv + '\tNEW')
elif key(lv) < key(loc): print(lv + '\tAHEAD')
else:                    print(lv + '\tOK')
" 2>/dev/null | tr -d '\r')
    case "${state:-}" in
      OK)        printf '  OK    %-28s %s\n' "$slug" "$local_v" ;;
      NEW)       printf '  NEW   %-28s %s -> %s\n' "$slug" "$local_v" "$latest"; has_update=1 ;;
      AHEAD)     printf '  AHEAD %-28s %s（本地更新，线上仍 %s）\n' "$slug" "$local_v" "$latest" ;;
      NOVERSION) printf '  WARN  %-28s 线上未取到版本号\n' "$slug"; failed=1 ;;
      ERR)       printf '  WARN  %-28s 详情接口返回非 JSON\n' "$slug"; failed=1 ;;
      *)         printf '  WARN  %-28s 查询失败（无响应）\n' "$slug"; failed=1 ;;
    esac
  done < <("$PY" -c "
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
for k, v in (d.get('skills') or {}).items():
    print(str(k) + '\t' + str((v or {}).get('version', '')))
" "$LOCK" 2>/dev/null | tr -d '\r')
  [ "$found" -eq 0 ] && echo "lock 里没有已装 skill"
fi

echo
if [ "$has_update" -eq 1 ]; then
  echo "STATUS=HAS_UPDATE"
elif [ "$failed" -eq 1 ]; then
  echo "STATUS=CHECK_FAILED"
else
  echo "STATUS=NO_UPDATE"
fi
exit 0
