# demo/ — MCP Server 演示视频与封面

本目录用于存放 **MCP Server**（根模块，详见根目录 `README.md` 第七节）的演示视频与封面图。

## 当前文件

| 文件 | 说明 | 大小 |
|---|---|---|
| `poster.png` | 视频封面图（从视频第 5 秒抽取，仓库根 README 的「演示视频」区块会渲染此封面） | 102 KB |
| `demo.mp4` | MCP Server 演示视频（H.264 1280×836 / 30fps / CRF 23，源 `.mov` 3246×2122 / 57fps / 11.8 Mbps 已压缩） | 4.4 MB |

## 关于 GitHub 直接播放

GitHub 不直接渲染 `<video>`，因此采用与 `web/demo/` 一致的「封面图链接到视频文件」方式：

```markdown
[![MCP 演示](demo/poster.png)](demo/demo.mp4)
```

读者点击封面即可跳转播放 / 下载视频。

## 替换 / 更新步骤

1. 重新录制 MCP Server 演示视频（建议 1280×720 或更高、H.264 编码、时长 1–3 分钟）。
2. 用真实视频覆盖 `demo.mp4`（保持文件名不变，仓库根 README 的封面链接即自动指向它）。
3. 如需更换封面，覆盖 `poster.png`（建议 16:9，可用 ffmpeg 从视频第 5 秒附近抽取一帧）。

## 压缩参考命令

源视频如果是高分辨率大文件（如 `.mov` / `.mkv`），可用 ffmpeg 压缩到适合仓库的体积（目标 < 50 MB）：

```bash
ffmpeg -y -i source.mov \
  -vf "scale=1280:-2,fps=30" \
  -c:v libx264 -preset slow -crf 23 \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  demo.mp4
```

并从第 5 秒附近抽取封面：

```bash
ffmpeg -y -ss 00:00:05 -i source.mov \
  -frames:v 1 -vf "scale=1280:-1" \
  demo/poster.png
```