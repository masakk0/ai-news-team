#!/usr/bin/env python3
"""Radar AI Big Tech: legge feed RSS/Atom e genera index.html (solo libreria standard)."""
import html, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Rome")
except Exception:
    TZ = timezone(timedelta(hours=2))

DAYS = 7           # quanti giorni mostrare
MAX_PER_CO = 20    # massimo notizie (dopo l'unione dei doppioni) per azienda
GN = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="
Q = f"+when:{DAYS}d"
# Modifica qui feed e colori. Ogni feed è (indirizzo, è_ufficiale).
COMPANIES = {
    "Microsoft": {"light": "#2f6fdb", "dark": "#6c9bf5", "own": ["microsoft"], "feeds": [
        (GN + "Microsoft+AI+OR+Copilot+OR+Windows+OR+Azure" + Q, False),
        ("https://blogs.microsoft.com/feed/", True)]},
    "Anthropic": {"light": "#c0592b", "dark": "#e08a5f", "own": ["anthropic"], "feeds": [
        (GN + "Anthropic+Claude" + Q, False),
        (GN + "site:anthropic.com" + Q, True)]},
    "Google": {"light": "#1f8a5b", "dark": "#55c28d", "own": ["google", "deepmind"], "feeds": [
        (GN + "Google+Gemini+OR+DeepMind" + Q, False),
        ("https://blog.google/technology/ai/rss/", True),
        ("https://deepmind.google/blog/rss.xml", True)]},
    "OpenAI": {"light": "#7a54c9", "dark": "#a98af0", "own": ["openai"], "feeds": [
        (GN + "OpenAI+ChatGPT+OR+GPT" + Q, False),
        ("https://openai.com/news/rss.xml", True)]},
}
MESI = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
GIORNI = ["lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica"]
# Filtro per argomento, pensato per sviluppatori e solution architect.
# 1) la notizia deve parlare di AI (AI_RE);
# 2) deve toccare almeno un argomento tecnico (TAGS). "Modelli" conta solo se c'è anche un verbo di rilascio;
# 3) per i feed non ufficiali si scartano titoli su borsa, cause legali, politica, consumer (NOISE_RE).
AI_RE = re.compile(r"\b(ai|a\.i\.|artificial intelligence|chatgpt|gpt[-\s]?\w*|claude|gemini|copilot|llms?|openai|"
    r"anthropic|deepmind|codex|sora|maia|agents?|agentic|machine learning|generative|genai|foundry|mythos|astra|"
    r"fable|opus|sonnet|haiku|flash-lite|chatbots?|reasoning|inference|open[-\s]weights?)\b", re.I)
TAGS = {
    "Modelli": re.compile(r"\b(gpt[-\s]?\w*|claude|gemini|opus|sonnet|haiku|mythos|astra|fable|flash(-lite)?|llama|mistral|"
        r"deepseek|qwen|grok|models?|benchmarks?|multimodal|reasoning)\b", re.I),
    "API e SDK": re.compile(r"\b(apis?|sdks?|cli|developers?|devs?|function calling|tool use|mcp|context window|tokens?|"
        r"rate limits?|deprecat\w*|batch|prompt cach\w*|caching|fine-?tun\w*|embeddings?|structured outputs?|plugins?|"
        r"connectors?|marketplace|github|codex|claude code|vs code)\b", re.I),
    "Agenti": re.compile(r"\b(agents?|agentic|computer use|browser use|workflows?|automation|orchestrat\w*|copilot)\b", re.I),
    "Sicurezza": re.compile(r"\b(security|safety|sandbox\w*|guardrails?|compliance|governance|privacy|data retention|"
        r"vulnerabilit\w*|jailbreak\w*|alignment|misalign\w*|evals?|red[- ]team\w*|prompt injection|audit\w*|"
        r"regulat\w*|eu ai act)\b", re.I),
    "Prezzi": re.compile(r"\b(pricing|prices?|price cuts?|cheaper|costs?|credits?|free tier|usage limits?|quotas?)\b", re.I),
    "Infrastruttura": re.compile(r"\b(chips?|gpus?|tpus?|data ?centers?|azure|vertex|bedrock|foundry|inference|latency|compute|"
        r"cloud|maia|nvidia|rtx|on-device|local ai|training)\b", re.I),
    "Open source": re.compile(r"\b(open[- ]source|open[- ]weights?|hugging ?face)\b", re.I),
}
RELEASE_RE = re.compile(r"\b(launch\w*|releas\w*|unveil\w*|introduc\w*|rolls? out|rolling out|rollout|available|ships?|"
    r"shipping|debuts?|upgrad\w*|updat\w*|adds?|preview|beta|coming|arrives?|announc\w*|expands?|open-?sourc\w*)\b", re.I)
