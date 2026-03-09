#!/usr/bin/env python3
"""
Daily Digest v2 - 结构化新闻简报
输出：public/data/YYYY-MM-DD.json（无 HTML，无 raw 字段，body 截断 300 字）
"""

import json
import os
import gzip
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# ── 配置 ──────────────────────────────────────────────────────────────
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
today = NOW.strftime("%Y年%m月%d日")
date_str = NOW.strftime("%Y-%m-%d")
weekday = ["周一","周二","周三","周四","周五","周六","周日"][NOW.weekday()]
PROJECT_DIR = os.environ.get("PROJECT_DIR", os.path.join(os.path.expanduser("~"), "Projects", "daily-news-site"))
DATA_DIR = os.path.join(PROJECT_DIR, "public", "data")

SECTIONS = [
    {
        "id": "highlight",
        "title": "今日看点",
        "icon": "⚡",
        "queries": [
            f"{today} 重大新闻 site:xinhuanet.com OR site:people.com.cn OR site:thepaper.cn OR site:bbc.com OR site:reuters.com",
            f"{today} 头条新闻 breaking news",
            f"{today} 热搜 trending site:weibo.com OR site:x.com OR site:twitter.com",
        ],
        "color": "#e74c3c",
    },
    {
        "id": "china",
        "title": "国内",
        "icon": "🇨🇳",
        "queries": [
            f"{today} 中国 政策 社会 site:gov.cn OR site:xinhuanet.com OR site:people.com.cn OR site:thepaper.cn OR site:caixin.com",
            f"{today} 两会 政策 国内新闻",
            f"{today} site:weibo.com OR site:zhihu.com 国内 热点",
        ],
        "color": "#c0392b",
    },
    {
        "id": "world",
        "title": "国际",
        "icon": "🌍",
        "queries": [
            f"{today} international news site:reuters.com OR site:apnews.com OR site:bbc.com OR site:ft.com OR site:economist.com",
            f"{today} world news geopolitics",
            f"{today} site:x.com OR site:twitter.com world news trending",
        ],
        "color": "#2980b9",
    },
    {
        "id": "military",
        "title": "军事与安全",
        "icon": "⚔️",
        "queries": [
            f"{today} military defense geopolitics site:janes.com OR site:defensenews.com OR site:mod.gov.cn OR site:globaltimes.cn OR site:reuters.com",
            f"{today} 军事 冲突 国防 安全",
            f"{today} military site:x.com OR site:twitter.com OR site:youtube.com",
        ],
        "color": "#8e44ad",
    },
    {
        "id": "economy",
        "title": "财经与市场",
        "icon": "📈",
        "queries": [
            f"{today} 经济 股市 财经 site:bloomberg.com OR site:wsj.com OR site:caixin.com OR site:cs.com.cn OR site:sse.com.cn OR site:szse.cn",
            f"{today} A股 人民币 经济数据 PMI",
            f"{today} 财经 股市 site:weibo.com OR site:zhihu.com OR site:x.com",
        ],
        "color": "#27ae60",
    },
    {
        "id": "tech",
        "title": "科技前沿",
        "icon": "🤖",
        "queries": [
            f"{today} AI technology site:techcrunch.com OR site:theverge.com OR site:wired.com OR site:36kr.com OR site:mit.edu OR site:arxiv.org",
            f"{today} 人工智能 大模型 科技新闻",
            f"{today} AI tech site:x.com OR site:twitter.com OR site:youtube.com OR site:bilibili.com OR site:zhihu.com",
        ],
        "color": "#16a085",
    },
    {
        "id": "auto",
        "title": "汽车",
        "icon": "🚗",
        "queries": [
            f"{today} 汽车 新能源 电动车 site:autohome.com.cn OR site:pcauto.com.cn OR site:reuters.com OR site:36kr.com OR site:carnewschina.com",
            f"{today} 特斯拉 比亚迪 新车发布",
            f"{today} 汽车 site:weibo.com OR site:bilibili.com OR site:youtube.com",
        ],
        "color": "#3498db",
    },
    {
        "id": "travel",
        "title": "旅游",
        "icon": "✈️",
        "queries": [
            f"{today} 旅游 出行 景点 site:mafengwo.cn OR site:ctrip.com OR site:lonelyplanet.com OR site:travelandleisure.com OR site:tourism.gov.cn",
            f"{today} 旅游 签证 出境 目的地推荐",
            f"{today} 旅游 打卡 site:douyin.com OR site:xiaohongshu.com OR site:weibo.com OR site:youtube.com",
        ],
        "color": "#1abc9c",
    },
    {
        "id": "entertainment",
        "title": "娱乐",
        "icon": "🎭",
        "queries": [
            f"{today} 娱乐 电影 综艺 site:variety.com OR site:ent.sina.com.cn OR site:mtime.com OR site:douban.com OR site:hollywoodreporter.com",
            f"{today} 票房 热播剧 明星 娱乐新闻",
            f"{today} 娱乐 综艺 site:weibo.com OR site:douyin.com OR site:bilibili.com OR site:youtube.com",
        ],
        "color": "#d35400",
    },
    {
        "id": "sports",
        "title": "体育",
        "icon": "⚽",
        "queries": [
            f"{today} sports results site:espn.com OR site:bbc.com/sport OR site:goal.com OR site:sports.sina.com.cn",
            f"{today} 足球 篮球 CBA NBA 体育赛事",
            f"{today} sports highlights site:youtube.com OR site:x.com OR site:twitter.com OR site:weibo.com",
        ],
        "color": "#2ecc71",
    },
    {
        "id": "jobs_hot",
        "title": "热门方向",
        "icon": "💼",
        "queries": [
            f"{today} 热门招聘 高薪 site:zhipin.com OR site:liepin.com OR site:lagou.com OR site:linkedin.com OR site:zhaopin.com",
            f"{today} 求职 薪资 就业市场 AI 热门岗位",
            f"{today} 求职 职场 site:zhihu.com OR site:weibo.com OR site:x.com OR site:linkedin.com",
        ],
        "color": "#f39c12",
    },
]

