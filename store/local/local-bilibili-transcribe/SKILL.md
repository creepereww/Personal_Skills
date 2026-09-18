---
name: local-bilibili-transcribe
description: 把 B 站视频转成带时间戳的文字稿并据此整理笔记，无需登录、没有公开字幕也能做（本地 Whisper 语音识别）。当用户发来 bilibili.com 链接或 BV 号，或提到"导出字幕/转写视频/视频转文字/总结视频知识点/视频笔记/提取文稿"时使用；中文技术视频、教程、访谈都适用。用户只给了本地音视频文件要求转写时，也可直接用其中的 transcribe 子命令。
version: v1.2
---

# B站视频转文字（无登录）

B站字幕接口对匿名请求返回 `need_login_subtitle=true` + 空列表，所以拿不到官方字幕时走这条路：
**取 360P 播放流 → 抽音轨 → 本地 Whisper 转写（优先 GPU）→ 按用户偏好整理成代码为主的笔记**。

实测成本：

- 31 分钟视频，RTX 5070 + medium：全程约 5 分钟（下载 1 分钟 + 转写 4 分钟）
- 7:35 视频，同环境：下载+抽音轨约 40s，**转写仅 18s**（72 段）；模型已缓存时更快
- 短音频转写很快，瓶颈几乎全在装依赖和下载模型上，别被"1.5GB 模型"吓到

## 依赖（先探测再装）

```bash
# 第一步永远先探测，别盲装
python -c "
import importlib
for m in ['faster_whisper','imageio_ffmpeg']:
    try: importlib.import_module(m); print(m,'OK')
    except Exception as e: print(m,'MISSING',e)"
```

```bash
# 缺了再装，务必带清华源
python -m pip install faster-whisper imageio-ffmpeg nvidia-cublas-cu12 nvidia-cudnn-cu12 \
  -i https://pypi.tuna.tsinghua.edu.cn/simple --disable-pip-version-check
```

`imageio-ffmpeg` 自带 ffmpeg 二进制，不必单独装。脚本只用标准库 `urllib`，**不需要 requests**。

**装依赖务必带清华源 `-i`**：默认 PyPI 源在本机会卡在 imageio-ffmpeg(31MB)/cudnn(747MB) 这类大包上不动（实测 10 分钟零进度，只能 kill）。CUDA 两个包合计约 1.3GB，加源后 20 秒装完。长命令挂后台跑。

> 本机 shell 环境（Bash 工具状态、MSYS 与原生程序的路径格式差异、PowerShell 注意点）
> 见 `local-wgc-machine`，本 skill 不重复。

## 流程

### 1. 先取元信息，别急着下载

```bash
python scripts/bili_transcribe.py info --url "https://www.bilibili.com/video/BV1xx411c7XX/"
```

输出包含标题、UP、时长、**官方章节（view_points）**、字幕可用性、以及每个章节的封面帧图片地址。
两点很关键：

- 官方章节本身就是视频的知识骨架，章节封面帧常含目录总览页/终端画面；**先读图往往比转写更快拿到结构**，也能用来校对转写里的专有名词。
- 若 `info` 显示"有公开字幕"，直接下载字幕 JSON，跳过转写。
- **若输出里没有"官方章节"一段**（无 view_points，短教程很常见）：别干等，改用两个替代骨架——
  ① `info` 打印的简介（desc），作者常把步骤/要点写在里面；
  ② 转写后按"命令边界/操作步骤"自己切分，短教程（<5min）通常就一条主线，按步骤编号即可。
  另：续作类视频要在笔记里和上一篇互链，并回改上一篇把"遗留问题"标为已解决。

### 2. 一条龙转写

```bash
python scripts/bili_transcribe.py all \
  --url "https://www.bilibili.com/video/BV1xx411c7XX/" \
  --workdir "$TEMP/bili" \
  --prompt "术语表：WSL、PowerShell、Claude Code、vLLM、nvidia-smi、镜像网络模式……"
```

- `--prompt` 传术语表（`initial_prompt`）能明显降低专有名词错误率，中文技术视频强烈建议传。
- 首次运行会从 hf-mirror 下载模型（medium ≈1.5GB）到 `%TEMP%\whisper_medium`，之后复用。
- 也可拆开跑：`audio` / `model` / `transcribe` 三个子命令。

### 3. 输出与整理