NOISE_RE = re.compile(r"\b(stocks?|shares|share price|earnings|price target|analysts?|dividends?|investors?|valuation|"
    r"ipo|market cap|nasdaq|wall street|etfs?|buy or sell|should you buy|worth buying|deals?|discounts?|layoffs?|"
    r"job cuts|hiring freeze|lawsuits?|sues?|sued|court|senators?|trump|election|delusions?|teens?|kids|children|"
    r"advertis\w*|ads|celebrit\w*|review)\b", re.I)

def tags_of(title, summ):
    allt, tt = set(), set()
    for name, rx in TAGS.items():
        if rx.search(title): allt.add(name); tt.add(name)
        elif rx.search(summ): allt.add(name)
    if "Modelli" in allt and not RELEASE_RE.search(title + " " + summ):
        allt.discard("Modelli"); tt.discard("Modelli")
    return allt, tt

def relevant(r):
    if not AI_RE.search(r["title"] + " " + r["summary"]): return False
    if r["official"]: return bool(r["tags"])
    if NOISE_RE.search(r["title"]): return False
    return bool(r["ttags"]) or len(r["tags"]) >= 2

STOP = set("the and for with from that this its new says say after over into more about not has have via will how why what who are was were can may".split())

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
        try: d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception: return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

def parse_feed(data):
    root = ET.fromstring(data)
    out = []
    for it in root.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"): continue
        g = lambda n: next((c for c in it if c.tag.split("}")[-1] == n), None)
        first = lambda *ns: next((x for x in (g(n) for n in ns) if x is not None), None)
        te, le, se = g("title"), g("link"), g("source")
        de = first("pubDate", "published", "updated", "date")
        ds = first("description", "summary", "content")
        link = ""
        if le is not None:
            link = le.get("href") or le.text or ""
        out.append({"title": clean(te.text if te is not None else ""), "link": link.strip(),
                    "date": parse_date(de.text if de is not None else None),
                    "summary": clean(ds.text if ds is not None else ""),
                    "source": clean(se.text) if se is not None and se.text else ""})
    return out

def tokens(t):
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 2 and w not in STOP}

def same_story(a, b):
    inter = len(a & b)
    return inter >= 3 and inter / min(len(a), len(b)) >= 0.6

def tidy(row, official_feed, own):
    title, pub = row["title"], row["source"]
    if pub:                                   # toglie " - Testata" in coda
        title = re.sub(r"\s*[-–|]\s*" + re.escape(pub) + r"\s*$", "", title)
    elif " - " in title:
        title, pub = title.rsplit(" - ", 1)
    summ = row["summary"]
    if summ.lower().startswith(title.lower()[:30]): summ = ""   # Google News ripete il titolo
    low = (pub or "").lower()
    official = official_feed or any(low.startswith(o) for o in own)
    allt, tt = tags_of(title, summ)
    return {"title": title.strip(), "link": row["link"], "date": row["date"], "summary": summ[:280],
            "source": pub or "Fonte ufficiale", "official": official, "tok": tokens(title),
            "tags": allt, "ttags": tt}

def build_clusters(co, rows):
    mine = []
    for r in sorted(rows, key=lambda r: r["date"], reverse=True):
        for c in mine:
            if any(r["link"] == x["link"] for x in c) or any(same_story(r["tok"], x["tok"]) for x in c):
                c.append(r); break
        else:
            mine.append([r])
    out = []
    for c in mine[:MAX_PER_CO]:
        main = next((x for x in c if x["official"]), c[0])
        others, seen = [], {main["source"]}
        for x in c:
            if x is not main and x["source"] not in seen:
                seen.add(x["source"]); others.append(x)
        out.append({"co": co, "main": main, "others": others, "n": len(seen),
                    "date": max(x["date"] for x in c), "tags": set().union(*(x["tags"] for x in c))})
    return out