# ── Brave Search ─────────────────────────────────────────────────────
def load_api_key():
    env_key = os.environ.get("BRAVE_API_KEY", "")
    if env_key: return env_key
    try:
        cfg_path = os.path.expanduser("~/.openclaw/openclaw.json")
        with open(cfg_path) as f:
            cfg = json.load(f)
        return cfg.get("tools", {}).get("web", {}).get("search", {}).get("apiKey", "")
    except Exception:
        return ""

API_KEY = load_api_key()

def web_search(query, count=8, retries=2) -> list:
    """搜索，失败自动重试，429 等待后重试"""
    if not API_KEY:
        return []
    encoded = urllib.parse.quote(query)
    url = f"https://api.search.brave.com/res/v1/web/search?q={encoded}&count={count}&country=CN"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": API_KEY
    })
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                data = json.loads(raw)
                results = data.get("web", {}).get("results", [])
                return [{"title": x.get("title",""), "url": x.get("url",""), "desc": x.get("description","")} for x in results]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 8 * (attempt + 1)
                print(f"  429 限流，等待 {wait}s 后重试...", flush=True)
                time.sleep(wait)
            else:
                print(f"  search HTTP {e.code} [{query[:25]}]", flush=True)
                return []
        except Exception as e:
            print(f"  search error [{query[:25]}]: {e}", flush=True)
            return []
    return []

def collect_all() -> dict:
    """每板块执行多条查询并去重合并，间隔 2s，失败的板块标记为空让 LLM 补全"""
    results = {}
    failed = []
    for i, s in enumerate(SECTIONS):
        if i > 0:
            time.sleep(2)
        queries = s.get("queries") or [s.get("query", "")]
        seen_urls: set = set()
        combined = []
        for qi, q in enumerate(queries):
            if qi > 0:
                time.sleep(1.5)
            items = web_search(q, count=10)
            for item in items:
                u = item.get("url", "")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    combined.append(item)
        results[s["id"]] = combined
        status = f"{len(combined)} 条" if combined else "❌ 搜索失败（LLM补全）"
        print(f"  {'✓' if combined else '○'} {s['title']}: {status}", flush=True)
        if not combined:
            failed.append(s["title"])
    if failed:
        print(f"  ⚠ 以下板块无搜索结果，将由 LLM 用自身知识补全：{', '.join(failed)}", flush=True)
    return results

