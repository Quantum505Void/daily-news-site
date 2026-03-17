export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    const url = new URL(request.url);

    // ── /vote — 每日一问投票 ──
    if (url.pathname === "/vote") {
      const date = url.searchParams.get("date");
      if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
        return json({ error: "invalid date" }, 400);
      }
      const kvKey = `vote_${date}`;

      if (request.method === "GET") {
        const raw = await env.VOTE_KV.get(kvKey);
        const tally = raw ? JSON.parse(raw) : null;
        return json({ date, tally });
      }

      if (request.method === "POST") {
        const body = await request.json();
        const idx = parseInt(body.idx);
        const total = parseInt(body.total);
        if (isNaN(idx) || isNaN(total) || idx < 0 || idx >= total) {
          return json({ error: "invalid idx/total" }, 400);
        }
        const raw = await env.VOTE_KV.get(kvKey);
        const tally = raw ? JSON.parse(raw) : Array(total).fill(0);
        tally[idx] = (tally[idx] ?? 0) + 1;
        await env.VOTE_KV.put(kvKey, JSON.stringify(tally), { expirationTtl: 60 * 60 * 24 * 90 });
        return json({ date, tally });
      }
    }

    // ── /quote — 行情代理 (GET) ──
    if (url.pathname === "/quote") {
      const syms = url.searchParams.get("symbols") ?? "";
      if (!syms) return json({ error: "missing symbols" }, 400);
      try {
        const upstream = `https://query2.finance.yahoo.com/v8/finance/spark?symbols=${encodeURIComponent(syms)}&range=1d&interval=1d`;
        const r = await fetch(upstream, {
          headers: { "User-Agent": "Mozilla/5.0", "Accept": "application/json" },
        });
        if (!r.ok) throw new Error(`upstream ${r.status}`);
        const data = await r.json();
        return json(data);
      } catch (e) {
        return json({ error: String(e) }, 502);
      }
    }

    // ── /og — 卡片分享图（SVG）──
    if (url.pathname === "/og") {
      const date = url.searchParams.get("date") ?? "";
      const sec  = url.searchParams.get("sec")  ?? "";
      const idx  = parseInt(url.searchParams.get("idx") ?? "0");

      // 从 GitHub Pages 拉取 JSON
      const dataUrl = `https://quantum505void.github.io/daily-news-site/data/${date}.json`;
      let item = null, secTitle = "", secColor = "#e74c3c";
      try {
        const r = await fetch(dataUrl, { cf: { cacheTtl: 3600 } });
        if (r.ok) {
          const d = await r.json();
          const section = (d.sections ?? []).find(s => s.id === sec);
          if (section) {
            item = (section.items ?? [])[idx] ?? null;
            secTitle = section.title ?? sec;
            secColor = section.color ?? secColor;
          }
        }
      } catch {}

      const title   = item?.title   ?? "小新日报";
      const body    = item?.body    ?? "每日精选资讯，由 AI 驱动";
      const source  = item?.source  ?? "quantum505void.github.io/daily-news-site";
      const bodyShort = body.length > 80 ? body.slice(0, 78) + "…" : body;

      // 转义 XML 特殊字符
      const esc = s => s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");

      // 多行标题（每30字换行）
      const titleLines = [];
      for (let i = 0; i < title.length; i += 28) titleLines.push(title.slice(i, i + 28));

      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="314" viewBox="0 0 600 314">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1a1a2e"/>
      <stop offset="100%" stop-color="#16213e"/>
    </linearGradient>
  </defs>
  <!-- 背景 -->
  <rect width="600" height="314" fill="url(#bg)" rx="16"/>
  <!-- 顶部色条 -->
  <rect width="600" height="5" fill="${esc(secColor)}" rx="0"/>
  <!-- 板块标签 -->
  <rect x="24" y="24" width="80" height="26" fill="${esc(secColor)}22" rx="6"/>
  <text x="64" y="41" font-family="system-ui,sans-serif" font-size="12" fill="${esc(secColor)}" text-anchor="middle" font-weight="700">${esc(secTitle)}</text>
  <!-- 标题 -->
  ${titleLines.map((l, i) => `<text x="24" y="${76 + i * 34}" font-family="system-ui,sans-serif" font-size="22" fill="#f1f5f9" font-weight="800">${esc(l)}</text>`).join("\n  ")}
  <!-- 摘要 -->
  <text x="24" y="${76 + titleLines.length * 34 + 18}" font-family="system-ui,sans-serif" font-size="13" fill="#94a3b8">${esc(bodyShort)}</text>
  <!-- 底部 -->
  <rect x="0" y="280" width="600" height="34" fill="#0f172a" rx="0"/>
  <rect x="0" y="278" width="600" height="36" fill="#0f172a"/>
  <rect x="0" y="294" width="600" height="20" fill="#0f172a" rx="0"/>
  <text x="24" y="301" font-family="system-ui,sans-serif" font-size="11" fill="#475569">📰 小新日报 · ${esc(date)}</text>
  <text x="576" y="301" font-family="system-ui,sans-serif" font-size="11" fill="#475569" text-anchor="end">quantum505void.github.io/daily-news-site</text>
</svg>`;

      return new Response(svg, {
        headers: {
          "Content-Type": "image/svg+xml",
          "Cache-Control": "public, max-age=86400",
          "Access-Control-Allow-Origin": "*",
        },
      });
    }

    // ── /chat — AI 流式代理 (POST) ──
    if (request.method !== "POST" || url.pathname !== "/chat") {
      return new Response("Not Found", { status: 404 });
    }

    try {
      const body = await request.json();
      const stream = body.stream !== false; // 默认开流式

      const tokenRes = await fetch("https://api.github.com/copilot_internal/v2/token", {
        headers: {
          "Authorization": `token ${env.GHU}`,
          "Accept": "application/json",
          "User-Agent": "GitHubCopilotChat/0.12.0",
          "Editor-Version": "vscode/1.85.0",
          "Editor-Plugin-Version": "copilot-chat/0.12.0",
        },
      });
      if (!tokenRes.ok) {
        const txt = await tokenRes.text();
        return json({ error: `token fetch failed: ${txt.slice(0, 100)}` }, 500);
      }
      const tokenData = await tokenRes.json();
      const token = tokenData.token;
      if (!token) return json({ error: "no token" }, 500);

      const aiRes = await fetch("https://api.githubcopilot.com/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
          "Copilot-Integration-Id": "vscode-chat",
          "Editor-Version": "vscode/1.85.0",
        },
        body: JSON.stringify({
          model: "gpt-5-mini",
          messages: body.messages ?? [],
          max_tokens: body.max_tokens ?? 500,
          temperature: 0.7,
          stream,
        }),
      });

      if (!aiRes.ok) {
        const txt = await aiRes.text();
        return json({ error: `upstream ${aiRes.status}: ${txt.slice(0, 100)}` }, 500);
      }

      if (!stream) {
        const data = await aiRes.json();
        const answer = data.choices?.[0]?.message?.content ?? "未能获取回答";
        return json({ answer });
      }

      // 流式：透传 SSE，追加 CORS 头
      return new Response(aiRes.body, {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          "X-Accel-Buffering": "no",
          ...corsHeaders(),
        },
      });
    } catch (e) {
      return json({ error: String(e) }, 500);
    }
  },
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "https://quantum505void.github.io",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  };
}
