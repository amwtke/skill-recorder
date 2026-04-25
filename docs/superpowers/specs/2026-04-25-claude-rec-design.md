# claude-rec — Claude Code 会话录制工具

**状态：** Draft
**日期：** 2026-04-25

## 目标

跨平台（macOS + Ubuntu Linux）的 CLI 工具，把 Claude Code 会话录成视频，并自动压缩静止时段。每次录制产出 `.cast`、`.gif`、`.mp4` 三种文件。

## 背景

需要把 Claude Code 中 skill 的执行过程（包括与用户的来回交互）录制下来作为演示/教学素材。常规屏幕录制按 wall-clock 时间录，文件大、含大量"静止"画面、回放枯燥。本工具利用 asciinema 的 idle 压缩，输出聚焦在"实际有变化"时段的精炼录像。

设计上选择"包住 shell"的方式（asciinema 的工作模型），从用户的 shell 启动 `claude-rec`，由它再启动 `claude`。**不在 Claude Code 内部触发录制**——因为 asciinema 必须作为父进程才能录到子 shell 的 I/O。

## 整体架构

单文件 shell 脚本 `claude-rec`，用 `asciinema rec` 包住 `claude` CLI。Claude Code 退出后，脚本自动执行后处理流水线：cast → gif → mp4。

### 组件

| 组件 | 用途 |
|---|---|
| `asciinema` | 录制终端会话为 `.cast` 文件（JSONL + 时间戳） |
| `agg` | `.cast` → `.gif` |
| `ffmpeg` | `.gif` → `.mp4` |

### 数据流

```
$ claude-rec
    ↓
[依赖检查]
    ↓
asciinema rec --idle-time-limit=N --command claude  →  *.cast
    ↓ (claude 退出)
agg *.cast → *.gif
    ↓
ffmpeg *.gif → *.mp4
    ↓
[打印结果]
```

## CLI 接口

```
claude-rec — record a Claude Code session as cast/gif/mp4

Usage: claude-rec [OPTIONS]

Options:
  -o, --output <DIR>     Output directory (default: ~/Recordings/claude-skills)
  -i, --idle <SECONDS>   Compress idle gaps to N seconds (default: 1)
      --no-mp4           Skip mp4 generation (still produces cast + gif)
      --cast-only        Skip all conversion (only .cast file)
  -h, --help             Show this help

Output files: <DIR>/claude-YYYYMMDD-HHMMSS.{cast,gif,mp4}
```

### 用法示例

```bash
claude-rec                              # 默认：cast + gif + mp4
claude-rec --idle 2                     # idle 阈值改为 2s
claude-rec --no-mp4                     # 不要 mp4
claude-rec --cast-only                  # 只录 cast
claude-rec -o /tmp/test                 # 自定义输出目录
claude-rec -o /tmp/test --idle 0.5      # 组合
```

### 参数优先级

- `--cast-only` 优先于 `--no-mp4`（前者更激进，跳过所有转换）
- **不提供** `--no-gif`：mp4 依赖 gif；"要 mp4 不要 gif" 的组合无意义，省掉

## 文件布局

- 脚本本体：`~/.local/bin/claude-rec`（macOS、Ubuntu 通用；需在 `$PATH` 中）
- 默认输出目录：`~/Recordings/claude-skills/`
- 文件命名：`claude-YYYYMMDD-HHMMSS.{cast,gif,mp4}`
- 三个文件全部保留（不自动删除中间产物）

## 跨平台

同一份脚本在两边都跑，**唯一的 OS 区分**只在缺依赖时打印的安装提示文本。

| 依赖 | macOS 安装 | Ubuntu Linux 安装 |
|---|---|---|
| asciinema | `brew install asciinema` | `apt install asciinema` |
| agg | `brew install agg` | `cargo install --git https://github.com/asciinema/agg`（Ubuntu 无 apt 包，需 Rust 工具链） |
| ffmpeg | `brew install ffmpeg` | `apt install ffmpeg` |
| claude | （Claude Code 官方安装方式） | 同左 |

## 错误处理

| 情况 | 行为 |
|---|---|
| 依赖缺失（asciinema/agg/ffmpeg） | 按当前 OS 打印对应安装命令，`exit 1` |
| `claude` 不在 PATH | 打印 "claude not found, install Claude Code"，`exit 1` |
| 录制中 Ctrl-C | asciinema 优雅退出；cast 文件有效；继续后处理 |
| `claude` 异常退出（exit code ≠ 0） | cast 仍然有效；继续后处理；打印 warning |
| `agg` 或 `ffmpeg` 转换失败 | 保留 `.cast`（已完成的中间产物也保留）；打印错误；`exit 0`（录制本体成功） |
| 输出目录创建失败 | 打印错误，`exit 1` |

## 显式不做（YAGNI）

v1 明确不包含：

- Hooks-based 自动触发
- Per-skill 切片 / 边界标记
- 整屏录制（GUI capture）
- 音频录制
- 自动上传 / 分享
- 并发锁（多次同时调用就各录各的；时间戳到秒，理论上不会冲突）
- `--name` 前缀参数（文件名固定时间戳格式；要重命名手动 `mv`）

## 测试

**手动冒烟测试**：

1. 运行 `claude-rec`
2. 在 claude 里输入几条命令、和它对话
3. `/quit` 退出 claude
4. 检查输出目录中 `.cast`、`.gif`、`.mp4` 都生成
5. 用 `asciinema play *.cast` 验证 cast 可回放
6. 用任意播放器打开 `.mp4` 验证可播放
7. 验证录制中"长时间无输出"段被压缩

**测试参数变体**：
- `--cast-only`：只生成 cast，无 gif/mp4
- `--no-mp4`：生成 cast + gif，无 mp4
- `--idle 5`：压缩阈值生效
- `-o /tmp/xxx`：自定义目录生效

**不写自动化测试** —— 脚本是对外部工具的薄包装；集成测试需要 TTY 环境，性价比低。

## 实施大纲

脚本约 60-100 行 bash，主要分段：

1. **参数解析** —— 处理 `-o`、`-i`、`--no-mp4`、`--cast-only`、`-h`
2. **依赖检查** —— `command -v` 每个工具；按 `uname -s` 给对应 OS 的安装命令
3. **路径准备** —— 算时间戳文件名，`mkdir -p` 输出目录
4. **录制** —— `asciinema rec --idle-time-limit=$idle --command claude $cast`
5. **后处理** —— 按参数条件跑 `agg` 和 `ffmpeg`
6. **总结** —— 打印文件路径和大小
