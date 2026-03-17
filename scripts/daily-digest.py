#!/usr/bin/env python3
"""
Daily Digest v2 - 结构化新闻简报
输出：public/data/YYYY-MM-DD.json（无 HTML，无 raw 字段）
"""

import json
import os
import glob
import gzip
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from pypinyin import lazy_pinyin, Style
    def to_pinyin(text: str) -> str:
        """汉字转拼音首字母串+全拼串，用于搜索"""
        full = "".join(lazy_pinyin(text, style=Style.NORMAL))
        initials = "".join(lazy_pinyin(text, style=Style.FIRST_LETTER))
        return f"{full} {initials}"
except ImportError:
    def to_pinyin(text: str) -> str:
        return ""

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
            f"{today} 重大新闻 site:xinhuanet.com OR site:people.com.cn OR site:thepaper.cn OR site:bbc.com OR site:reuters.com OR site:apnews.com OR site:chinadaily.com.cn",
            f"{today} 头条新闻 breaking news site:cnn.com OR site:aljazeera.com OR site:guardian.com OR site:nytimes.com",
        ],
        "color": "#e74c3c",
    },
    {
        "id": "china",
        "title": "国内",
        "icon": "🇨🇳",
        "queries": [
            f"{today} 中国 政策 社会 site:gov.cn OR site:xinhuanet.com OR site:people.com.cn OR site:thepaper.cn OR site:caixin.com OR site:chinadaily.com.cn OR site:globaltimes.cn",
            f"{today} 国内 政策 民生 site:163.com OR site:sohu.com OR site:ifeng.com OR site:bjnews.com.cn OR site:yicai.com",
        ],
        "color": "#c0392b",
    },
    {
        "id": "world",
        "title": "国际",
        "icon": "🌍",
        "queries": [
            f"{today} international news site:reuters.com OR site:apnews.com OR site:bbc.com OR site:ft.com OR site:economist.com OR site:aljazeera.com",
            f"{today} world geopolitics diplomacy site:foreignpolicy.com OR site:cfr.org OR site:politico.com OR site:theguardian.com OR site:nytimes.com",
        ],
        "color": "#2980b9",
    },
    {
        "id": "military",
        "title": "军事与安全",
        "icon": "⚔️",
        "queries": [
            f"{today} military defense site:janes.com OR site:defensenews.com OR site:mod.gov.cn OR site:globaltimes.cn OR site:reuters.com OR site:breakingdefense.com",
            f"{today} 军事 冲突 国防 安全 site:81.cn OR site:thepaper.cn OR site:guancha.cn OR site:huanqiu.com",
        ],
        "color": "#8e44ad",
    },
    {
        "id": "economy",
        "title": "财经与市场",
        "icon": "📈",
        "queries": [
            f"{today} 经济 股市 财经 site:bloomberg.com OR site:wsj.com OR site:caixin.com OR site:yicai.com OR site:cs.com.cn OR site:stcn.com",
            f"{today} 宏观经济 货币政策 site:pbc.gov.cn OR site:ndrc.gov.cn OR site:mof.gov.cn OR site:stats.gov.cn OR site:21jingji.com OR site:jiemian.com",
        ],
        "color": "#27ae60",
    },
    {
        "id": "tech",
        "title": "科技前沿",
        "icon": "🤖",
        "queries": [
            f"{today} AI technology site:techcrunch.com OR site:theverge.com OR site:wired.com OR site:36kr.com OR site:arxiv.org OR site:venturebeat.com OR site:mit.edu",
            f"{today} 人工智能 大模型 芯片 科技 site:ithome.com OR site:leiphone.com OR site:jiqizhixin.com OR site:qbitai.com OR site:aijishu.com",
        ],
        "color": "#16a085",
    },
    {
        "id": "auto",
        "title": "汽车",
        "icon": "🚗",
        "queries": [
            f"{today} 汽车 新能源 电动车 site:autohome.com.cn OR site:pcauto.com.cn OR site:carnewschina.com OR site:d1ev.com OR site:evweekly.com.cn",
            f"{today} 新车 发布 销量 site:che168.com OR site:xchuxing.com OR site:reuters.com OR site:36kr.com OR site:jiemian.com",
        ],
        "color": "#3498db",
    },
    {
        "id": "travel",
        "title": "旅游",
        "icon": "✈️",
        "queries": [
            f"{today} 旅游 出行 签证 site:mafengwo.cn OR site:ctrip.com OR site:tourism.gov.cn OR site:lvmama.com OR site:tuniu.com",
            f"{today} 旅游 目的地 攻略 site:lonelyplanet.com OR site:travelandleisure.com OR site:cnn.com/travel OR site:natgeo.com",
        ],
        "color": "#1abc9c",
    },
    {
        "id": "entertainment",
        "title": "娱乐",
        "icon": "🎭",
        "queries": [
            f"{today} 娱乐 电影 综艺 site:variety.com OR site:ent.sina.com.cn OR site:douban.com OR site:hollywoodreporter.com OR site:deadline.com",
            f"{today} 票房 热播剧 音乐 site:mtime.com OR site:1905.com OR site:163.com/ent OR site:ifeng.com/ent OR site:qq.com/ent",
        ],
        "color": "#d35400",
    },
    {
        "id": "sports",
        "title": "体育",
        "icon": "⚽",
        "queries": [
            f"{today} sports results site:espn.com OR site:bbc.com/sport OR site:goal.com OR site:sports.sina.com.cn OR site:skysports.com",
            f"{today} 足球 篮球 CBA NBA 体育赛事 site:titan007.com OR site:sports.163.com OR site:zhibo8.cc OR site:hupu.com",
        ],
        "color": "#2ecc71",
    },
    {
        "id": "jobs_hot",
        "title": "热门方向",
        "icon": "💼",
        "queries": [
            f"{today} 热门招聘 高薪 site:zhipin.com OR site:liepin.com OR site:lagou.com OR site:linkedin.com OR site:zhaopin.com OR site:maimai.cn",
            f"{today} 就业 薪资 行业趋势 site:36kr.com OR site:huxiu.com OR site:caixin.com OR site:economist.com OR site:jiemian.com",
        ],
        "color": "#f39c12",
    },
    {
        "id": "health",
        "title": "健康生活",
        "icon": "🏥",
        "queries": [
            f"{today} 健康 医疗 疾病 site:healthline.com OR site:webmd.com OR site:dxy.cn OR site:yxj.org.cn OR site:nhc.gov.cn OR site:who.int",
            f"{today} 健康 养生 医学 site:jiankang.com OR site:39.net OR site:120ask.com OR site:medscape.com OR site:nejm.org",
        ],
        "color": "#e91e8c",
    },
    {
        "id": "science",
        "title": "科学探索",
        "icon": "🔬",
        "queries": [
            f"{today} science discovery research site:nature.com OR site:science.org OR site:phys.org OR site:newscientist.com OR site:scientificamerican.com",
            f"{today} 科学 发现 研究 宇宙 site:guokr.com OR site:zhishi.com OR site:cas.cn OR site:nasa.gov OR site:esa.int",
        ],
        "color": "#7b1fa2",
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

# ── RSS 直接抓取（不消耗 Brave 配额，补充实时数据） ───────────────────
RSS_FEEDS = {
    "highlight": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://www.reutersagency.com/feed/?best-topics=top-news&post_type=best",
    ],
    "china": [
        "http://www.xinhuanet.com/rss/news.xml",
        "https://www.thepaper.cn/rss_ori.jsp?id=25950",
    ],
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
    "tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://36kr.com/feed",
    ],
    "economy": [
        "https://www.ft.com/?format=rss",
    ],
    "science": [
        "https://www.nature.com/nature.rss",
        "https://phys.org/rss-feed/",
    ],
    "health": [
        "https://www.who.int/rss-feeds/news-english.xml",
    ],
    "entertainment": [
        "https://variety.com/feed/",
    ],
    "sports": [
        "https://www.espn.com/espn/rss/news",
    ],
}