产物：`<workdir>/<BVID>.wav`、`<workdir>/<BVID>.txt`（每行 `[MM:SS] 文本`）。

整理笔记时遵守用户偏好：**以命令/代码块为主，文字描述尽量少**。推荐结构：

```markdown
# <视频标题> · 命令速查
> 来源：B站《<标题>》（<UP>，<时长>）
> 完整文稿：<文稿文件名>（相对链接）

## <章节名>
```bash
<该章节演示的命令>
```
```text
<一句话说明 / 陷阱>
```
```

按官方章节切分，每节只留：命令块 + 最多一两行说明。文稿文件与笔记放同目录，用相对链接互指。

## 会再踩的坑

### ⚠️ 头号陷阱：模型加载成功 ≠ 能推理

```text
日志打印 "模型加载成功: cuda/float16 (2s)" 不代表 GPU 可用 ——
一开始 encode 就崩 RuntimeError: cublas64_12.dll is not found or cannot be loaded。
原因：WhisperModel() 构造时不真正调用 cuBLAS，缺 DLL 要等到推理才暴露。

→ 判定 GPU 真的可用的唯一标准是"转出了第一段"，不是"模型加载成功"。
```

```python
# 解法两步，缺一不可：
#   1) 装包：pip install nvidia-cublas-cu12 nvidia-cudnn-cu12（务必带清华源）
#   2) preload_cuda_dlls() 把 DLL 塞进进程：os.add_dll_directory 单独用无效，
#      必须在 import 后、建模型前把 site-packages/nvidia/*/bin 的 DLL
#      用 ctypes.WinDLL(绝对路径) 预加载 + 插 PATH → 脚本里已实现
#   preload 只解决"DLL 已装但路径没暴露"，包没装它也没辙。
```

### 其他

```text
1. huggingface.co 直连不通；hf-mirror.com 走 huggingface_hub 客户端对 Xet 存储仓库报
   401 Unauthorized → 必须 curl/urllib 直接下 resolve 直链（返回 302 到签名地址，可下）：
   https://hf-mirror.com/Systran/faster-whisper-<size>/resolve/main/model.bin
   该仓库模型文件为 config.json + model.bin + tokenizer.json + vocabulary.txt（无 preprocessor_config.json）
   模型缓存在 %TEMP%\whisper_<size>，已存在会打印"已存在, 跳过"

2. 匿名 playurl 上限 360P（qn=32, platform=html5）；实测请求 32 可能返回 qn=16，
   转写只需要音轨，画质无关，不必纠结

3. 章节封面帧 URL 是 http://（非 https）+ i0.hdslb.com，直接 urllib 抓会被 403 挡
   → 必须带 headers：User-Agent + Referer: https://www.bilibili.com/

4. 脚本里 `--out` 必须在 `transcribe` 和 `all` 两个子命令上都可读：`all` 会转调 `transcribe`，
   取参数要用 `getattr(args, "out", None)`，否则 `all` 直接崩 AttributeError。
```

### 转写质量：错字必然出现，必须二次校对

```text
中文技术视频口播快，专有名词必定出错，实测错法全是音近替换：
  pacman -Syu  → "packman-sue"     fuzzel/alacritty → "fuzzle-elecrede"
  swaybg       → "swabg"           gitee            → "該替倉庫"
  Wayland      → "VLAN"            平铺式            → "评估式"

--prompt 术语表有帮助但不能根治。三个校对源，按性价比排序：
  1) 官方章节封面帧 —— Read 工具直接看图，终端画面里的命令是准的
  2) 视频简介里的仓库链接 —— 抓作者 gitee/GitHub 对应文档，命令通常一字不差
  3) 该软件的官方文档

校对后要在笔记末尾显式写一节"转写勘误"列出改了什么，别默默改掉——
方便用户判断哪些是视频原话、哪些是我的修正。
```

## 交付前自检

- [ ] 真的转出了第一段（不是"模型加载成功"）→ GPU 才算跑通
- [ ] 文稿里抽查 2-3 段，确认术语正确（错了就带 `--prompt` 重跑，或在笔记里改对）
- [ ] 术语已用章节封面帧 / 作者仓库交叉校对，笔记里有"转写勘误"一节
- [ ] 笔记里的每个命令块对应到具体章节，别把没演示过的命令写进去
- [ ] 文稿/笔记文件确实落在磁盘上（用 python 列目录验证）
