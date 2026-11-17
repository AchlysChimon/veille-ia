#!/usr/bin/env python3
"""Carrousel + vidéo TikTok « FLASH IA » (1080x1920) : couverture, news, mèmes, slide de fin.

Usage : python3 render_tiktok.py news.json sortie/
Sortie : 00.png, 01.png… (carrousel), flash_ia.mp4 (vidéo avec GIF animés), legende_tiktok.txt

Champs lus dans news.json (en plus de ceux de render.py) :
  "tiktok": [3, 1, 7, ...]       indices (à partir de 1) des news retenues, dans l'ordre. Absent : les 7 premières.
  "couverture_tiktok": "Les 7 news IA [[à ne pas rater]]"   ([[...]] = tuiles jaunes)
  "memes": [ {"apres": 3, "image": "giphy:mind blown", "legende": "Moi quand [[ChatGPT]] paie à ma place"} ]
            slide mème plein écran insérée après la 3e news TikTok (GIF animé dans la vidéo).
  Par news :
    "titre_tiktok": "ChatGPT fait [[tes achats]]"   titre des tuiles. Absent : "titre".
    "texte_tiktok": "..."                          ≤ 220 caractères. Absent : "texte".
    "bemol": "Pas encore dispo en France"          ligne d'avertissement (optionnelle).
    "image_tiktok": "https://…"                    image dédiée à TikTok (sinon "image", sinon og:image du lien).
    "cadrage": "plein" | "carte"                   force le cadrage. Par défaut : automatique
                                                   (paysage, capture d'écran ou image claire → carte entière sur fond flouté).
    "meme": "giphy:shut up and take my money"     mème collé en sticker : URL directe, ou « giphy:mots » / « tenor:mots »
                                                   (premier GIF trouvé ; animé dans la vidéo).
    "recherche_image": "California lawsuit OpenAI" mots-clés (en anglais de préférence) pour trouver une illustration
                                                   si la source n'a pas d'image exploitable.
    L'image peut aussi valoir « recherche:mots » (illustration trouvée sur Bing Images).
    "meme_legende": "Shut up and take my money"    légende courte sous le sticker (optionnelle).
"""
import base64, html, json, math, re, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import render as R   # récupération des images (og:image, capture d'écran de secours)

