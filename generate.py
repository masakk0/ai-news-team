#!/usr/bin/env python3
"""Radar AI Big Tech: legge i feed RSS/Atom e genera index.html (solo libreria standard)."""
import html, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

GN = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="
# Modifica qui feed e parole chiave. Ogni azienda può avere più feed.
COMPANIES = {
    "Microsoft": {"color": "#2f6fdb", "dark": "#6c9bf5", "feeds": [
        GN + "Microsoft+AI+OR+Copilot+OR+Windows+OR+Azure+when:7d",
        "https://blogs.microsoft.com/feed/"]},
    "Anthropic": {"color": "#c0592b", "dark": "#e08a5f", "feeds": [
        GN + "Anthropic+Claude+when:7d"]},
    "Google": {"color": "#1f8a5b", "dark": "#55c28d", "feeds": [
        GN + "Google+Gemini+OR+DeepMind+when:7d",
        "https://blog.google/technology/ai/rss/",
        "https://deepmind.google/blog/rss.xml"]},
    "OpenAI": {"color": "#7a54c9", "dark": "#a98af0", "feeds": [
        GN + "OpenAI+ChatGPT+OR+GPT+when:7d",
        "https://openai.com/news/rss.xml"]},
}
DAYS = 14          # quanti giorni mostrare
MAX_PER_CO = 15    # massimo notizie per azienda
MESI = ["gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RadarAI"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()

def clean(t):
    t = re.sub(r"<[^>]+>", " ", html.unescape(t or ""))
    return re.sub(r"\s+", " ", t).strip()

def parse_date(s):
    if not s: return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try: d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception: return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

def parse_feed(data):
    root = ET.fromstring(data)
    out = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"): continue
        g = lambda n: next((c for c in it if c.tag.split("}")[-1] == n), None)
        title = clean(g("title").text if g("title") is not None else "")
        link_el = g("link")
        link = ""
        if link_el is not None:
            link = link_el.get("href") or (link_el.text or "")
        first = lambda *ns: next((x for x in (g(n) for n in ns) if x is not None), None)
        de = first("pubDate", "published", "updated", "date")
        d = parse_date(de.text if de is not None else None)
        desc = first("description", "summary", "content")
        src = g("source")
        out.append({"title": title, "link": link.strip(), "date": d,
                    "summary": clean(desc.text if desc is not None else ""),
                    "source": clean(src.text) if src is not None and src.text else ""})
    return out

def collect():
    now = datetime.now(timezone.utc)
    items = []
    for co, cfg in COMPANIES.items():
        seen, rows = set(), []
        for url in cfg["feeds"]:
            try:
                rows += parse_feed(fetch(url))
            except Exception as e:
                print(f"[avviso] {co}: {url} non letto ({e})", file=sys.stderr)
        for r in sorted((r for r in rows if r["date"]), key=lambda r: r["date"], reverse=True):
            if r["date"] < now - timedelta(days=DAYS): continue
            title, pub = r["title"], r["source"]
            if " - " in title and not pub:       # Google News: "Titolo - Testata"
                title, pub = title.rsplit(" - ", 1)
            key = re.sub(r"\W+", "", title.lower())[:60]
            if key in seen or not title: continue
            seen.add(key)
            summ = r["summary"]
            if summ.lower().startswith(title.lower()[:30]): summ = ""   # Google News ripete il titolo
            items.append({**r, "title": title, "source": pub or "Fonte ufficiale",
                          "summary": summ[:260], "co": co})
            if len([i for i in items if i["co"] == co]) >= MAX_PER_CO: break
    return sorted(items, key=lambda i: i["date"], reverse=True), now

def render(items, now):
    e = html.escape
    cos = list(COMPANIES)
    css_co = "".join(f'[data-co="{c}"]{{--dot:{v["color"]}}}' for c, v in COMPANIES.items())
    css_dk = "".join(f'[data-co="{c}"]{{--dot:{v["dark"]}}}' for c, v in COMPANIES.items())
    tiles = "".join(
        f'<button class="tile" type="button" data-filter="{e(c)}" data-co="{e(c)}" aria-pressed="false">'
        f'<span class="nm"><span class="dot"></span>{e(c)}</span>'
        f'<span class="n">{sum(1 for i in items if i["co"]==c)}</span></button>' for c in cos)
    li = ""
    for i in items:
        d = i["date"].astimezone(timezone.utc)
        li += (f'<li class="item" data-co="{e(i["co"])}"><div class="when">{d.day} {MESI[d.month-1]}</div><div>'
               f'<div class="co"><span class="dot"></span>{e(i["co"])} · <span class="pub">{e(i["source"])}</span></div>'
               f'<h3><a href="{e(i["link"])}" target="_blank" rel="noopener">{e(i["title"])}</a></h3>'
               + (f'<p>{e(i["summary"])}</p>' if i["summary"] else "") + '</div></li>')
    upd = f"{now.day} {MESI[now.month-1]} {now.year}, {now:%H:%M} UTC"
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Radar AI Big Tech</title>
<style>
:root{{--bg:#f3f4f7;--surface:#fff;--fg:#171b26;--muted:#5d6578;--line:#dfe2ea;--focus:#2f55d4;
--font:system-ui,-apple-system,"Segoe UI",sans-serif;--mono:ui-monospace,Menlo,Consolas,monospace}}
{css_co}
@media(prefers-color-scheme:dark){{:root{{--bg:#11141c;--surface:#181c26;--fg:#e8ebf3;--muted:#9aa2b6;--line:#2a3040;--focus:#8aa4ff;color-scheme:dark}}{css_dk}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 var(--font)}}
.wrap{{max-width:900px;margin:0 auto;padding:24px 16px 40px;display:flex;flex-direction:column;gap:18px}}
h1{{margin:0;font-size:1.75rem;letter-spacing:-.02em}}.sub{{color:var(--muted);margin:4px 0 0}}
.stamp{{font:.78rem var(--mono);color:var(--muted)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}}
.tile{{font:inherit;color:inherit;text-align:left;cursor:pointer;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column}}
.tile[aria-pressed=true]{{border-color:var(--fg);box-shadow:inset 0 0 0 1px var(--fg)}}
.nm{{display:flex;align-items:center;gap:8px;font-weight:600}}.n{{font:500 1.6rem var(--mono)}}
.dot{{width:9px;height:9px;border-radius:50%;background:var(--dot,var(--fg));flex:none}}
.feed{{list-style:none;margin:0;padding:0;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
.item{{display:grid;grid-template-columns:64px minmax(0,1fr);gap:4px 16px;padding:14px 16px;border-top:1px solid var(--line)}}
.item:first-child{{border-top:0}}.when{{font:.8rem var(--mono);color:var(--muted);padding-top:3px}}
.co{{display:flex;align-items:center;gap:6px;font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em}}.pub{{font-weight:400;text-transform:none;color:var(--muted);letter-spacing:0}}
h3{{margin:3px 0;font-size:1rem;line-height:1.3}}h3 a{{text-decoration:none}}h3 a:hover{{text-decoration:underline}}
p{{margin:0;color:var(--muted);font-size:.9rem}}a:focus-visible,button:focus-visible{{outline:2px solid var(--focus);outline-offset:2px}}
footer{{font-size:.8rem;color:var(--muted)}}@media(max-width:520px){{.item{{grid-template-columns:minmax(0,1fr)}}}}
</style></head><body><div class="wrap">
<header><h1>Radar AI Big Tech</h1><p class="sub">Ultime notizie di Microsoft, Anthropic, Google e OpenAI dai feed pubblici, degli ultimi {DAYS} giorni.</p>
<div class="stamp">Aggiornato il {upd}</div></header>
<div class="tiles"><button class="tile" type="button" data-filter="all" aria-pressed="true"><span class="nm">Tutte</span><span class="n">{len(items)}</span></button>{tiles}</div>
<ol class="feed" id="feed">{li}</ol>
<footer>Titoli e link provengono da feed pubblici (Google News e blog ufficiali). Le notizie non sono verificate: controlla sempre la fonte originale.</footer></div>
<script>
var t=document.querySelectorAll('.tile'),it=document.querySelectorAll('.item');
t.forEach(function(b){{b.onclick=function(){{var k=b.dataset.filter;
it.forEach(function(i){{i.hidden=k!=='all'&&i.dataset.co!==k}});
t.forEach(function(x){{x.setAttribute('aria-pressed',x===b)}})}}}});
</script></body></html>"""

if __name__ == "__main__":
    items, now = collect()
    if not items:
        sys.exit("Nessuna notizia letta: controlla la connessione o i feed. index.html non modificato.")
    open("index.html", "w", encoding="utf-8").write(render(items, now))
    print(f"index.html creato con {len(items)} notizie")