# ── GitHub Copilot LLM ───────────────────────────────────────────────
GHU = os.environ.get("GHU_TOKEN", "")

def get_copilot_token():
    req = urllib.request.Request(
        "https://api.github.com/copilot_internal/v2/token",
        headers={
            "Authorization": f"token {GHU}",
            "Accept": "application/json",
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "copilot-chat/0.12.0"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read()).get("token", "")

def llm(prompt, max_tokens=3000):
    try:
        token = get_copilot_token()
        payload = json.dumps({
            "model": "gpt-5.2",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }).encode()
        req = urllib.request.Request(
            "https://api.githubcopilot.com/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "Copilot-Integration-Id": "vscode-chat",
                "Editor-Version": "vscode/1.85.0",
            }
        )
        with urllib.request.urlopen(req, timeout=150) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  LLM error: {e}", flush=True)
        return None

# ── 热词提取（服务端，比前端 JS 准确） ──────────────────────────────
STOP_WORDS = {
    "中国","美国","日本","欧洲","全球","市场","公司","企业","发展","相关",
    "表示","表明","目前","方面","进行","工作","推出","实现","提出","提供",
    "建设","加强","支持","合作","增长","增加","下降","同比","环比","以上",
    "以下","今年","去年","国内","国际","政府","部门","官员","记者","报道",
    "消息","据悉","此前","已经","可以","需要","没有","这个","那么","什么",
    "如何","为何","亿元","万元","百分","一个","一种","一项","多个","多项",
    "新闻","内容","情况","问题","时间","地方","人员","事件","数据","结果",
    "通过","计划","进行","提升","带来","影响","重要","主要","目标","系列",
}

def extract_hot_words(sections, top_n=20):
    import re
    freq: dict = {}
    for sec in sections:
        for item in sec.get("items", []):
            # 只从标题提取，body 是 LLM 分析文本，词汇质量差
            text = item.get("title") or ""
            for w in re.findall(r'[\u4e00-\u9fa5]{2,6}', text):
                if w in STOP_WORDS:
                    continue
                if re.fullmatch(r'[一二三四五六七八九十百千万亿第两]+', w):
                    continue
                freq[w] = freq.get(w, 0) + 1
    # 频次>=2 才收录
    sorted_words = sorted(
        [(w, c) for w, c in freq.items() if c >= 2],
        key=lambda x: -x[1]
    )[:top_n]
    return [{"word": w, "count": c} for w, c in sorted_words]

# ── 生成结构化 sections ───────────────────────────────────────────────
def build_raw_text(raw_results):
    lines = []
    for s in SECTIONS:
        items = raw_results.get(s["id"], [])
        if not items:
            continue
        lines.append(f"=== {s['title']} ===")
        for r in items[:8]:
            lines.append(f"- {r['title']}: {r['desc'][:150]}")
        lines.append("")
    return "\n".join(lines)