NAME = "FLASH IA"
DUR = {"cover": 2.5, "news": 4.5, "meme": 3.5, "end": 3.0}

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1920px;overflow:hidden;position:relative;background:#000;color:#fff;font-family:'Inter'}
.ph{position:absolute;inset:0;overflow:hidden}.ph img{width:100%;height:100%;object-fit:cover;display:block}
.frame{display:none}
body.carte .ph img{filter:blur(38px) brightness(.38) saturate(1.2);transform:scale(1.25)}
body.carte .frame{display:flex;position:absolute;top:210px;left:60px;right:60px;height:820px;align-items:center;justify-content:center}
.frame img{max-width:100%;max-height:100%;border-radius:20px;border:5px solid #fff;box-shadow:0 30px 80px rgba(0,0,0,.6);display:block}
.noimg{position:absolute;inset:0;background:radial-gradient(900px 700px at 70% 20%,#3a3a3a,#0b0b0b 70%)}
.sh{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.45),transparent 15%,transparent 42%,rgba(0,0,0,.88) 64%,#000 86%)}
body.carte .sh{background:linear-gradient(180deg,rgba(0,0,0,.3),transparent 20%,transparent 50%,rgba(0,0,0,.85) 66%,#000 88%)}
.c{position:absolute;width:100px;height:100px;border:8px solid #fff}
.top{position:absolute;top:95px;left:100px;right:100px;display:flex;justify-content:space-between;font:700 34px 'JetBrains Mono';text-shadow:0 2px 10px rgba(0,0,0,.6)}
.top b{color:#FF2020}
.col{position:absolute;left:60px;right:60px;bottom:170px;display:flex;flex-direction:column;gap:34px}
.h{font-size:150px}
.w{display:inline-block;background:#0A0A0A;color:#fff;font-family:'Anton';font-size:1em;line-height:1;text-transform:uppercase;padding:.07em .15em .09em;margin:0 .07em .08em 0;border-radius:10px;border-top:3px solid #333;box-shadow:0 10px 30px rgba(0,0,0,.6)}
.w.y{background:#FFE600;color:#000;border-top-color:#fff59a}
p{font:500 36px/1.42 'Inter';color:#e4e4e4}
.b{font:700 26px/1.3 'JetBrains Mono';color:#FFE600}
.swipe{position:absolute;bottom:120px;right:100px;font:700 34px 'JetBrains Mono';color:#fff}
.meme{position:absolute;top:250px;right:70px;width:440px;background:#fff;padding:14px 14px 16px;transform:rotate(6deg);box-shadow:0 20px 50px rgba(0,0,0,.55);z-index:5}
.meme img{width:100%;height:auto;display:block}
.meme .cap{font:800 28px/1.15 'Inter';color:#000;text-align:center;margin-top:12px;text-transform:uppercase}
.mfull{position:absolute;top:620px;left:60px;right:60px;bottom:200px;display:flex;align-items:center;justify-content:center}
.mfull img{max-width:100%;max-height:100%;border:6px solid #fff;border-radius:16px;display:block;box-shadow:0 30px 80px rgba(0,0,0,.6)}
"""
CORN = ('<i class=c style="top:50px;left:50px;border-right:0;border-bottom:0"></i>'
        '<i class=c style="top:50px;right:50px;border-left:0;border-bottom:0"></i>'
        '<i class=c style="bottom:50px;left:50px;border-right:0;border-top:0"></i>'
        '<i class=c style="bottom:50px;right:50px;border-left:0;border-top:0"></i>')

# Choisit le cadrage, ajuste les tuiles, renvoie la position du GIF pour la vidéo.
PREP = """async (mode) => {
  await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
  const im = document.querySelector('.ph img');
  if (im && mode !== 'plein') {
    const r = im.naturalWidth / Math.max(1, im.naturalHeight);
    let clair = false;
    try { const c = document.createElement('canvas'); c.width = 24; c.height = 24; const x = c.getContext('2d');
      x.drawImage(im, 0, 0, 24, 24); const d = x.getImageData(0, 0, 24, 24).data; let s = 0;
      for (let k = 0; k < d.length; k += 4) s += (d[k] + d[k+1] + d[k+2]) / 3; clair = s / (d.length / 4) > 185; } catch (e) {}
    if (mode === 'carte' || r > 0.8 || clair) document.body.classList.add('carte');
  }
  for (const g of document.querySelectorAll('.mfull img, body.carte .frame img')) {   // agrandit en gardant les proportions
    const P = g.parentElement, bw = P.clientWidth - 12, bh = P.clientHeight - 12;
    const k = Math.min(bw / Math.max(1, g.naturalWidth), bh / Math.max(1, g.naturalHeight));
    g.style.maxWidth = 'none'; g.style.maxHeight = 'none';
    g.style.width = Math.round(g.naturalWidth * k) + 'px'; g.style.height = Math.round(g.naturalHeight * k) + 'px';
  }
  const h = document.querySelector('.h');
  if (h) { const max = parseInt(h.dataset.max || '720'); let s = parseInt(getComputedStyle(h).fontSize);
    while ((h.offsetHeight > max || h.scrollWidth > h.clientWidth + 2) && s > 70) { s -= 4; h.style.fontSize = s + 'px'; } }
  const g = document.querySelector('img.anim');
  if (!g) return null;
  const b = g.getBoundingClientRect();
  return {cx: b.left + b.width / 2, cy: b.top + b.height / 2, w: g.offsetWidth, h: g.offsetHeight,
          a: parseFloat(g.dataset.angle || '0')};
}"""


def tiles(t):
    out = []
    for part in re.split(r"(\[\[.+?\]\])", t):
        y = part.startswith("[[")
        for w in part.strip("[]").split():
            out.append(f'<span class="w{" y" if y else ""}">{html.escape(w)}</span>')
    return "".join(out)


def plain(t):
    return re.sub(r"\[\[|\]\]", "", t)


def fetch(url, dest_stem):
    """Télécharge un mème ; renvoie (data_uri, chemin_local, est_gif)."""
    url = R.resolve_meme(url)
    if not url:
        return None, None, False
    try:
        r = R.get(url); b = r.read(15_000_000)
        ct = r.headers.get_content_type()
        gif = ct == "image/gif" or b[:6] in (b"GIF87a", b"GIF89a")
        if not ct.startswith("image/"):
            ct = "image/gif" if gif else "image/jpeg"
        path = Path(f"{dest_stem}.{'gif' if gif else 'img'}"); path.write_bytes(b)
        return f"data:{ct};base64,{base64.b64encode(b).decode()}", path, gif
    except Exception as e:
        print("mème KO", url, e)
        return None, None, False


def bg(img):
    if img:
        return f'<div class=ph><img src="{img}"></div><div class=frame><img src="{img}"></div><div class=sh></div>'
    return '<div class=noimg></div><div class=sh></div>'


def page(body):
    return f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>{body}</body></html>"


def top(right):
    return f'<div class=top><span><b>●</b> REC · {NAME}</span><span>{html.escape(right)}</span></div>'


def main(src, out):
    data = json.loads(Path(src).read_text())
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"; tmp.mkdir(exist_ok=True)
    items = data["items"]
    idx = data.get("tiktok") or list(range(1, min(7, len(items)) + 1))
    sel = [items[i - 1] for i in idx if 0 < i <= len(items)]
    n = len(sel)

    pw = sync_playwright().start(); b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 760}, user_agent=R.UA["User-Agent"], locale="fr-FR")
    R.SHOT["page"] = ctx.new_page()
    imgs = []
    for it in sel:
        img = R.image_for({"image": it.get("image_tiktok")}) if it.get("image_tiktok") else None
        if not img and it.get("image") is not False:
            img = R._image_for(it)
        if not img:   # jamais de slide sans image : illustration trouvée à partir du titre, puis capture de la page
            img = R.search_image(it.get("recherche_image") or plain(it.get("titre_tiktok") or it["titre"]))
        if not img and it.get("lien"):
            img = R.screenshot(it["lien"])
        imgs.append(img)
    cov = R.image_for({"image": data.get("image_couverture")}) or next((x for x in imgs if x), None)

    slides = []   # (html, durée, cadrage, gif local ou None)
    hook = data.get("couverture_tiktok") or f"Les {n} news IA [[à ne pas rater]]"
    slides.append((page(bg(cov) + CORN + top(data["date"]) +
        f'<div class=col><div class=h data-max=900 style="font-size:180px">{tiles(hook)}</div>'
        f'<p>IA, tech et design : l\'essentiel en {n} slides.</p></div><div class=swipe>SWIPE →</div>'),
        DUR["cover"], "plein", None))

    memes = {m.get("apres"): m for m in data.get("memes", [])}
    for i, (it, img) in enumerate(zip(sel, imgs), 1):
        uri, gpath, gif = fetch(it.get("meme"), tmp / f"m{i}")
        sticker = ""
        if uri:
            cap = it.get("meme_legende")
            sticker = (f'<div class=meme><img class="{"anim" if gif else ""}" data-angle=6 src="{uri}">'
                       + (f'<div class=cap>{html.escape(cap)}</div>' if cap else "") + "</div>")
        bem = it.get("bemol")
        slides.append((page(bg(img) + CORN + top(f"{i:02d}/{n:02d}") + sticker +
            f'<div class=col><div class=h data-max=640>{tiles(it.get("titre_tiktok") or it["titre"])}</div>'
            f'<p>{html.escape(it.get("texte_tiktok") or it["texte"])}</p>'
            + (f'<div class=b>⚠ {html.escape(bem.upper())}</div>' if bem else "") + '</div>'),
            DUR["news"], it.get("cadrage") or "auto", gpath if gif else None))
        m = memes.get(i)
        if m:
            uri, gpath, gif = fetch(m.get("image"), tmp / f"full{i}")
            if uri:
                slides.append((page(
                    '<div class=noimg style="background:#0A0A0A"></div>' + CORN + top("PAUSE MÈME") +
                    f'<div class=col style="bottom:auto;top:230px"><div class=h data-max=360 style="font-size:110px">{tiles(m.get("legende", ""))}</div></div>'
                    f'<div class=mfull><img class="{"anim" if gif else ""}" data-angle=0 src="{uri}"></div>'),
                    DUR["meme"], "plein", gpath if gif else None))
    slides.append((page(
        '<div class=noimg style="background:radial-gradient(900px 800px at 50% 30%,#2a2a2a,#000 70%)"></div>' + CORN + top("FIN") +
        f'<div class=col style="bottom:auto;top:620px"><div class=h data-max=800 style="font-size:190px">{tiles("[[Abonne-toi]] pour ta veille IA chaque matin")}</div>'
        f'<p>Les sources de chaque news sont dans la description.</p></div>'), DUR["end"], "plein", None))

    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    segs = []
    for k, (h, dur, mode, gpath) in enumerate(slides):
        pg.set_content(h); pg.wait_for_timeout(250)
        box = pg.evaluate(PREP, mode)
        png = out / f"{k:02d}.png"; pg.screenshot(path=str(png))
        segs.append((png, dur, gpath, box))
    b.close(); pw.stop()

    # Vidéo : chaque slide tient quelques secondes ; les GIF sont rejoués par-dessus (même taille, même angle).
    try:
        parts = []
        for k, (png, dur, gpath, box) in enumerate(segs):
            seg = tmp / f"s{k:02d}.mp4"
            enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-r", "30", "-t", str(dur)]
            if gpath and box:
                a = math.radians(box["a"]); w, hh = round(box["w"]), round(box["h"])
                rw = w * abs(math.cos(a)) + hh * abs(math.sin(a)); rh = w * abs(math.sin(a)) + hh * abs(math.cos(a))
                x, y = round(box["cx"] - rw / 2), round(box["cy"] - rh / 2)
                fc = (f"[1:v]scale={w}:{hh},format=rgba,rotate={a}:c=none:ow=rotw({a}):oh=roth({a})[m];"
                      f"[0:v][m]overlay={x}:{y}:shortest=0,format=yuv420p")
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
                       "-ignore_loop", "0", "-i", str(gpath), "-filter_complex", fc] + enc + [str(seg)]
            else:
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png)] + enc + [str(seg)]
            subprocess.run(cmd, check=True)
            parts.append(seg)
        lst = tmp / "list.txt"; lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", "-movflags", "+faststart", str(out / "flash_ia.mp4")], check=True)
        print("vidéo :", out / "flash_ia.mp4", round((out / "flash_ia.mp4").stat().st_size / 1e6, 1), "Mo")
    except Exception as e:
        print("vidéo KO", e)

    lines = [plain(hook) + " 👇", ""]
    for i, it in enumerate(sel, 1):
        lines.append(f"{i}. {plain(it.get('titre_tiktok') or it['titre'])} — {it.get('lien', '')}")
    lines += ["", "#ia #intelligenceartificielle #veilleia #chatgpt #claude #design #techtok"]
    (out / "legende_tiktok.txt").write_text("\n".join(lines))
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    print(f"{len(segs)} slides TikTok dans {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
