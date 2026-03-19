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
        "https://www.thepaper.cn/rss_ori.jsp?id=25950",        # 澎湃新闻
        "https://rsshub.app/zaobao/znews/china",               # 联合早报中国
    ],
    "china": [
        "http://www.xinhuanet.com/rss/news.xml",
        "https://www.thepaper.cn/rss_ori.jsp?id=25950",
        "https://www.caixin.com/rss/home.xml",                 # 财新
        "https://rsshub.app/gov/zhengce",                      # 国务院政策
    ],
    "world": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.bbci.co.uk/news/world/asia/rss.xml",   # BBC亚洲
        "https://www.aljazeera.com/xml/rss/all.xml",           # 半岛电视台
    ],
    "military": [
        "https://www.defensenews.com/arc/outboundfeeds/rss/",
        "https://feeds.feedburner.com/janes/news",             # Jane's
        "https://www.mil.cn/rss/index.xml",                    # 中国军网
    ],
    "tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://36kr.com/feed",
        "https://sspai.com/feed",                              # 少数派
        "https://rsshub.app/huxiu/article",                    # 虎嗅
        "https://www.wired.com/feed/rss",
    ],
    "economy": [
        "https://www.ft.com/?format=rss",
        "https://feeds.bloomberg.com/markets/news.rss",        # Bloomberg Markets
        "https://caifuhao.eastmoney.com/rss.xml",              # 东方财富
        "https://rsshub.app/cls/depth",                        # 财联社深度
    ],
    "science": [
        "https://www.nature.com/nature.rss",
        "https://phys.org/rss-feed/",
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://feeds.feedburner.com/nasa/breaking-news",     # NASA
    ],
    "health": [
        "https://www.who.int/rss-feeds/news-english.xml",
        "https://rsshub.app/dxy/headline",                     # 丁香园
        "https://www.sciencedaily.com/rss/top/health.xml",
    ],
    "entertainment": [
        "https://variety.com/feed/",
        "https://deadline.com/feed/",
        "https://rsshub.app/douban/movie/playing",             # 豆瓣正在热映
    ],
    "sports": [
        "https://www.espn.com/espn/rss/news",
        "https://rsshub.app/zhibo8/news",                      # 直播吧
    ],
    "auto": [
        "https://rsshub.app/autohome/news",                    # 汽车之家
        "https://rsshub.app/cls/auto",                         # 财联社汽车
        "https://electrek.co/feed/",                           # 电动车
    ],
    "travel": [
        "https://rsshub.app/mafengwo/note/destination/10065", # 马蜂窝热门
    ],
    "jobs_hot": [
        "https://rsshub.app/zhihu/hot",                        # 知乎热榜（就业话题）
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


def web_search(query: str, count: int = 10, retries: int = 2) -> list:
    """搜索，加 freshness=day 只取24h内结果，失败自动重试，429 等待后重试"""
    if not API_KEY:
        return []
    encoded = urllib.parse.quote(query)
    url = f"https://api.search.brave.com/res/v1/web/search?q={encoded}&count={count}&country=CN&freshness=pd"
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

def title_key(title: str) -> str:
    """取标题前20字做相似度key，用于去重"""
    return title.strip()[:20].lower()

def collect_all() -> dict:
    """并发搜索所有板块（highlight 除外），每板块内部串行查询"""
    results = {}
    global_seen_urls: set = set()
    global_seen_titles: set = set()  # 标题去重（前20字）
    lock = __import__('threading').Lock()

    def fetch_section(s):
        if s["id"] == "highlight":
            return s["id"], s["title"], []  # highlight 后面从其他板块聚合
        queries = s.get("queries") or [s.get("query", "")]
        local_seen_urls: set = set()
        local_seen_titles: set = set()
        combined = []

        # 优先拉 RSS
        for item in collect_rss(s["id"]):
            u = item.get("url", "")
            tk = title_key(item.get("title", ""))
            if not u or u in local_seen_urls or tk in local_seen_titles:
                continue
            with lock:
                if u in global_seen_urls or tk in global_seen_titles:
                    continue
                global_seen_urls.add(u)
                global_seen_titles.add(tk)
            local_seen_urls.add(u)
            local_seen_titles.add(tk)
            combined.append(item)

        # Brave Search 补充
        for qi, q in enumerate(queries):
            if qi > 0:
                time.sleep(1)
            for item in web_search(q, count=10):
                u = item.get("url", "")
                tk = title_key(item.get("title", ""))
                if not u or u in local_seen_urls or tk in local_seen_titles:
                    continue
                with lock:
                    if u in global_seen_urls or tk in global_seen_titles:
                        continue
                    global_seen_urls.add(u)
                    global_seen_titles.add(tk)
                local_seen_urls.add(u)
                local_seen_titles.add(tk)
                combined.append(item)
        return s["id"], s["title"], combined

    # 并发抓取（highlight 跳过）
    non_highlight = [s for s in SECTIONS if s["id"] != "highlight"]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch_section, s): s for s in non_highlight}
        for fut in as_completed(futures):
            try:
                sid, title, combined = fut.result()
                results[sid] = combined
                status = f"{len(combined)} 条" if combined else "❌ 无数据"
                print(f"  {'✓' if combined else '○'} {title}: {status}", flush=True)
            except Exception as e:
                s = futures[fut]
                print(f"  ✗ {s['title']} 搜索异常: {e}", flush=True)
                results[s["id"]] = []

    # highlight：从所有其他板块各取前2条，组成今日看点候选池
    highlight_pool = []
    seen_h_urls: set = set()
    for s in SECTIONS:
        if s["id"] == "highlight":
            continue
        for item in results.get(s["id"], [])[:2]:
            u = item.get("url", "")
            if u and u not in seen_h_urls:
                seen_h_urls.add(u)
                highlight_pool.append(item)
    results["highlight"] = highlight_pool
    print(f"  ✓ 今日看点（聚合）: {len(highlight_pool)} 条候选", flush=True)

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
    """
    新架构：原始新闻条目直接保留（title/url/thumbnail/desc），
    LLM 只负责：全局 summary、热词、每板块 overview（2句话），
    以及 history_today/almanac/daily_question/quote/key_numbers。
    """
    # 构建带序号的原始条目供 LLM 引用
    indexed_items: dict = {}  # sec_id -> [(idx, item)]
    for s in SECTIONS:
        indexed_items[s["id"]] = list(enumerate(raw_results.get(s["id"], [])[:8]))

    def build_indexed_text():
        lines = []
        for s in SECTIONS:
            items = indexed_items.get(s["id"], [])
            if not items:
                continue
            lines.append(f"=== {s['title']} ===")
            for idx, r in items:
                lines.append(f"[{s['id']}:{idx}] {r.get('title','')} | {r.get('desc','')[:120]}")
            lines.append("")
        return "\n".join(lines)

    raw_text = build_indexed_text()

    prompt = f"""你是专业新闻编辑。今天是 {today} {weekday}。
以下原始新闻用 [板块id:序号] 标注，请据此生成辅助内容。

**输出格式：严格 JSON，不要包含 markdown 代码块：**
{{
  "summary": "2-3句话全局总结，点出今日最值得关注的1-2件事，语言有力度",
  "hot_words": ["热词1", "热词2", ...],
  "overviews": {{
    "highlight": "今日看点板块的2句话编辑导读",
    "china": "国内板块的2句话编辑导读",
    "world": "国际板块的2句话编辑导读",
    "military": "军事板块的2句话编辑导读",
    "economy": "财经板块的2句话编辑导读",
    "tech": "科技板块的2句话编辑导读",
    "entertainment": "娱乐板块的2句话编辑导读",
    "sports": "体育板块的2句话编辑导读",
    "auto": "汽车板块的2句话编辑导读",
    "travel": "旅游板块的2句话编辑导读",
    "jobs_hot": "招聘板块的2句话编辑导读",
    "health": "健康板块的2句话编辑导读",
    "science": "科学板块的2句话编辑导读"
  }},
  "ranked": {{
    "highlight": ["highlight:0","highlight:2",...],
    "china": ["china:1","china:0",...],
    "world": [...],
    "military": [...],
    "economy": [...],
    "tech": [...],
    "entertainment": [...],
    "sports": [...],
    "auto": [...],
    "travel": [...],
    "jobs_hot": [...],
    "health": [...],
    "science": [...]
  }},
  "insights": {{
    "highlight:0": "30-50字洞察：这条新闻为什么值得关注",
    "china:1": "30-50字洞察",
    ...
  }},
  "history_today": [{{"year": "年份", "event": "30字内描述"}}],
  "almanac": {{"lunar_date": "农历日期", "yi": ["宜1","宜2","宜3"], "ji": ["忌1","忌2"], "lucky_color": "幸运色", "fortune": "20字运势寄语"}},
  "daily_question": {{"question": "有争议的问题20字内", "options": ["选项1","选项2","选项3"]}},
  "quote": {{"text": "名言原文", "author": "作者", "zh": "英文名言的中译，原文是中文则留空"}},
  "key_numbers": [{{"number": "数字", "label": "10字说明", "context": "15字背景", "trend": "up/down/neutral"}}]
}}

ranked：每个板块按重要性对原始条目重新排序，用 [板块id:序号] 引用，最重要的放最前。
insights：只需为每个板块前5条写洞察，key 格式为 "板块id:序号"，value 是30-50字中文洞察。
hot_words：从新闻标题提取15-20个关键词（2-5字），按热度排序。
history_today：历史上的今天（{today}）3-5件大事。
key_numbers：从新闻中提取4-5个最值得关注的数字。

原始数据：
{raw_text}

输出 JSON："""

    raw = llm(override_prompt or prompt, max_tokens=4000 if attempt == 0 else 2500)
    if not raw:
        return None

    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        result = json.loads(raw)

        overviews = result.get("overviews", {})
        insights  = result.get("insights", {})
        ranked    = result.get("ranked", {})

        sections = []
        for s in SECTIONS:
            items_raw = raw_results.get(s["id"], [])[:8]
            # 按 ranked 排序
            ranked_keys = ranked.get(s["id"], [])
            if ranked_keys:
                idx_order = []
                for k in ranked_keys:
                    try: idx_order.append(int(k.split(":")[1]))
                    except: pass
                # 补上未排到的
                all_idx = list(range(len(items_raw)))
                idx_order += [i for i in all_idx if i not in idx_order]
                items_raw_sorted = [items_raw[i] for i in idx_order if i < len(items_raw)]
            else:
                items_raw_sorted = items_raw

            items = []
            for orig_idx, r in enumerate(items_raw_sorted):
                # 找原始序号（用于 insights key）
                orig_key = f"{s['id']}:{items_raw.index(r) if r in items_raw else orig_idx}"
                insight = insights.get(orig_key, "")
                items.append({
                    "title": r.get("title", "")[:80],
                    "body": r.get("desc", "")[:300],
                    "insight": insight,
                    "tag": "",
                    "url": r.get("url", ""),
                    "thumbnail": r.get("thumbnail", ""),
                })
            sections.append({
                "id": s["id"],
                "overview": overviews.get(s["id"], ""),
                "items": items,
            })

        result["sections"] = sections
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
        sections.append({
            "id": s["id"],
            "overview": "",
            "items": [
                {
                    "title": r.get("title", "")[:80],
                    "body": r.get("desc", "")[:300],
                    "tag": "",
                    "url": r.get("url", ""),
                    "thumbnail": r.get("thumbnail", ""),
                }
                for r in items[:8]
            ]
        })
    return {"summary": f"{today} {weekday} 每日简报", "sections": sections}

# ── 保存 ─────────────────────────────────────────────────────────────
def save(structured, raw_results):
    os.makedirs(DATA_DIR, exist_ok=True)

    # thumbnail 已在 items 里，无需额外映射
    _ = raw_results  # 保留参数签名兼容性
    # 合并板块 meta（icon/color/title）
    section_meta = {s["id"]: s for s in SECTIONS}
    for sec in structured.get("sections", []):
        meta = section_meta.get(sec["id"], {})
        sec["title"] = meta.get("title", sec["id"])
        sec["icon"]  = meta.get("icon", "📌")
        sec["color"] = meta.get("color", "#888")

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
    quality = {
        "sections": len(sections),
        "total_items": total_items,
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
