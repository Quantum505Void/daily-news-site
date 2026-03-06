export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    const url = new URL(request.url);

    // ── /quote — 行情代理 (GET) ──
    if (url.pathname === "/quote") {
      const syms = url.searchParams.get("symbols") ?? "";
      if (!syms) return json({ error: "missing symbols" }, 400);
      try {
        const upstream = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(syms)}&fields=regularMarketPrice,regularMarketChange,regularMarketChangePercent,shortName`;
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

    // ── /chat — AI 代理 (POST) ──
    if (request.method !== "POST" || url.pathname !== "/chat") {
      return new Response("Not Found", { status: 404 });
    }

    try {
      const body = await request.json();

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
        return json({ error: `token fetch failed: ${txt.slice(0,100)}` }, 500);
      }
      const tokenData = await tokenRes.json();
      const token = tokenData.token;
      if (!token) return json({ error: "no token", data: JSON.stringify(tokenData).slice(0,200) }, 500);

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
        }),
      });

      const data = await aiRes.json();
      const answer = data.choices?.[0]?.message?.content ?? "未能获取回答";
      return json({ answer });
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
