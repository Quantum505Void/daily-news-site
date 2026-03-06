/**
 * scripts/build.ts
 * 1. 扫描 public/data/ 下的 JSON 文件，更新 manifest.json
 * 2. 预生成全局搜索索引 public/search-index.json
 * 3. bun run astro build
 * 4. git add/commit/push
 */

import { readdir, writeFile, readFile } from "node:fs/promises";
import { join } from "node:path";
import { execSync } from "node:child_process";

const REPO        = join(import.meta.dir, "..");
const PUBLIC_DATA = join(REPO, "public", "data");
const MANIFEST    = join(REPO, "public", "manifest.json");
const SEARCH_IDX  = join(REPO, "public", "search-index.json");

// ── Manifest ─────────────────────────────────────────────────────────
async function writeManifest(): Promise<string[]> {
  const files = (await readdir(PUBLIC_DATA))
    .filter((f) => /^\d{4}-\d{2}-\d{2}\.json$/.test(f))   // 新格式：2026-03-05.json
    .sort()
    .reverse();

  const dates = files.map((f) => f.replace(".json", ""));

  await writeFile(
    MANIFEST,
    JSON.stringify({ dates, updated: new Date().toISOString() }, null, 2),
    "utf-8"
  );
  return dates;
}

// ── Search index ──────────────────────────────────────────────────────
async function writeSearchIndex(dates: string[]): Promise<void> {
  interface Doc {
    date: string;
    secId: string;
    secTitle: string;
    title: string;
    body: string;
    tag: string;
    url: string;
  }
  const docs: Doc[] = [];

  for (const date of dates) {
    try {
      const raw = await readFile(join(PUBLIC_DATA, `${date}.json`), "utf-8");
      const d = JSON.parse(raw);
      for (const sec of d.sections ?? []) {
        for (const item of sec.items ?? []) {
          docs.push({
            date,
            secId: sec.id,
            secTitle: sec.title,
            title: item.title ?? "",
            body: (item.body ?? "").slice(0, 100),   // 只取前100字，控制体积
            tag: item.tag ?? "",
            url: item.url ?? "",
          });
        }
      }
    } catch { /* 跳过损坏文件 */ }
  }

  await writeFile(SEARCH_IDX, JSON.stringify(docs), "utf-8");
  console.log(`🔍 search-index: ${docs.length} docs (${dates.length} days)`);
}

// ── Astro build ──────────────────────────────────────────────────────
function astroBuild(): void {
  console.log("🔨 Building with Astro...");
  execSync("bun run astro build", { cwd: REPO, stdio: "inherit" });
}

// ── Git push ─────────────────────────────────────────────────────────
function gitPush(): boolean {
  const today = new Date()
    .toLocaleDateString("sv-SE", { timeZone: "Asia/Shanghai" });

  const cmds = [
    `git -C ${REPO} add -A`,
    `git -C ${REPO} commit -m "daily: ${today}"`,
    `git -C ${REPO} push origin main`,
  ];

  for (const cmd of cmds) {
    try {
      const out = execSync(cmd, { encoding: "utf-8" });
      if (out.trim()) console.log(" ", out.trim().split("\n")[0]);
    } catch (e: any) {
      const msg: string = (e.stdout ?? "") + (e.stderr ?? "");
      if (msg.includes("nothing to commit")) {
        console.log("  (nothing to commit)");
        return true;
      }
      console.error(`  ✗ ${msg.slice(0, 120)}`);
      return false;
    }
  }
  return true;
}

// ── 更新 README ──────────────────────────────────────────────────────
async function updateReadme(dates: string[]): Promise<void> {
  const latest = dates[0] ?? "—";
  const total  = dates.length;
  const now    = new Date().toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });

  const content = `# 🗞️ 小新日报

> AI 驱动的每日新闻简报，自动采集 · 智能摘要 · 每日更新

🔗 **[立即访问 →](https://Quantum505Void.github.io/daily-news-site)**

---

## 📊 状态

| 项目 | 内容 |
|------|------|
| 最新一期 | ${latest} |
| 累计期数 | ${total} 期 |
| 最后构建 | ${now} (CST) |

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

\`\`\`
前端：Astro 5 + TypeScript（单页 SPA）
构建：Bun
部署：GitHub Pages
AI 代理：Cloudflare Workers（gpt-5-mini via GitHub Copilot）
数据：JSON 文件（public/data/YYYY-MM-DD.json）
搜索：Fuse.js + 预构建索引
\`\`\`

---

## 🤖 自动化

每日由 [小新](https://github.com/Quantum505Void) 通过脚本自动采集、生成、构建并推送。

---

*README 由构建脚本自动更新*
`;

  await writeFile(join(REPO, "README.md"), content, "utf-8");
  console.log(`📝 README updated (latest: ${latest}, total: ${total})`);
}

// ── Main ─────────────────────────────────────────────────────────────
async function main() {
  const dates = await writeManifest();
  console.log(`📋 manifest updated: ${dates.slice(0, 3).join(", ")}${dates.length > 3 ? "..." : ""}`);

  await updateReadme(dates);
  await writeSearchIndex(dates);

  astroBuild();

  console.log("🚀 Pushing to GitHub...");
  const ok = gitPush();
  if (ok) {
    console.log("✅ Done → https://Quantum505Void.github.io/daily-news-site");
  } else {
    console.error("❌ Push failed");
    process.exit(1);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