def fetch_rss(url, max_items=6) -> list:
    """拉取 RSS，解析成统一格式，失败静默跳过"""
    import xml.etree.ElementTree as ET
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; newsbot/1.0)"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = []
        # RSS 2.0
        for item in root.findall(".//item")[:max_items]:
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link") or "").strip()
            desc  = (item.findtext("description") or "").strip()[:200]
            if title and link:
                items.append({"title": title, "url": link, "desc": desc, "thumbnail": ""})
        # Atom
        if not items:
            for entry in root.findall(".//atom:entry", ns)[:max_items]:
                title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
                link_el = entry.find("atom:link", ns)
                link = (link_el.get("href", "") if link_el is not None else "").strip()
                desc = (entry.findtext("atom:summary", namespaces=ns) or "")[:200]
                if title and link:
                    items.append({"title": title, "url": link, "desc": desc, "thumbnail": ""})
        return items
    except Exception as e:
        print(f"  RSS skip {url[:40]}: {e}", flush=True)
        return []

def collect_rss(sec_id: str) -> list:
    feeds = RSS_FEEDS.get(sec_id, [])
    results = []
    seen = set()
    for feed_url in feeds:
        for item in fetch_rss(feed_url):
            u = item["url"]
            if u and u not in seen:
                seen.add(u)
                results.append(item)
    return results


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
                return [{"title": x.get("title",""), "url": x.get("url",""), "desc": x.get("description",""), "thumbnail": (x.get("thumbnail") or {}).get("src","")} for x in results]
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
    """并发搜索所有板块，每板块内部串行查询（避免同时打爆 API 限流）"""
    results = {}
    # 全局 URL 去重集合，防止同一条新闻出现在多个板块
    global_seen_urls: set = set()
    lock = __import__('threading').Lock()

    def fetch_section(s):
        queries = s.get("queries") or [s.get("query", "")]
        local_seen: set = set()
        combined = []

        # 优先拉 RSS（不消耗 Brave 配额）
        for item in collect_rss(s["id"]):
            u = item.get("url", "")
            if not u or u in local_seen:
                continue
            with lock:
                if u in global_seen_urls:
                    continue
                global_seen_urls.add(u)
            local_seen.add(u)
            combined.append(item)

        # Brave Search 补充
        for qi, q in enumerate(queries):
            if qi > 0:
                time.sleep(1)
            items = web_search(q, count=10)
            for item in items:
                u = item.get("url", "")
                if not u or u in local_seen:
                    continue
                with lock:
                    if u in global_seen_urls:
                        continue
                    global_seen_urls.add(u)
                local_seen.add(u)
                combined.append(item)
        return s["id"], s["title"], combined

    # 最多 4 个并发，避免触发 Brave 429
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch_section, s): s for s in SECTIONS}
        for fut in as_completed(futures):
            try:
                sid, title, combined = fut.result()
                results[sid] = combined
                status = f"{len(combined)} 条" if combined else "❌ 无数据（LLM补全）"
                print(f"  {'✓' if combined else '○'} {title}: {status}", flush=True)
            except Exception as e:
                s = futures[fut]
                print(f"  ✗ {s['title']} 搜索异常: {e}", flush=True)
                results[s["id"]] = []

    failed = [s["title"] for s in SECTIONS if not results.get(s["id"])]
    if failed:
        print(f"  ⚠ 无数据板块，LLM补全：{', '.join(failed)}", flush=True)
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

