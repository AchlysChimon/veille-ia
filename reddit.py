#!/usr/bin/env python3
"""Récupère le top de la semaine de plusieurs subreddits → reddit/top.json (lancé par GitHub chaque matin).
Utilise l'API officielle si REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET sont définis, sinon les pages .json publiques."""
import base64, json, os, sys, time, urllib.request
SUBS = ["ClaudeAI", "ChatGPT", "OpenAI", "LocalLLaMA", "StableDiffusion", "aivideo", "singularity", "FigmaDesign", "UXDesign", "webdev", "artificial", "GeminiAI"]
UA = "linux:veille-ia:1.0 (by /u/veille-ia-bot)"

def token():
    cid, sec = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and sec): return None
    req = urllib.request.Request("https://www.reddit.com/api/v1/access_token", data=b"grant_type=client_credentials",
        headers={"User-Agent": UA, "Authorization": "Basic " + base64.b64encode(f"{cid}:{sec}".encode()).decode()})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())["access_token"]

def main():
    tok = token(); out = {"genere": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "mode": "api" if tok else "public", "subs": {}}
    ok = 0
    for s in SUBS:
        url = (f"https://oauth.reddit.com/r/{s}/top?t=week&limit=12" if tok else f"https://www.reddit.com/r/{s}/top.json?t=week&limit=12")
        h = {"User-Agent": UA}; 
        if tok: h["Authorization"] = f"bearer {tok}"
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20).read())
            out["subs"][s] = [{"titre": p["data"]["title"], "votes": p["data"]["score"], "commentaires": p["data"]["num_comments"],
                               "lien": "https://www.reddit.com" + p["data"]["permalink"], "url": p["data"].get("url"),
                               "image": (p["data"].get("preview", {}).get("images", [{}])[0].get("source", {}).get("url", "") or "").replace("&amp;", "&"),
                               "date": time.strftime("%Y-%m-%d", time.gmtime(p["data"]["created_utc"])),
                               "texte": (p["data"].get("selftext") or "")[:500]} for p in d["data"]["children"]]
            ok += 1; print(s, "OK", len(out["subs"][s]))
        except Exception as e:
            print(s, "KO", e)
        time.sleep(1.2)
    os.makedirs("reddit", exist_ok=True)
    json.dump(out, open("reddit/top.json", "w"), ensure_ascii=False, indent=1)
    print(f"{ok}/{len(SUBS)} subreddits")

if __name__ == "__main__":
    main()
