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
