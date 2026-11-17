#!/usr/bin/env python3
"""Génère le carrousel « Veille IA » (PNG 1080x1350) à partir d'un fichier JSON.

Usage : python3 render.py news.json sortie/

Format du JSON :
{
  "date": "18 novembre 2026",
  "accroche": "L'IA avance plus vite que jamais : voici ce qui a bougé hier.",
  "items": [
    {
      "titre": "Anthropic lance Claude Fable 5.2",
      "texte": "3 à 4 phrases de contexte, avec le bémol éventuel.",
      "categorie": "IA" | "TECH" | "UI/UX",
      "visuel": {                       # un seul des trois types
        "type": "citation", "source": "NVIDIA · formulaire 8-K", "date": "12 nov. 2026",
        "lignes": ["“Jensen Huang [[has resigned]] as CEO.”"]   # [[...]] = surligné
      }
      # ou {"type": "chiffre", "valeur": "96 %", "legende": "de réussite chez Mercedes"}
      # ou {"type": "mots", "mots": ["Photoshop", "Premiere", "MCP"]}
      "image": "https://... (image de la source ; sinon og:image du lien)",
      "lien": "https://..."
    }
  ]
}
"""
import urllib.parse, base64, html, json, mimetypes, re, sys, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

def get(url, timeout=15):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)

def og_image(url):
    try:
        h = get(url).read(600_000).decode("utf-8", "ignore")
        for pat in (r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
                    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)'):
            m = re.search(pat, h, re.I)
            if m: return urllib.parse.urljoin(url, html.unescape(m.group(1)))
    except Exception as e:
        print("og:image KO", url, e)

def data_uri(url):
    try:
        r = get(url); b = r.read(8_000_000)
        ct = r.headers.get_content_type()
        if ct.startswith("text/") or b.lstrip()[:1] == b"<": return None   # une page web, pas une image
        if not ct.startswith("image/"): ct = mimetypes.guess_type(url)[0] or "image/jpeg"
        if len(b) < 3000 or "svg" in ct: return None   # icônes, pixels de tracking
        return f"data:{ct};base64,{base64.b64encode(b).decode()}"
    except Exception as e:
        print("image KO", url, e)

SHOT = {"page": None}

def search_image(terms):
    """« recherche:mots » → première grande image trouvée par Bing Images."""
    try:
        q = urllib.parse.quote(terms)
        h = get(f"https://www.bing.com/images/search?q={q}&form=HDRSC2&first=1").read(2_000_000).decode("utf-8", "ignore")
        for u in re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', h)[:8]:
            d = data_uri(html.unescape(u))
            if d and len(d) > 40_000: return d
    except Exception as e:
        print("recherche image KO", terms, e)

def resolve_meme(spec):
    """URL directe, ou « giphy:mots » / « tenor:mots » → URL du premier GIF trouvé."""
    if not spec or spec.startswith("http"): return spec
    src, _, terms = spec.partition(":")
    slug = re.sub(r"[^a-z0-9]+", "-", terms.lower()).strip("-")
    pages = [("https://giphy.com/search/" + slug, r'https://media\d?\.giphy\.com/media/(?:v1\.[^/]+/)?([A-Za-z0-9]+)/giphy\.gif'),
             ("https://tenor.com/search/" + slug + "-gifs", r'https://media1?\.tenor\.com/[A-Za-z0-9_-]+/[^"\'\s]+?\.gif')]
    if src == "tenor": pages.reverse()
    for url, pat in pages:
        try:
            h = get(url).read(3_000_000).decode("utf-8", "ignore")
            m = re.search(pat, h)
            if m:
                return f"https://media.giphy.com/media/{m.group(1)}/giphy.gif" if "giphy" in url else m.group(0)
        except Exception as e:
            print("mème KO", spec, e)

