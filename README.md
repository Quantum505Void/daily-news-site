# 🗞️ 小新日报

> AI 驱动的每日新闻简报，自动采集 · 智能摘要 · 每日更新

🔗 **[立即访问 →](https://Quantum505Void.github.io/daily-news-site)**

---

## 📊 状态

| 项目 | 内容 |
|------|------|
| 最新一期 | 2026-03-06 |
| 累计期数 | 2 期 |
| 最后构建 | 2026/03/06 13:34 (CST) |

---

## ✨ 功能

- **11 大板块**：今日看点 · 国内 · 国际 · 军事 · 财经 · 科技 · 娱乐 · 体育 · 汽车 · 旅游 · 热门职位
- **AI 问答**：基于当日日报，Cloudflare Worker + GitHub Copilot gpt-5-mini
- **全文搜索**：Fuse.js，支持模糊匹配，⌘K 快速唤起
- **热词云**：LLM 提取当日热词，点击直接搜索
- **语音播报**：Web Speech API 朗读日报
- **阅读进度条**：顶部滚动进度指示
- **卡片已读状态**：localStorage 记录，已读标题变灰
- **收藏夹**：⭐ 收藏任意条目，跨日期聚合
- **历史浏览**：最近 30 天存档，侧栏 hover 预览摘要
- **键盘导航**：j/k 上下 · o 打开 · b 收藏 · / 搜索
- **主题切换**：暗色/亮色，View Transitions 圆形扩散动画
- **PWA 离线缓存**：Service Worker 缓存资源
- **移动端适配**：底部导航栏，响应式布局

---

## 🏗️ 技术栈

```
前端：Astro 5 + TypeScript（单页 SPA）
构建：Bun
部署：GitHub Pages
AI 代理：Cloudflare Workers（gpt-5-mini via GitHub Copilot）
数据：JSON 文件（public/data/YYYY-MM-DD.json）
搜索：Fuse.js + 预构建索引
```

---

## 🤖 自动化

每日由 [小新](https://github.com/Quantum505Void) 通过脚本自动采集、生成、构建并推送。

---

*README 由构建脚本自动更新*
