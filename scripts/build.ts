/**
 * scripts/build.ts
 * 1. 扫描 public/data/ 下的 JSON 文件，更新 manifest.json
 * 2. bun run astro build
 * 3. git add/commit/push
 */

import { readdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { execSync } from "node:child_process";

const REPO        = join(import.meta.dir, "..");
const PUBLIC_DATA = join(REPO, "public", "data");
const MANIFEST    = join(REPO, "public", "manifest.json");

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