def llm(prompt, max_tokens=8000):
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
        with urllib.request.urlopen(req, timeout=240) as r:
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
        for r in items[:12]:
            lines.append(f"- {r['title']}: {r['desc'][:150]}")
        lines.append("")
    return "\n".join(lines)

def generate_sections(raw_results, override_prompt=None, attempt=0):
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
          "title": "标题（15字以内，有力度，不是新闻标题堆砌，避免套话）",
          "body": "正文（150-280字，必须有自己的分析判断和背景解读，不只是转述；优先引用权威来源具体数据/数字；结尾给出一句前瞻或影响判断；没有搜索数据时用自身知识写）",
          "tag": "从[突发,重磅,分析,趋势,观察,机会,提醒,知识库]选一个",
          "url": "来源url（优先用权威媒体/官方平台链接），没有就空字符串"
        }}
      ]
    }}
  ]
}}

**板块要求（全部必须输出，一个都不能少）：**
- highlight（今日看点）：选今天最重要的 5-8 件事，给一句话判断，语言精练有力
- china（国内）：5-8 条，政策/社会/经济/民生，优先引用 gov.cn/新华社/人民日报，有背景分析，每条都要有具体数据或细节
- world（国际）：5-8 条，重大事件/地区冲突/外交动态，优先引用 Reuters/AP/BBC，写清楚影响链和对中国的潜在影响
- military（军事与安全）：5-8 条，必须有自己的战略判断，不只复述；可涵盖演习、装备、地缘博弈
- economy（财经与市场）：5-8 条，宏观/股市/汇率/大宗商品，优先引用 Bloomberg/WSJ/财新/上交所/深交所数据，有操作层面的观察和风险提示
- tech（科技前沿）：5-8 条，AI/半导体/新能源技术为重点，优先引用 arXiv/TechCrunch/MIT，写清楚技术突破意味着什么
- entertainment（娱乐）：5-8 条，轻松但要有观点，涵盖影视/音乐/网红/综艺，不是流水账
- sports（体育）：5-8 条，重要赛事/中国运动员/赛事赛程，有结果有分析有期待
- auto（汽车）：5-8 条，新能源/传统车/行业竞争，有具体车型/销量/价格数据，优先引用 autohome/pcauto/reuters
- travel（旅游）：5-8 条，热门目的地/签证政策/出行攻略，优先引用 mafengwo/ctrip/官方旅游局，有实用信息
- jobs_hot（热门方向）：5-8 条，不限地区行业，列公司+岗位+薪资范围(如有)+核心亮点，选当下最热门/高薪/有代表性的岗位方向
- health（健康生活）：5-8 条，医学研究/疾病防治/健康政策/生活方式建议，优先引用 WHO/国家卫健委/NEJM/丁香医生，有具体数据和实用建议
- science（科学探索）：5-8 条，最新科研成果/天文发现/生物医学突破，优先引用 Nature/Science/NASA，解释清楚"发现了什么"和"为什么重要"
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

    raw = llm(override_prompt or prompt, max_tokens=8000 if attempt == 0 else 5000)
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

    # 构建双重映射：url→thumbnail 和 title关键词→thumbnail（兜底）
    url_thumb: dict = {}
    title_thumb: list = []  # [(title_lower, thumbnail)]
    for items in raw_results.values():
        for r in items:
            if not r.get("thumbnail"):
                continue
            if r.get("url"):
                url_thumb[r["url"]] = r["thumbnail"]
            if r.get("title"):
                title_thumb.append((r["title"].lower(), r["thumbnail"]))

    def find_thumbnail(item_url: str, item_title: str) -> str:
        # 1. 精确 url 匹配
        if item_url and item_url in url_thumb:
            return url_thumb[item_url]
        # 2. 标题关键词模糊匹配（取前10字）
        if item_title and title_thumb:
            key = item_title[:10].lower()
            for t_title, t_thumb in title_thumb:
                if key and key in t_title:
                    return t_thumb
        return ""

    # 合并板块 meta（icon/color/title）
    section_meta = {s["id"]: s for s in SECTIONS}
    for sec in structured.get("sections", []):
        meta = section_meta.get(sec["id"], {})
        sec["title"] = meta.get("title", sec["id"])
        sec["icon"]  = meta.get("icon", "📌")
        sec["color"] = meta.get("color", "#888")
        for item in sec.get("items", []):
            if item.get("body"):
                item["body"] = item["body"][:450]
            if not item.get("thumbnail"):
                item["thumbnail"] = find_thumbnail(item.get("url",""), item.get("title",""))

    sections = structured.get("sections", [])
    # hot_words 优先用 LLM 生成的（字符串列表），转成 [{word, count}] 格式；降级用正则提取
    llm_words = structured.get("hot_words", [])
    if llm_words and isinstance(llm_words[0], str):
        hot_words = [{"word": w, "count": len(llm_words) - i} for i, w in enumerate(llm_words)]
    else:
        hot_words = extract_hot_words(sections)

    # 构建热词倒排索引：{word -> [card_id, ...]}
    # card_id 格式："{sec_id}:{item_index}"，方便客户端直接定位
    def build_hot_word_index(hot_words, sections):
        index = {}
        for hw in hot_words:
            word = hw["word"]
            # 生成候选匹配串：精确词 + 从词尾往前的 2 字 ngram（与前端降级逻辑一致）
            candidates = [word]
            if len(word) > 2:
                for i in range(len(word) - 2, -1, -1):
                    candidates.append(word[i:i+2])
            matched_ids = []
            for cand in candidates:
                for sec in sections:
                    for idx, item in enumerate(sec.get("items", [])):
                        text = (item.get("title", "") + " " + item.get("body", ""))
                        if cand in text:
                            card_id = f"{sec['id']}:{idx}"
                            if card_id not in matched_ids:
                                matched_ids.append(card_id)
                if matched_ids:
                    break  # 精确匹配到了，不继续降级
            index[word] = matched_ids
        return index

    hot_word_index = build_hot_word_index(hot_words, sections)

    # ── 生成质量评分 ──────────────────────────────────────────────────
    all_items = [item for sec in sections for item in sec.get("items", [])]
    total_items = len(all_items)
    has_url = sum(1 for i in all_items if i.get("url"))
    has_thumb = sum(1 for i in all_items if i.get("thumbnail"))
    avg_body = int(sum(len(i.get("body") or "") for i in all_items) / total_items) if total_items else 0
    quality = {
        "sections": len(sections),
        "total_items": total_items,
        "url_rate": round(has_url / total_items * 100) if total_items else 0,
        "thumb_rate": round(has_thumb / total_items * 100) if total_items else 0,
        "avg_body_len": avg_body,
        "score": min(100, int(
            (len(sections) / 13 * 30) +           # 板块完整度 30分
            (has_url / max(total_items,1) * 30) +  # URL覆盖率 30分
            (min(avg_body, 300) / 300 * 25) +      # 正文丰富度 25分
            (has_thumb / max(total_items,1) * 15)  # 图片覆盖率 15分
        ))
    }

    data = {
        "date":          date_str,
        "weekday":       weekday,
        "title":         f"{today} {weekday}",
        "summary":       structured.get("summary", ""),
        "sections":      sections,
        "hot_words":     hot_words,
        "hot_word_index": hot_word_index,
        "history_today": structured.get("history_today", []),
        "almanac":       structured.get("almanac", {}),
        "daily_question": structured.get("daily_question", {}),
        "quote":          structured.get("quote", {}),
        "key_numbers":    structured.get("key_numbers", []),
        "quality":        quality,
        "generated_at":  NOW.isoformat(),
        "version":       2
    }
    # 文件名英文（URL 友好），不再生成 HTML
    json_path = f"{DATA_DIR}/{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 已保存 → {json_path}")

    # 更新 manifest.json：扫 data 目录重建，避免幽灵日期
    manifest_path = os.path.join(PROJECT_DIR, "public", "manifest.json")
    all_dates = sorted(
        [f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")],
        reverse=True
    )
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

    # 重建全量搜索索引（所有日期）
    search_index = []
    section_meta = {s["id"]: s for s in SECTIONS}
    for date_file in sorted(glob.glob(os.path.join(DATA_DIR, "*.json")), reverse=True):
        try:
            with open(date_file, encoding="utf-8") as f:
                day = json.load(f)
            for sec in day.get("sections", []):
                meta = section_meta.get(sec["id"], {})
                sec_title = meta.get("title", sec.get("title", sec["id"]))
                for item in sec.get("items", []):
                    search_index.append({
                        "date": day["date"],
                        "secId": sec["id"],
                        "secTitle": sec_title,
                        "title": item.get("title", ""),
                        "body": (item.get("body", "") or "")[:120],
                        "tag": item.get("tag", ""),
                        "url": item.get("url", ""),
                        "pinyin": to_pinyin(item.get("title", "")),
                    })
        except Exception as e:
            print(f"  ⚠ 搜索索引跳过 {date_file}: {e}", flush=True)

    search_path = os.path.join(PROJECT_DIR, "public", "search-index.json")
    with open(search_path, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✅ search-index.json 已重建 → {len(search_index)} 条")

    return json_path

# ── 主流程 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[{today} {weekday}] 开始生成每日简报 v2...", flush=True)

    print("📡 并发搜索新闻...", flush=True)
    raw_results = collect_all()

    print("🤖 LLM 生成结构化内容...", flush=True)
    structured = None
    for attempt in range(2):
        if attempt == 1:
            print("  第1次失败，降低要求重试...", flush=True)
        structured = generate_sections(raw_results, attempt=attempt)
        if structured:
            break

    if not structured:
        print("⚠️  LLM 失败，使用 fallback", flush=True)
        structured = fallback_sections(raw_results)

    print("💾 保存文件...", flush=True)
    save(structured, raw_results)

    print("✅ 日报生成完成")
