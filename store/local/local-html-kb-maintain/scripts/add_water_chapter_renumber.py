#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 c05 之后插入新章 c06「全屋净水系统」，并把原 c06-c24 后移重编为 c07-c25。
同步更新：章节 id、目录/顶部导航、href/data-ch、可见文本引用、h2 编号、part2 副标题。
"""
import re
from pathlib import Path

P = Path(r"C:\Users\cgw06\Desktop\装修\装修知识大全.html")

text = P.read_text(encoding="utf-8")

# ============== 1. 旧章节重编号：c06-c24 -> c07-c25 ==============
old_nums = list(range(6, 25))      # 6..24
new_nums = list(range(7, 26))      # 7..25
old_to_new = {f"c{n:02d}": f"c{m:02d}" for n, m in zip(old_nums, new_nums)}

# section id（两种属性顺序）
def replace_section_id(m):
    cid = m.group(1) or m.group(2)
    if cid in old_to_new:
        return m.group(0).replace(f'id="{cid}"', f'id="{old_to_new[cid]}"', 1)
    return m.group(0)

text = re.sub(
    r'<section\b[^>]*?\b(?:id="(c\d{2})"[^>]*?class="chapter"|class="chapter"[^>]*?id="(c\d{2})")[^>]*>',
    replace_section_id,
    text,
    flags=re.S,
)

# data-ch
text = re.sub(
    r'data-ch="(c\d{2})"',
    lambda m: f'data-ch="{old_to_new.get(m.group(1), m.group(1))}"',
    text,
)

# href="#cNN"
text = re.sub(
    r'href="#(c\d{2})"',
    lambda m: f'href="#{old_to_new.get(m.group(1), m.group(1))}"',
    text,
)

# ============== 2. 其余可见文本中的章节号（非链接/脚本）整体 +1 ==============
def shift_text_refs(s):
    def sub_ref(m):
        n = int(m.group(1))
        return f'c{n + 1}'
    return re.sub(r'\bc(0?[6-9]|1[0-9]|2[0-4])\b', sub_ref, s)

# 跳过 style/script 内容；其余部分把标签和文本分开处理，避免误改标签属性
def process_visible_text(s):
    parts = re.split(r'(<(?:script|style)\b[^>]*>.*?</(?:script|style)>)', s, flags=re.S)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
            continue
        tokens = re.split(r'(<[^>]+>)', part)
        for j, tok in enumerate(tokens):
            if j % 2 == 0:
                tokens[j] = shift_text_refs(tok)
        out.append(''.join(tokens))
    return ''.join(out)

text = process_visible_text(text)

# ============== 3. 修复 <a> 链接文本中的章节号，使其与 href 对齐 ==============
# 放在 process_visible_text 之后，确保链接文本最终与 href 目标一致
def align_link(m):
    prefix = m.group(1)
    href = m.group(2)
    suffix = m.group(3)
    link_text = m.group(4)
    target_match = re.match(r'^#c(\d{2})$', href)
    if not target_match:
        return m.group(0)
    target = int(target_match.group(1))
    # 把链接文本中的 cXX/cX 统一替换为 href 指向的章节号
    new_text = re.sub(r'\bc(0?\d{1,2})\b', lambda _: f'c{target}', link_text)
    return f'{prefix}{href}{suffix}{new_text}</a>'

text = re.sub(
    r'(<a\b[^>]*?\bhref=")(#c\d{2})("[^>]*>)(.*?)(</a>)',
    align_link,
    text,
    flags=re.S,
)

# ============== 4. 插入新章 c06 ==============
new_chapter = '''<section class="chapter" id="c06">
<h2>06 💧 全屋净水系统</h2>
<p class="lead">家庭水处理不是买一个净水器就完事，而是按水质需求做分质供水的系统。本章按“入户—生活用水—直饮水”的链路，梳理各环节的功能、预留与选购要点。</p>

<div class="callout info"><div class="ctitle">🏠 典型系统链路</div><p>前置过滤器 → 中央净水机 → 中央软水机 → 末端直饮机（RO 反渗透 / 超滤），不同区域按需组合。</p></div>

<h3 class="sub">前置过滤</h3>
<p>入户总管处的第一道粗过滤，拦截泥沙、铁锈等大颗粒杂质；过滤精度常见 40–100 微米，需预留冲洗排污口与检修空间。</p>

<h3 class="sub">中央净水机</h3>
<p>安装在前置过滤器之后，吸附余氯、部分有机物并降低重金属含量，改善全屋洗浴、洗涤用水品质；需预留电源与排水。</p>

<h3 class="sub">中央软水机</h3>
<p>通过离子交换降低水中钙、镁离子，减少水垢，保护热水器、花洒、龙头及管道；软水不宜直接饮用，直饮回路需单独设置。</p>

<h3 class="sub">末端直饮</h3>
<p>厨房饮用水终端。RO 反渗透过滤精度最高，可直饮；超滤保留矿物质但无法去除重金属，按当地水质选择。</p>

<h3 class="sub">水电预留要点</h3>
<ul>
<li>入户总水管处预留前置过滤器安装空间与地漏；</li>
<li>中央净水 / 软水机附近预留 10A 插座与排水口；</li>
<li>厨房水槽下预留净水机插座、排水及 2 分管 / 3 分管走管空间；</li>
<li>若做零冷水 / 热水循环，净水回路应避免进入软水机后直饮。</li>
</ul>

<div class="callout tip"><div class="ctitle">💡 选购提示</div><p>不必一次性配齐四级：水质较好地区前置 + 末端 RO 即可，硬水地区再加软水机。滤芯更换周期与长期成本是容易被忽视的隐性开销，下单前务必问清。</p></div>

</section>
'''

# 在原 c06（现已重编号为 c07）之前插入新章
insert_marker = '<section class="chapter" id="c07">\n'
if insert_marker not in text:
    raise RuntimeError("未找到插入位置")
text = text.replace(insert_marker, new_chapter + insert_marker, 1)

# ============== 5. 修正所有 h2 章节序号，使其与 section id 对齐 =============-
def fix_h2_number(m):
    sec_open = m.group(1)
    cid = m.group(2)
    h2_rest = m.group(4)
    num = int(cid[1:])  # c06 -> 6
    return f'{sec_open}{num:02d}{h2_rest}'

# 匹配到 section 开始后的第一个 <h2>...
text = re.sub(
    r'(<section\b[^>]*?\bid="(c\d{2})"[^>]*>.*?<h2>)(\d{2})(\s+.*?</h2>)',
    fix_h2_number,
    text,
    flags=re.S,
)

# ============== 6. 从 c05 的「水路」折叠块中移除「全屋净水」卡片并改计数 ==============
water_summary_old = '<details class="item-fold"><summary class="item-fold-summary">📖 水路（6 条 · 点击展开）</summary><div class="item-grid">'
water_summary_new = '<details class="item-fold"><summary class="item-fold-summary">📖 水路（5 条 · 点击展开）</summary><div class="item-grid">'
text = text.replace(water_summary_old, water_summary_new, 1)

card_to_remove = '''<div class="item">
<div class="term">全屋净水</div>
<div class="desc">家庭水处理系统组合：前置过滤器→中央净水机→中央软水机→末端直饮机（RO反渗透），不同区域分质供水。</div>
</div>'''
if card_to_remove in text:
    text = text.replace(card_to_remove, '', 1)
else:
    print("⚠️ 未找到 c05 内的「全屋净水」卡片")

# ============== 7. 更新 part2 副标题、顶部导航、侧边目录 ==============
# part2 副标题
old_sub = '<span class="part-sub">拆除改造 · 水电隐蔽 · 全屋定位 · 开关插座 · 照明电气 · 暖通</span>'
new_sub = '<span class="part-sub">拆除改造 · 水电隐蔽 · 全屋净水 · 全屋定位 · 开关插座 · 照明电气 · 暖通</span>'
text = text.replace(old_sub, new_sub, 1)

# 顶部导航 part2（此时 href 已重编号完毕）
old_nav = '<div class="nav-chapters"><a href="#c04">拆改基础</a><a href="#c05">水电隐蔽</a><a href="#c07">水电定位</a><a href="#c08">开关插座</a><a href="#c09">照明电气</a><a href="#c10">暖通设备</a></div>'
new_nav = '<div class="nav-chapters"><a href="#c04">拆改基础</a><a href="#c05">水电隐蔽</a><a href="#c06">全屋净水</a><a href="#c07">水电定位</a><a href="#c08">开关插座</a><a href="#c09">照明电气</a><a href="#c10">暖通设备</a></div>'
text = text.replace(old_nav, new_nav, 1)

# 侧边目录 part2
old_toc = '''    <li><a class="toc-ch" href="#c04" data-ch="c04">拆改基础</a></li>
    <li><a class="toc-ch" href="#c05" data-ch="c05">水电隐蔽</a></li>
    <li><a class="toc-ch" href="#c07" data-ch="c07">水电定位</a></li>'''
new_toc = '''    <li><a class="toc-ch" href="#c04" data-ch="c04">拆改基础</a></li>
    <li><a class="toc-ch" href="#c05" data-ch="c05">水电隐蔽</a></li>
    <li><a class="toc-ch" href="#c06" data-ch="c06">💧 全屋净水</a></li>
    <li><a class="toc-ch" href="#c07" data-ch="c07">水电定位</a></li>'''
text = text.replace(old_toc, new_toc, 1)

# ============== 8. 静态章节数统计改为 25（JS 仍会动态覆盖） ==============
text = text.replace('data-count="chapters">24</span>', 'data-count="chapters">25</span>', 1)
text = text.replace('data-stat="chapters">24</div>', 'data-stat="chapters">25</div>', 1)

# 写入
P.write_text(text, encoding="utf-8")
print("✅ 已插入 c06 全屋净水系统，并完成 c06-c24 → c07-c25 重编号")