def collect():
    now = datetime.now(timezone.utc)
    clusters = []
    for co, cfg in COMPANIES.items():
        rows = []
        for url, official in cfg["feeds"]:
            try:
                rows += [t for t in (tidy(r, official, cfg["own"]) for r in parse_feed(fetch(url))
                                     if r["date"] and r["title"] and r["date"] >= now - timedelta(days=DAYS))
                         if relevant(t)]
            except Exception as e:
                print(f"[avviso] {co}: {url} non letto ({e})", file=sys.stderr)
        clusters += build_clusters(co, rows)
    clusters.sort(key=lambda c: c["date"], reverse=True)
    return clusters, now

def render(clusters, now):
    e = html.escape
    loc = lambda d: d.astimezone(TZ)
    css_l = "".join(f'[data-co="{c}"]{{--dot:{v["light"]}}}' for c, v in COMPANIES.items())
    css_d = "".join(f'[data-co="{c}"]{{--dot:{v["dark"]}}}' for c, v in COMPANIES.items())
    chips = "".join(
        f'<button class="chip" type="button" data-filter="{e(c)}" data-co="{e(c)}" aria-pressed="false">'
        f'<span class="dot"></span>{e(c)}<span class="n">{sum(1 for k in clusters if k["co"] == c)}</span></button>'
        for c in COMPANIES)

    tagbtns = '<button class="tg" type="button" data-tag="all" aria-pressed="true">Tutti gli argomenti</button>' + "".join(
        f'<button class="tg" type="button" data-tag="{e(t)}" aria-pressed="false">{e(t)}<span class="n">{sum(1 for k in clusters if t in k["tags"])}</span></button>' for t in TAGS)

    def row(k):
        m = k["main"]
        d = loc(k["date"])
        q = e((m["title"] + " " + m["summary"] + " " + k["co"] + " " + m["source"]).lower())
        tl = [t for t in TAGS if t in k["tags"]]
        tga = "|" + "|".join(tl) + "|"
        tagh = ('<div class="tags">' + "".join(f'<span class="tag">{e(t)}</span>' for t in tl) + '</div>') if tl else ""
        also = ""
        if k["others"]:
            also = '<div class="also">Anche su: ' + " ".join(
                f'<a href="{e(x["link"])}" target="_blank" rel="noopener">{e(x["source"])}</a>' for x in k["others"][:6]) + "</div>"
        return (f'<li class="item" data-co="{e(k["co"])}" data-q="{q}" data-tags="{tga}"><time class="when" datetime="{k["date"].isoformat()}">{d:%H:%M}</time><div>'
                f'<div class="co"><span class="dot"></span>{e(k["co"])}<span class="pub">· {e(m["source"])}</span>'
                + ('<span class="badge">Ufficiale</span>' if m["official"] else "") + '</div>'
                f'<h3><a href="{e(m["link"])}" target="_blank" rel="noopener">{e(m["title"])}</a></h3>'
                + (f'<p>{e(m["summary"])}</p>' if m["summary"] else "") + tagh + also + '</div></li>')

    days, order = {}, []
    for k in clusters:
        d = loc(k["date"]).date()
        if d not in days: days[d] = []; order.append(d)
        days[d].append(k)
    feed = "".join(
        f'<section class="day"><h2>{GIORNI[d.weekday()]} {d.day} {MESI[d.month-1]}</h2><ol class="feed">'
        + "".join(row(k) for k in days[d]) + '</ol></section>' for d in order)

    hot = sorted((k for k in clusters if k["n"] >= 2), key=lambda k: (k["n"], k["date"]), reverse=True)[:4]
    top = ""
    if hot:
        top = ('<section class="hot" id="hot"><h2>Più coperte</h2><ul>' + "".join(
            f'<li data-co="{e(k["co"])}" data-tags="|{"|".join(t for t in TAGS if t in k["tags"])}|"><span class="dot"></span><a href="{e(k["main"]["link"])}" target="_blank" rel="noopener">{e(k["main"]["title"])}</a>'
            f'<span class="nt">{k["n"]} testate</span></li>' for k in hot) + '</ul></section>')
    n = loc(now)
    upd = f"{n.day} {MESI[n.month-1]} {n.year}, {n:%H:%M}"
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Radar AI Big Tech</title>
<style>
:root{{--bg:#f3f4f7;--surface:#fff;--fg:#171b26;--muted:#5d6578;--line:#dfe2ea;--focus:#2f55d4;--badge:#e9ecf3;
--font:system-ui,-apple-system,"Segoe UI",sans-serif;--mono:ui-monospace,Menlo,Consolas,monospace}}
{css_l}
@media(prefers-color-scheme:dark){{:root{{--bg:#11141c;--surface:#181c26;--fg:#e8ebf3;--muted:#9aa2b6;--line:#2a3040;--focus:#8aa4ff;--badge:#262c3c;color-scheme:dark}}{css_d}}}
*{{box-sizing:border-box}}[hidden]{{display:none!important}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 var(--font)}}
a{{color:inherit}}a:focus-visible,button:focus-visible,input:focus-visible{{outline:2px solid var(--focus);outline-offset:2px}}
.wrap{{max-width:900px;margin:0 auto;padding:24px 16px 40px;display:flex;flex-direction:column;gap:18px}}
h1{{margin:0;font-size:1.75rem;letter-spacing:-.02em;line-height:1.15}}.sub{{color:var(--muted);margin:4px 0 0;max-width:62ch}}
.stamp{{font:.78rem var(--mono);color:var(--muted);margin-top:6px}}
.bar{{position:sticky;top:0;z-index:3;background:var(--bg);padding-block:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-bottom:1px solid var(--line)}}
.chip{{font:inherit;font-size:.88rem;font-weight:600;color:inherit;cursor:pointer;background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:6px 12px;display:inline-flex;align-items:center;gap:7px}}
.chip .n{{font:500 .78rem var(--mono);color:var(--muted)}}
.chip[aria-pressed=true]{{border-color:var(--fg);box-shadow:inset 0 0 0 1px var(--fg)}}
.dot{{width:9px;height:9px;border-radius:50%;background:var(--dot,var(--fg));flex:none}}
.tgrow{{flex-basis:100%;display:flex;flex-wrap:wrap;gap:6px}}.tg{{font:inherit;font-size:.78rem;color:var(--muted);cursor:pointer;background:transparent;border:1px solid var(--line);border-radius:6px;padding:3px 9px;display:inline-flex;gap:6px}}.tg .n{{font:.72rem var(--mono)}}.tg[aria-pressed=true]{{color:var(--fg);border-color:var(--fg)}}.tags{{margin-top:6px;display:flex;flex-wrap:wrap;gap:4px}}.tag{{font-size:.7rem;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 6px}}
#q{{flex:1 1 180px;min-width:0;font:inherit;color:var(--fg);background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:7px 10px}}
.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
h2{{margin:0 0 8px;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.09em;color:var(--muted)}}
.hot{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
.hot ul{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}}
.hot li{{display:flex;align-items:baseline;gap:8px}}.hot a{{font-weight:600;text-decoration:none}}.hot a:hover{{text-decoration:underline}}
.nt{{margin-left:auto;font:.75rem var(--mono);color:var(--muted);white-space:nowrap;padding-left:8px}}
.day{{display:flex;flex-direction:column}}#days{{display:flex;flex-direction:column;gap:18px}}
.feed{{list-style:none;margin:0;padding:0;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
.item{{display:grid;grid-template-columns:48px minmax(0,1fr);gap:4px 14px;padding:14px 16px;border-top:1px solid var(--line)}}
.item:first-child{{border-top:0}}.when{{font:.8rem var(--mono);color:var(--muted);padding-top:3px}}
.co{{display:flex;flex-wrap:wrap;align-items:center;gap:4px 6px;font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em}}
.pub{{font-weight:400;text-transform:none;color:var(--muted);letter-spacing:0}}
.badge{{font-size:.68rem;background:var(--badge);border-radius:4px;padding:1px 6px;margin-left:2px}}
h3{{margin:3px 0;font-size:1rem;line-height:1.3;text-wrap:balance}}h3 a{{text-decoration:none}}h3 a:hover{{text-decoration:underline}}
p{{margin:0;color:var(--muted);font-size:.9rem;max-width:70ch}}
.also{{margin-top:6px;font-size:.8rem;color:var(--muted);display:flex;flex-wrap:wrap;gap:2px 10px}}
.also a{{color:var(--fg);text-decoration-color:var(--line);text-underline-offset:3px}}
.empty{{color:var(--muted);padding:16px 0}}footer{{font-size:.8rem;color:var(--muted)}}
@media(max-width:520px){{.item{{grid-template-columns:minmax(0,1fr)}}.nt{{display:none}}}}
</style></head><body><div class="wrap">
<header><h1>Radar AI Big Tech</h1><p class="sub">Novità tecniche su AI di Microsoft, Anthropic, Google e OpenAI per sviluppatori e solution architect: modelli, API e SDK, agenti, sicurezza, prezzi e infrastruttura.</p>
<div class="stamp">Aggiornato il {upd} · ultimi {DAYS} giorni · <span id="count">{len(clusters)} notizie</span></div></header>
<div class="bar"><button class="chip" type="button" data-filter="all" aria-pressed="true">Tutte<span class="n">{len(clusters)}</span></button>{chips}
<label class="sr" for="q">Cerca nelle notizie</label><input id="q" type="search" placeholder="Cerca (es. Gemini, chip, prezzi)" autocomplete="off"><div class="tgrow">{tagbtns}</div></div>
{top}
<main id="days">{feed}</main>
<p class="empty" id="empty" hidden>Nessuna notizia corrisponde ai filtri.</p>
<footer>Titoli e link da feed pubblici (Google News e blog ufficiali), filtrati per rilevanza tecnica (AI, API, agenti, sicurezza, prezzi, infrastruttura). Le notizie non sono verificate: controlla la fonte originale prima di citarle.</footer></div>
<script>
(function(){{
var chips=[].slice.call(document.querySelectorAll('.chip')),items=[].slice.call(document.querySelectorAll('.item')),
hot=[].slice.call(document.querySelectorAll('#hot li')),days=[].slice.call(document.querySelectorAll('.day')),
q=document.getElementById('q'),count=document.getElementById('count'),empty=document.getElementById('empty'),hotBox=document.getElementById('hot'),
st={{co:'all',q:'',tag:'all'}},tgs=[].slice.call(document.querySelectorAll('.tg'));
function ok(el,withText){{return (st.co==='all'||el.dataset.co===st.co)&&(st.tag==='all'||(el.dataset.tags||'').indexOf('|'+st.tag+'|')>-1)&&(!withText||!st.q||el.dataset.q.indexOf(st.q)>-1)}}
function apply(){{var n=0;
items.forEach(function(i){{var v=ok(i,true);i.hidden=!v;if(v)n++}});
days.forEach(function(d){{d.hidden=!d.querySelector('.item:not([hidden])')}});
hot.forEach(function(h){{h.hidden=!ok(h,false)}});
if(hotBox)hotBox.hidden=!!st.q||!hot.some(function(h){{return !h.hidden}});
count.textContent=n+(n===1?' notizia':' notizie');empty.hidden=n>0;
chips.forEach(function(c){{c.setAttribute('aria-pressed',c.dataset.filter===st.co)}});tgs.forEach(function(t){{t.setAttribute('aria-pressed',t.dataset.tag===st.tag)}})}}
chips.forEach(function(c){{c.addEventListener('click',function(){{st.co=c.dataset.filter;
try{{history.replaceState(null,'',st.co==='all'?location.pathname:'#'+encodeURIComponent(st.co))}}catch(e){{}}apply()}})}});
tgs.forEach(function(t){{t.addEventListener('click',function(){{st.tag=t.dataset.tag;apply()}})}});
q.addEventListener('input',function(){{st.q=q.value.trim().toLowerCase();apply()}});
var h=decodeURIComponent(location.hash.slice(1));
if(chips.some(function(c){{return c.dataset.filter===h}}))st.co=h;
apply();
}})();
</script></body></html>"""

if __name__ == "__main__":
    clusters, now = collect()
    if not clusters:
        sys.exit("Nessuna notizia letta: controlla la connessione o i feed. index.html non modificato.")
    open("index.html", "w", encoding="utf-8").write(render(clusters, now))
    print(f"index.html creato con {len(clusters)} notizie")
