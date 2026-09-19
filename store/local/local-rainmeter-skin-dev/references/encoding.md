# 皮肤文件编码

## 本机实测（抽样 `Documents\Rainmeter\Skins\` 下的 ini）

| 编码 | 个数 | 谁 |
|---|---|---|
| **UTF-16 LE (BOM)** | 1 | **`NotionTodo.ini`（自建，含大量中文）** |
| 无 BOM、可按 UTF-8 解 | 8 | 多数 |
| 无 BOM、非 UTF-8 | 1 | `illustro\Welcome\Welcome.ini` |

→ **自建的中文皮肤选了 UTF-16 LE，这个选择是对的。**

## 推荐：UTF-16 LE with BOM

三个理由：

1. **BOM 是"我是 UTF-16"的信号** —— 没有 BOM 只能靠猜，编辑器和解析器都可能猜错
2. **中文安全** —— GBK 只在中文 Windows 上"看着正常"，换环境就乱码
3. 社区里的中文皮肤普遍这么做

## 三个陷阱

**① 无 BOM 的 UTF-8：能跑，但踩雷**

本机 8 个无 BOM 文件都能跑 —— 因为它们**基本是纯 ASCII**。一旦加中文：
存成 UTF-8 无 BOM 时，Rainmeter 可能按 ANSI 解 → 乱码。
**给皮肤加中文前，先转成 UTF-16 LE + BOM。**

**② ANSI / GBK：单字节，中文必炸**

**③ 脚本写 ini 时要显式指定编码**

```python
# 读写都带 BOM（python 的 "utf-16" 会写 \xff\xfe 头）
t = io.open(path, encoding="utf-16").read()
io.open(path, "w", encoding="utf-16", newline="").write(t)
```

- 要带 BOM → 用 `"utf-16"`；用 `"utf-16-le"` 则**不带** BOM
- **`newline=""`** —— ini 用 `\r\n` 更稳，别让 Python 二次转换

## 在编辑器里转

| 工具 | 操作 |
|---|---|
| Notepad++ | 编码 → 转为 UTF-16 LE BOM |
| VS Code | 右下角编码 → Save with Encoding → UTF-16 LE |
| PowerShell 批量 | 见下 |

```powershell
Get-ChildItem *.ini | ForEach-Object {
    $t = Get-Content $_ -Raw
    # Encoding::Unicode = UTF-16 LE + BOM
    [System.IO.File]::WriteAllText($_.FullName, $t, [System.Text.Encoding]::Unicode)
}
```

## 排查乱码三步

1. **看文件头**（十六进制）：
   - `FF FE` → UTF-16 LE ✓
   - `EF BB BF` → UTF-8 with BOM
   - 其它 → 无 BOM
2. **有中文但无 BOM** → 转成 UTF-16 LE + BOM
3. **转了还乱码** → 就不是编码问题，是**字体**：`FontFace` 要选有中文字形的字体
   （本机的 `NotionTodo.ini` 用系统自带的中文字体一族）
