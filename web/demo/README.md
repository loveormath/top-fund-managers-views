# Web 模块演示视频（Demo）

把 Fund Insight 的演示视频放在**本目录**，根目录 `README.md` 顶部的「Web 模块演示视频」一节会引用这里。

建议文件名：

- `demo.mp4` —— 推荐，直接嵌入 GitHub README 的 `<video>` 标签
- `demo.gif` —— 轻量预览（如只截一段循环动图）
- `poster.png` —— 视频封面（可选，对应 `<video poster="...">`）

## 怎么接上 README

在根目录 `README.md` 顶部的演示视频一节，把占位替换为实际路径即可：

```html
<video src="web/demo/demo.mp4" controls width="100%" poster="web/demo/poster.png"></video>
```

> 该 `src` 是相对于仓库根的路径，在 GitHub 上可直接加载 `web/demo/demo.mp4`。

## 建议覆盖的内容

- 单人总结 / 多人总结 / 会议讨论 三种模式
- 「设置」录入 DeepSeek Key、知识索引构建过程
- 讨论详情页的「来源抽屉」（直接证据可溯源）
