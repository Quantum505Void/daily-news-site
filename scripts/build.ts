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
    .filter((f) => f.startsWith("小新日报-") && f.endsWith(".json"))
    .sort()
    .reverse();

  const dates = files.map((f) => f.replace("小新日报-", "").replace(".json", ""));

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
      const raw = await readFile(join(PUBLIC_DATA, `小新日报-${date}.json`), "utf-8");
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

// ── Main ─────────────────────────────────────────────────────────────
async function main() {
  const dates = await writeManifest();
  console.log(`📋 manifest updated: ${dates.slice(0, 3).join(", ")}${dates.length > 3 ? "..." : ""}`);

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
