#!/usr/bin/env python3
"""Lit une page web et affiche son texte (titre, date, og:image, paragraphes), pour vérifier une news sans WebFetch.
Usage : python3 lire.py URL [nb_caracteres]
        python3 lire.py github "claude skill" [jours]   → dépôts GitHub créés récemment, triés par étoiles
"""
import html, json, re, sys, urllib.request, urllib.parse, datetime

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept-Language": "fr,en;q=0.8"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read(3_000_000).decode("utf-8", "ignore")

def page(url, n=6000):
    h = get(url)
    meta = lambda p: (re.search(p, h, re.I) or [None, ""])[1]
    print("TITRE :", html.unescape(meta(r"<title[^>]*>(.*?)</title>")).strip())
    print("DATE :", meta(r'(?:article:published_time|datePublished)["\']?\s*(?:content=|:)\s*["\']([^"\']+)'))
    print("IMAGE :", meta(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)') or meta(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image'))
    h = re.sub(r"(?is)<(script|style|nav|footer|header|noscript|svg)[^>]*>.*?</\1>", " ", h)
    t = re.sub(r"(?s)<[^>]+>", " ", h); t = re.sub(r"\s+", " ", html.unescape(t)).strip()
    print("TEXTE :", t[:n])

def github(q, jours=7):
    d = (datetime.date.today() - datetime.timedelta(days=int(jours))).isoformat()
    u = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": f"{q} created:>{d}", "sort": "stars", "per_page": 15})
    for r in json.loads(get(u))["items"]:
        print(f'{r["stargazers_count"]:>6} ★  {r["html_url"]}  —  {(r["description"] or "")[:140]}')

if __name__ == "__main__":
    if sys.argv[1] == "github":
        github(sys.argv[2], *(sys.argv[3:4]))
    else:
        page(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 6000)
