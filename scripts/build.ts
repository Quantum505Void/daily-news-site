/**
 * scripts/build.ts
 * 1. 同步 ~/Desktop/小新日报-*.json → public/data/
 * 2. 更新 public/manifest.json
 * 3. bun run astro build
 * 4. git add/commit/push
 */

import { readdir, copyFile, mkdir, writeFile, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { execSync } from "node:child_process";

const HOME = process.env.HOME!;
const DESKTOP = `${HOME}/Desktop`;
const REPO = join(import.meta.dir, "..");
const PUBLIC_DATA = join(REPO, "public", "data");
const MANIFEST = join(REPO, "public", "manifest.json");

// ── Sync JSON files ──────────────────────────────────────────────────
async function syncData(): Promise<string[]> {
  await mkdir(PUBLIC_DATA, { recursive: true });

  const files = (await readdir(DESKTOP))
    .filter((f) => f.startsWith("小新日报-") && f.endsWith(".json"))
    .sort()
    .reverse();

  const dates: string[] = [];

  for (const file of files) {
    const src = join(DESKTOP, file);
    const dst = join(PUBLIC_DATA, file);
    const date = file.replace("小新日报-", "").replace(".json", "");
    dates.push(date);

    let needsCopy = !existsSync(dst);
    if (!needsCopy) {
      const [s, d] = await Promise.all([stat(src), stat(dst)]);
      needsCopy = s.mtimeMs > d.mtimeMs;
    }
    if (needsCopy) {
      await copyFile(src, dst);
      console.log(`  ↑ synced ${file}`);
    }
  }

  return dates;
}

// ── Manifest ─────────────────────────────────────────────────────────
async function writeManifest(dates: string[]): Promise<void> {
  await writeFile(
    MANIFEST,
    JSON.stringify({ dates, updated: new Date().toISOString() }, null, 2),
    "utf-8"
  );
}

// ── Astro build ──────────────────────────────────────────────────────
function astroBuild(): void {
  console.log("🔨 Building with Astro...");
  execSync("bun run astro build", { cwd: REPO, stdio: "inherit" });
}

// ── Git push ─────────────────────────────────────────────────────────
function gitPush(): boolean {
  const today = new Date()
    .toLocaleDateString("sv-SE", { timeZone: "Asia/Shanghai" }); // YYYY-MM-DD

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
      console.error(`  ✗ ${cmd.split(" ").slice(2, 4).join(" ")}: ${msg.slice(0, 120)}`);
      return false;
    }
  }
  return true;
}

// ── Main ─────────────────────────────────────────────────────────────
async function main() {
  console.log("🔄 Syncing digest data...");
  const dates = await syncData();
  console.log(`  ${dates.length} digests: ${dates.slice(0, 3).join(", ")}${dates.length > 3 ? "..." : ""}`);

  await writeManifest(dates);
  console.log("  manifest.json updated");

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