def generate_sections(raw_results):
    # 统计哪些板块有搜索数据
    has_data = {sid: bool(items) for sid, items in raw_results.items()}
    empty_sections = [s["title"] for s in SECTIONS if not has_data.get(s["id"])]

    raw_text = build_raw_text(raw_results)

    note = ""
    if empty_sections:
        note = f"""
**注意：以下板块没有搜索数据，请完全依靠你自己的知识（截止训练日期）生成内容，标注 tag 为"知识库"：**
{', '.join(empty_sections)}
即使没有实时数据，这些板块也必须出现在输出中，不能省略，至少生成 2-3 条有价值的内容。
"""

    prompt = f"""你是一个专业、有深度的新闻编辑。今天是 {today} {weekday}。

以下搜索数据来自权威信源（新华社、人民日报、澎湃新闻、财新、Reuters、BBC、Bloomberg、FT、TechCrunch、arXiv 等）以及社交平台（微博、知乎、B站、抖音、X/Twitter、YouTube、LinkedIn 等）的公开内容。
社交平台数据可反映公众情绪和热点讨论，请酌情引用，但优先以权威媒体为主，社交平台作为补充视角。
{note}
**输出格式：严格 JSON，结构如下：**
{{
  "summary": "2-3句话的全局总结，点出今日最值得关注的1-2件事，语言有力度",
  "hot_words": ["热词1", "热词2", "热词3", ...],
  "sections": [
    {{
      "id": "板块id",
      "items": [
        {{
          "title": "标题（15字以内，有力度，不是新闻标题堆砌）",
          "body": "正文（120-220字，有分析判断，不只是转述；优先引用权威来源数据；没有搜索数据时用自身知识写）",
          "tag": "从[突发,重磅,分析,趋势,观察,机会,提醒,知识库]选一个",
          "url": "来源url（优先用权威媒体/官方平台链接），没有就空字符串"
        }}
      ]
    }}
  ]
}}

**板块要求（全部必须输出，一个都不能少）：**
- highlight（今日看点）：选今天最重要的 2-3 件事，给一句话判断
- china（国内）：3-4 条，政策/社会/经济，优先引用 gov.cn/新华社/人民日报，有背景分析
- world（国际）：3-4 条，重大事件，优先引用 Reuters/AP/BBC，写清楚影响链
- military（军事与安全）：3 条，必须有自己的判断，不只复述
- economy（财经与市场）：3-4 条，优先引用 Bloomberg/WSJ/财新/上交所/深交所数据，有操作层面的观察
- tech（科技前沿）：3-4 条，AI重点，优先引用 arXiv/TechCrunch/MIT，写清楚为什么重要
- entertainment（娱乐）：2-3 条，轻松但要有观点，不是流水账
- sports（体育）：2-3 条，重要赛事/中国运动员，有结果有分析
- auto（汽车）：3-4 条，新能源/传统车/行业动态，有数据有观点，优先引用 autohome/pcauto/reuters
- travel（旅游）：3-4 条，热门目的地/出行政策/旅游新闻，优先引用 mafengwo/ctrip/官方旅游局
- jobs_hot（热门方向）：3-5 条，不限地区行业，列公司+岗位+薪资(如有)+亮点，选当下最热门/高薪/有代表性的
- hot_words：从今日所有新闻标题中提取 15-20 个最能代表今日新闻热点的关键词（2-5字，真实词语，如"两会"、"美伊冲突"、"新能源"），按热度排序，不要动词短语

另外，在 JSON 根节点额外输出：
- "history_today": 历史上的今天（{today}）发生过的 3-5 件大事，每条包含 year(年份字符串) + event(一句话描述，30字内)
- "almanac": 中国传统黄历，包含：lunar_date(农历日期如"正月初七")、yi(宜，3-4项，数组)、ji(忌，2-3项，数组)、lucky_color(今日幸运色)、fortune(一句简短运势寄语，20字内)
- "daily_question": 今日一问，包含：question(一个有争议、值得思考的问题，20字内，不要是非题，不要答案显而易见的问题)、options(2-4个选项，每项15字内，数组)
- "quote": 今日名言，包含：text(名言原文，中英文均可，50字内)、author(作者姓名)、zh(若原文是英文则提供中文译文，否则留空字符串)
- "key_numbers": 今日关键数字，从新闻中提取 4-5 个最值得关注的具体数字/数据，每条包含：number(数字本身，如"7.3%""120亿""25bp")、label(简短说明，10字内)、context(所属新闻背景，15字内)、trend("up"/"down"/"neutral")

原始数据：
{raw_text}

输出完整 JSON（所有板块都必须有）："""

    raw = llm(prompt, max_tokens=4000)
    if not raw:
        return None

    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        result = json.loads(raw)
        # 验证所有板块都在
        section_ids = {s["id"] for s in result.get("sections", [])}
        required = {s["id"] for s in SECTIONS}
        missing = required - section_ids
        if missing:
            print(f"  ⚠ LLM 漏掉板块：{missing}，重试一次...", flush=True)
            return None
        # 强制按 SECTIONS 定义的顺序重排，不依赖 LLM 输出顺序
        sec_map = {s["id"]: s for s in result.get("sections", [])}
        result["sections"] = [sec_map[s["id"]] for s in SECTIONS if s["id"] in sec_map]
        return result
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}", flush=True)
        print(f"  raw[:300]: {raw[:300]}", flush=True)
        return None

