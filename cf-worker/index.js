export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    if (request.method !== "POST" || new URL(request.url).pathname !== "/chat") {
      return new Response("Not Found", { status: 404 });
    }

    try {
      const body = await request.json();

      // 1. 获取 Copilot token
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
        return new Response(JSON.stringify({ error: `token fetch failed: ${txt.slice(0,100)}` }), { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders() } });
      }
      const tokenData = await tokenRes.json();
      const token = tokenData.token;
      if (!token) {
        return new Response(JSON.stringify({ error: "no token in response", data: JSON.stringify(tokenData).slice(0,200) }), { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders() } });
      }

      // 2. 调 gpt-5-mini
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

      return new Response(
        JSON.stringify({ answer }, { ensure_ascii: false }),
        { headers: { "Content-Type": "application/json", ...corsHeaders() } }
      );
    } catch (e) {
      return new Response(
        JSON.stringify({ error: String(e) }),
        { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders() } }
      );
    }
  },
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "https://quantum505void.github.io",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  };
}
