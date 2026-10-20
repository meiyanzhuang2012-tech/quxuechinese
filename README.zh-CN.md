# 趣学汉语 · 视频生产仓库（QuXue Chinese）

> English: [README.md](README.md)

**一个字，一分钟，一句「原来是这个意思」。**

这里是 **趣学汉语（QuXue Chinese）** 汉语学习短视频账号的生产仓库：面向英语母语的成年自学者，60 秒内讲清一个汉字／词／成语／诗句的**来历**，不出镜、不做场景口语。

这个仓库不是课程，也不是短语手册。每一集只回答一个问题：*它为什么长这样、为什么这么说。*

一集的全部原料都在这里，纯文本 + 素材，所以一年后还能重渲、翻译、纠错、换平台重剪 —— 不用问任何人。

- 🎬 观看：[YouTube @quxuechinese](https://www.youtube.com/@quxuechinese)
- 🗂 落地页与免费字源卡包：GitHub Pages（`main` / `/docs` 发布，源文件在 [`docs/`](docs/)）
- 🐞 纠错优先处理：直接开 [issue](../../issues)

## 目录说明

| 路径 | 放什么 |
|---|---|
| `scripts/episodes/` | **每条视频一个 markdown**：时间轴、逐句英文旁白、屏幕文字、画面说明。这是唯一的源文件。 |
| `scripts/选题库/topics.json` | 选题库（首批 30 条，可持续扩），每条带 `id`／汉字／切入角度／平台。每集 front matter 里的 `topic_id` 对应这里。 |
| `scripts/render.py` | 渲染器：markdown → 配音 → 帧 → ffmpeg → MP4 + SRT。 |
| `assets/字源图/` | 字形演变动图（甲骨 → 金文 → 篆 → 楷），一集一个目录。 |
| `assets/fonts/`、`assets/audio/` | 实际用到的字体与音效（含授权信息）。 |
| `renders/成片/` | 成片输出（`EP-SLUG.mp4` + `.json` 清单）。这里不是归档 —— 成片可由源文件重出。 |
| `subtitles/` | 每集一个 `.srt`，由渲染器生成。 |
| `docs/` | GitHub Pages 站点：落地页、字源卡包下载页、脚本规范。 |
| `make.sh` | 一键出片入口。 |

## 快速开始

```bash
./make.sh --list                 # 列出所有脚本
./make.sh A-001 --none           # 无声版，约 30 秒出片 —— 用它验版式和钩子
./make.sh A-001                  # 带本机 Qwen3-TTS 英文配音出片
./make.sh A-001 --edge           # 备用：edge-tts
./make.sh --all --none           # 批量出无声版
```

产物：`renders/成片/A-001-huo.mp4`、`subtitles/A-001-huo.srt`，视频旁边一并写 `.json` 清单。

依赖：`ffmpeg`（libx264 + aac + libass）、`python3` + `pillow`，配音走本机 TTS 服务（`/tts` 接口，见 `scripts/render.py`）或 `edge-tts`。除此之外不需要装东西。

## 脚本格式

一集 = 一个 markdown：YAML 头 + 分镜表。**加一条视频 = 加一个文件**，不改代码、不登录后台、不接数据库：

```markdown
---
ep: A-001
line: A
slug: huo
title_en: Fire, drawn 3,000 years ago and never updated
hanzi: 火
topic_id: 1
platform: 双        # 双 = YouTube + TikTok 同发，YT = YouTube 优先，TT = TikTok 优先
status: draft
---

| time | vo_en | onscreen_zh | visual |
|---|---|---|---|
| 0:00 | Three thousand years ago, someone scratched fire onto a bone. | 火 | 纸纹底，一个大字 |
```

格式细则、字段含义、常见坑：见 [`docs/脚本规范.md`](docs/脚本规范.md)。

## 为什么用仓库，而不是一个 MP4 文件夹

视频是**构建产物**，真正值钱的是文本、字源素材和时间轴。放进 git 的意义：

- 纠错可 diff、可追溯（字源错误是这类账号的信任红线，必须有版本记录）；
- 60 秒版可无损重剪成 30 秒版投另一个平台，不用重新录音；
- 翻译就是 fork 一个目录；
- 换剪辑、换配音，人走了东西还在。

## 授权

- 代码（`scripts/`、`make.sh`、`docs/` 模板）：MIT。
- 脚本、字源图、成片：**CC BY-NC-SA 4.0** —— 署名、非商用、相同方式共享。商用或品牌素材请先开 issue。
- 第三方字体与音效：见 `assets/fonts/README.md`、`assets/audio/README.md`，每个文件都记录授权与来源链接。**无授权素材一律不入库。**

## 参与纠错

字源和用法上的纠错是这个项目最有价值的贡献 —— 请附工具书或论文依据，我们会在视频简介里署名致谢。
贡献流程见 CONTRIBUTING.md（首次公开发布时补齐）。