def screenshot(url):
    """Dernier recours : capture d'écran du haut de la page source."""
    pg = SHOT["page"]
    if not pg or not url: return None
    try:
        pg.goto(url, wait_until="domcontentloaded", timeout=25000); pg.wait_for_timeout(3500)
        pg.evaluate("""() => { for (const el of document.querySelectorAll('[id*=cookie],[class*=cookie],[id*=consent],[class*=consent],[class*=banner],[role=dialog]')) el.remove(); }""")
        b = pg.screenshot(type="jpeg", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(b).decode()
    except Exception as e:
        print("capture KO", url, e)

def image_for(it):
    if it.get("image") is False:   # pas de photo voulue (ex. portrait d'une personne) : visuel graphique
        return None
    d = _image_for(it)
    if not d and it.get("lien"):
        d = screenshot(it["lien"]); print("capture d'écran utilisée :", it["lien"]) if d else None
    return d

def tweet_media(url):
    """Lien x.com / twitter.com → URL de la photo (ou de la vignette vidéo) du tweet, via api.fxtwitter.com."""
    m = re.search(r"(?:x|twitter)\.com/([^/]+)/status/(\d+)", url or "")
    if not m: return None
    try:
        t = json.loads(get(f"https://api.fxtwitter.com/{m.group(1)}/status/{m.group(2)}").read()).get("tweet", {})
        md = t.get("media") or {}
        if md.get("photos"): return md["photos"][0]["url"]
        if md.get("videos"): return md["videos"][0].get("thumbnail_url")
    except Exception as e:
        print("tweet KO", url, e)

def _image_for(it):
    img = it.get("image")
    if str(img or "").startswith("recherche:"):
        d = search_image(img.split(":", 1)[1])
        if d: return d
        img = None
    lien = it.get("lien")
    for u in [img, tweet_media(img), tweet_media(lien)]:
        if u:
            d = data_uri(u) or (data_uri(og_image(u)) if og_image(u) else None)   # URL d'image, ou page dont on prend l'og:image
            if d: return d
    if lien:
        o = og_image(lien)
        if o: return data_uri(o)

ACCENTS = {"IA": "#8b5cf6", "TECH": "#22c55e", "UI/UX": "#f59e0b", "COMMU": "#38bdf8"}

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;font-family:Poppins,sans-serif;color:#fff;
 background:radial-gradient(1200px 700px at 20% 0%,#1d2233 0%,#0d0f15 55%,#08090c 100%);overflow:hidden;position:relative}
.wrap{position:absolute;top:170px;left:84px;right:84px;bottom:200px;display:flex;flex-direction:column;align-items:flex-start}
.cover{inset:0;padding:0 84px;display:block}
.tag{display:inline-block;font-weight:600;font-size:22px;letter-spacing:2px;padding:6px 16px;border-radius:999px;margin-bottom:22px}
h1{font-weight:800;font-size:62px;line-height:1.02;text-transform:uppercase;letter-spacing:-1px}
p.txt{margin-top:22px;font-weight:400;font-size:31px;line-height:1.45;color:#b9bcc6}
.media{align-self:stretch;flex:1;min-height:330px;margin-top:40px;position:relative;border-radius:22px;
 border:1.5px solid #2c3040;background:linear-gradient(160deg,#171a24,#0f1118);overflow:hidden;
 display:flex;align-items:center;justify-content:center}
.card{width:780px;background:#f1f0ec;color:#111;border-radius:18px;padding:34px 40px;box-shadow:0 20px 50px rgba(0,0,0,.45)}
.card .src{display:flex;align-items:center;gap:14px;font-weight:600;font-size:22px;color:#444}
.card .ico{width:34px;height:34px;border-radius:8px;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:20px}
.card .d{font-size:18px;color:#777;margin:6px 0 18px}
.card .l{font-weight:500;font-size:26px;line-height:1.4;margin-top:10px}
.card mark{background:none;color:inherit;border-bottom:4px solid var(--a)}
.big{font-weight:800;font-size:190px;line-height:1;letter-spacing:-6px;text-align:center}
.leg{font-weight:500;font-size:32px;color:#b9bcc6;text-align:center;margin-top:12px;padding:0 40px}
.mots{display:flex;flex-wrap:wrap;gap:18px;justify-content:center;padding:0 40px}
.mots span{font-weight:700;font-size:40px;padding:14px 30px;border-radius:999px;border:2px solid var(--a);background:rgba(255,255,255,.04)}
.media img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.glow{position:absolute;width:520px;height:520px;border-radius:50%;filter:blur(120px);opacity:.35;background:var(--a)}
.brand{position:absolute;bottom:62px;left:0;right:0;text-align:center;line-height:.95}
.brand b{display:block;font-weight:600;font-size:30px}
.brand i{display:block;font-style:normal;font-weight:800;font-size:52px}
.num{position:absolute;top:84px;right:84px;font-weight:600;font-size:24px;color:#6d7180}
.date{position:absolute;top:84px;left:84px;font-weight:600;font-size:24px;color:#6d7180}
.bg{position:absolute;inset:0;background-size:cover;background-position:center}
.bg:after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(8,9,12,.35),rgba(8,9,12,.75) 50%,#08090c 85%)}
.cover h1{font-size:92px;line-height:1.02;margin-top:560px}
.cover .sub{margin-top:30px;font-size:34px;color:#b9bcc6}
"""

def hl(s):
    s = html.escape(s)
    return re.sub(r"\[\[(.+?)\]\]", r"<mark>\1</mark>", s)

def media(v, accent):
    t = v.get("type")
    if t == "citation":
        src = html.escape(v.get("source", ""))
        lignes = "".join(f'<div class="l">{hl(x)}</div>' for x in v.get("lignes", []))
        return (f'<div class="card"><div class="src"><div class="ico" style="background:{accent}">'
                f'{html.escape(src[:1].upper())}</div>{src}</div>'
                f'<div class="d">{html.escape(v.get("date",""))}</div>{lignes}</div>')
    if t == "chiffre":
        return (f'<div class="glow"></div><div style="position:relative"><div class="big">{html.escape(v["valeur"])}</div>'
                f'<div class="leg">{html.escape(v.get("legende",""))}</div></div>')
    mots = "".join(f"<span>{html.escape(m)}</span>" for m in v.get("mots", []))
    return f'<div class="glow"></div><div class="mots" style="position:relative">{mots}</div>'

BRAND = '<div class="brand"><b>Ta veille</b><i>IA</i></div>'

def page(body, accent="#8b5cf6"):
    return f'<html><head><meta charset="utf-8"><style>{CSS}</style></head><body style="--a:{accent}">{body}</body></html>'

def main(src, out):
    data = json.loads(Path(src).read_text())
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    items = data["items"]; n = len(items)
    pw = sync_playwright().start(); b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 760}, user_agent=UA["User-Agent"], locale="fr-FR")
    SHOT["page"] = ctx.new_page()
    imgs = [image_for(it) for it in items]
    print(f"{sum(1 for x in imgs if x)}/{n} images récupérées")
    cov = image_for({"image": data.get("image_couverture")}) or next((x for x in imgs if x), None)
    pages = [page((f'<div class="bg" style="background-image:url({cov})"></div>' if cov else '') + f'<div class="wrap cover" style="position:absolute"><div class="date" style="left:84px">{html.escape(data["date"])}</div>'
                  f'<h1>{html.escape(data.get("accroche","Les news IA qui ont compté hier."))}</h1>'
                  f'<div class="sub">{n} news · IA, tech & UI/UX</div></div>{BRAND}')]
    for i, it in enumerate(items, 1):
        img = imgs[i-1]
        a = ACCENTS.get(it.get("categorie", "IA"), "#8b5cf6")
        body = (f'<div class="date">{html.escape(data["date"])}</div><div class="num">{i}/{n}</div>'
                f'<div class="wrap"><span class="tag" style="background:{a}22;color:{a}">{html.escape(it.get("categorie","IA"))}</span>'
                f'<h1>{i}. {html.escape(it["titre"])}</h1><p class="txt">{html.escape(it["texte"])}</p>'
                f'<div class="media">{f"<img src=\'{img}\'>" if img else media(it.get("visuel", {"type":"mots","mots":[it.get("categorie","IA")]}), a)}</div></div>{BRAND}')
        pages.append(page(body, a))
    pg = b.new_page(viewport={"width": 1080, "height": 1350})
    for k, h in enumerate(pages):
        pg.set_content(h); pg.wait_for_timeout(150)
        pg.screenshot(path=str(out / f"{k:02d}.png"))
    b.close(); pw.stop()
    print(f"{len(pages)} visuels dans {out}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
