#!/usr/bin/env python3
"""建库脚本：一次性铺出目录骨架 + 说明文件 + 模板。跑一次即可，之后手动维护。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DIRS = [
    "scripts/episodes",
    "scripts/选题库",
    "assets/字源图",
    "assets/fonts",
    "assets/audio",
    "renders/成片",
    "subtitles",
    "docs",
]

FILES = {
    "scripts/选题库/选题规则.md": """# 选题库规则

1. **先拿号再写稿**：新选题先进 `topics.json` 拿 `id`，脚本 front matter 的 `topic_id` 必须能对上。
2. **一条一个知识点**：标题里的钩子词必须在前 5 个词内（Shorts 标题在信息流被截断）。
3. **扩库顺序**（策划案 §3 已定）：
   - 字源类：HSK3 累计词表内高频字，逐字产出（每字 1 条）；
   - 成语类：四大名著 / 中学课本常见 100 成语，按常用度排序；
   - 诗词类：唐诗三百首前 50 首。
4. **状态字段**：`todo` / `scripted` / `published`。`published` 必须同时有 `renders/成片/` 里的成片和平台链接。
5. **查重**：同一汉字/成语只做一次；要做第二个角度，标题必须换钩子并在 `angle` 里写明差异。
""",
    "assets/字源图/README.md": """# 字源图（字形演变素材）

一集一个目录，命名 `<EP>-<汉字>`，例如 `A-001-火/`。

```
A-001-火/
├── 01-jiaguwen.png    甲骨文
├── 02-jinwen.png      金文
├── 03-zhuanshu.png    篆书（有则放）
└── 04-kaishu.png      楷书
```

规则：

- 背景透明 PNG，最短边 ≥ 1200px（1080×1920 竖屏留足放大余量）。
- 每张图必须有来源：优先使用公共领域拓本/摹本（《说文解字》刻本、甲骨文合集等），来源写进 `source.md`。
- **不接受**来源不明的扫描件、他人二创描摹、商用字库截图。
- 同一集内所有字图必须同一笔触风格，否则剪出来会跳。
""",
    "assets/fonts/README.md": """# 字体（授权是硬约束）

| 文件 | 用途 | 授权 | 来源 |
|---|---|---|---|
| （待填）Noto Serif CJK SC | 汉字主视觉 | SIL OFL 1.1 | https://fonts.google.com/noto |

规则：入库前逐条抄下授权名称与链接；商用字体必须先买授权并留合同编号。
""",
    "assets/audio/README.md": """# 音效与配乐

| 文件 | 用途 | 授权 | 来源 |
|---|---|---|---|
| （待填）hit.wav | 字撞合音效 | CC0 | （链接） |

规则：只用 CC0 / 已购授权；**不放进**来源不明的「免版权音乐包」，逐条核对商用条款并留档（策划案 §7.1）。
""",
    "renders/成片/.gitkeep": "",
    "subtitles/.gitkeep": "",
    ".gitignore": """.cache/
*.raw.mp4
__pycache__/
.DS_Store
# 成片体积大：默认不入库，靠 render 重出；要归档就放 GitHub Releases
renders/成片/*.mp4
""",
    "scripts/episodes/_模板.md": """---
ep: A-000
line: A
slug: template
title_en: Hook in the first five words
title_zh: 模板
hanzi: 字
pinyin: zì
topic_id: 0
platform: 双
duration_target: 40
voice: Serena
status: draft
---

# A-000 · 模板

## 分镜

| time | vo_en | onscreen_zh | visual |
|---|---|---|---|
| 0:00 | 钩子：3 秒内一句反直觉英文，不给答案。 | 字 | 一个大字占屏 60% |
| 0:04 | 主体第一拍：画面即证据。 | 甲骨文 · 说明 | 字源图 3 秒 |
| 0:15 | 主体第二拍：逐笔写出今天的样子。 | 楷书 | 逐笔动画 |
| 0:26 | 收束：一句结构性的结论。 | — | 定格 |
| 0:34 | Tomorrow's character has a ___ in it. Guess below. | New character tomorrow 👇 | CTA 字卡 |

## 素材清单

- `assets/字源图/<EP>/01-jiaguwen.png`
- `assets/字源图/<EP>/04-kaishu.png`

## 考据备注

- 依据：（工具书/论文，必须写）
- 异说：（有则写「有，见 X」，无则写「无」）
""",
}

for d in DIRS:
    (ROOT / d).mkdir(parents=True, exist_ok=True)
for rel, content in FILES.items():
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

print("scaffold ok:", ROOT)
for d in DIRS:
    print("  ", d)