# ── Fallback：直接格式化 ──────────────────────────────────────────────
def fallback_sections(raw_results):
    print("  LLM 不可用，使用原始格式", flush=True)
    sections = []
    for s in SECTIONS:
        items = raw_results.get(s["id"], [])
        if not items:
            continue
        sections.append({
            "id": s["id"],
            "items": [
                {
                    "title": r["title"][:40],
                    "body": r["desc"][:200],
                    "tag": "",
                    "url": r.get("url", "")
                }
                for r in items[:5]
            ]
        })
    return {"summary": f"{today} {weekday} 每日简报", "sections": sections}

# ── 保存 ─────────────────────────────────────────────────────────────
def save(structured, raw_results):
    os.makedirs(DATA_DIR, exist_ok=True)

    # 合并板块 meta（icon/color/title）
    section_meta = {s["id"]: s for s in SECTIONS}
    for sec in structured.get("sections", []):
        meta = section_meta.get(sec["id"], {})
        sec["title"] = meta.get("title", sec["id"])
        sec["icon"]  = meta.get("icon", "📌")
        sec["color"] = meta.get("color", "#888")
        # body 截断，控制 JSON 体积
        for item in sec.get("items", []):
            if item.get("body"):
                item["body"] = item["body"][:300]

    sections = structured.get("sections", [])
    # hot_words 优先用 LLM 生成的（字符串列表），转成 [{word, count}] 格式；降级用正则提取
    llm_words = structured.get("hot_words", [])
    if llm_words and isinstance(llm_words[0], str):
        hot_words = [{"word": w, "count": len(llm_words) - i} for i, w in enumerate(llm_words)]
    else:
        hot_words = extract_hot_words(sections)
    data = {
        "date":          date_str,
        "weekday":       weekday,
        "title":         f"{today} {weekday}",
        "summary":       structured.get("summary", ""),
        "sections":      sections,
        "hot_words":     hot_words,
        "history_today": structured.get("history_today", []),
        "almanac":       structured.get("almanac", {}),
        "daily_question": structured.get("daily_question", {}),
        "quote":          structured.get("quote", {}),
        "key_numbers":    structured.get("key_numbers", []),
        "generated_at":  NOW.isoformat(),
        "version":       2
    }
    # 文件名英文（URL 友好），不再生成 HTML
    json_path = f"{DATA_DIR}/{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 已保存 → {json_path}")

    # 更新 manifest.json（前端靠它发现可用日期列表）
    manifest_path = os.path.join(PROJECT_DIR, "public", "manifest.json")
    existing_dates = []
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            try:
                existing_dates = json.load(f).get("dates", [])
            except Exception:
                existing_dates = []
    # 合并当前日期，去重排序（最新在前）
    all_dates = sorted(set(existing_dates + [date_str]), reverse=True)
    manifest = {"dates": all_dates, "updated": datetime.utcnow().isoformat() + "Z"}
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"✅ manifest.json 已更新 → {all_dates[:5]}...")

    # 更新 README.md 状态表
    readme_path = os.path.join(PROJECT_DIR, "README.md")
    if os.path.exists(readme_path):
        import re
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()
        cst_time = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M (CST)")
        readme = re.sub(r"(\| 最新一期 \| ).*", f"\\g<1>{date_str} |", readme)
        readme = re.sub(r"(\| 累计期数 \| ).*", f"\\g<1>{len(all_dates)} 期 |", readme)
        readme = re.sub(r"(\| 最后构建 \| ).*", f"\\g<1>{cst_time} |", readme)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme)
        print(f"✅ README.md 已更新")

    return json_path

# ── 主流程 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[{today} {weekday}] 开始生成每日简报 v2...", flush=True)

    print("📡 并发搜索新闻...", flush=True)
    raw_results = collect_all()

    print("🤖 LLM 生成结构化内容...", flush=True)
    structured = None
    for attempt in range(2):
        structured = generate_sections(raw_results)
        if structured:
            break
        print(f"  第{attempt+1}次失败，重试...", flush=True)

    if not structured:
        print("⚠️  LLM 失败，使用 fallback", flush=True)
        structured = fallback_sections(raw_results)

    print("💾 保存文件...", flush=True)
    save(structured, raw_results)

    print("✅ 日报生成完成")
