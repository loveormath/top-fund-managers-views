# web/demo — 演示视频占位目录

本目录用于存放 Fund Insight（Web 模块）的演示视频与封面图。

## 当前文件

| 文件 | 说明 |
|---|---|
| `poster.png` | 视频封面图（已生成，仓库根 README 的「演示视频」区块会渲染此封面） |
| `demo.mp4` | 演示视频**占位文件**（当前为文本占位，请替换为你录制好的真实视频） |

## 替换步骤

1. 录制好 Fund Insight 的演示视频（建议 1280×720 或 1920×1080、H.264 编码、时长 1–3 分钟）。
2. 用真实视频**覆盖** `demo.mp4`（保持文件名不变，仓库根 README 的封面链接即自动指向它）。
3. 如需更换封面，覆盖 `poster.png`（建议 16:9）。

## 根 README 中的调用方式

仓库根 `README.md` 在「开篇介绍」后预留了点击播放位：

```markdown
[![Fund Insight 演示](web/demo/poster.png)](web/demo/demo.mp4)
```

GitHub 不直接渲染 `<video>`，因此采用「封面图链接到视频文件」的方式：读者点击封面即可跳转到 `demo.mp4` 播放/下载。
