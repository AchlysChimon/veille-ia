#!/usr/bin/env python3
"""Carrousel + vidéo TikTok « FLASH IA » (1080x1920) : couverture, news, mèmes, slide de fin.

Usage : python3 render_tiktok.py news.json sortie/
Sortie : 00.png, 01.png… (carrousel), flash_ia.mp4 (vidéo avec GIF animés), legende_tiktok.txt

Champs lus dans news.json (en plus de ceux de render.py) :
  "tiktok": [3, 1, 7, ...]       indices (à partir de 1) des news retenues, dans l'ordre. Absent : les 7 premières.
  "couverture_tiktok": "Les jeux vidéo de demain [[tiennent dans une page web]] ?"
            accroche qui TEASE une news précise ([[...]] = tuiles jaunes) ; "teaser": indice (à partir de 1, dans
            items) de la news teasée : elle est placée en avant-dernière news pour qu'on swipe jusqu'à la réponse,
            et son image sert de fond à la couverture.
  "memes": [ {"apres": 3, "image": "giphy:mind blown", "legende": "Moi quand [[ChatGPT]] paie à ma place"} ]
            slide mème plein écran insérée après la 3e news TikTok (GIF animé dans la vidéo).
  Par news :
    "titre_tiktok": "ChatGPT fait [[tes achats]]"   titre des tuiles. Absent : "titre".
    "texte_tiktok": "..."                          texte de la slide, COURT (≤ 190 caractères, 2 phrases) : il doit tenir
                                                   au-dessus de la légende TikTok en gros caractères. Absent : "texte".
    "bemol": "Gratuit dans 6 pays, pas encore de date pour la France."  phrase ajoutée à la fin du texte.
    "ou": "github.com/emilkowalski/skills"         où trouver l'outil / le skill / le post : affiché en étiquette.
    "image_tiktok": "https://…"                    image dédiée à TikTok (sinon "image", sinon og:image du lien).
    "cadrage": "plein" | "carte" | "entier"        plein : l'image remplit l'écran ; carte : grand panneau pleine largeur
                                                   (recadré) sur fond flouté ; entier : image affichée en entier (interface,
                                                   schéma). Par défaut : automatique (paysage ou image claire → carte).
    "meme": "tenor:this is fine dog"              mème en sticker DÉTOURÉ (fond supprimé, contour blanc), à réserver
                                                   aux news où il fait vraiment rire ; animé dans la vidéo.
    "recherche_image": "California lawsuit OpenAI" mots-clés (en anglais de préférence) pour trouver une illustration
                                                   si la source n'a pas d'image exploitable.
    L'image peut aussi valoir « recherche:mots » (illustration trouvée sur Bing Images).
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
body.carte .ph img{filter:blur(38px) brightness(.5) saturate(1.3);transform:scale(1.25)}
body.carte .frame{display:flex;position:absolute;top:210px;left:60px;right:60px;height:820px;align-items:center;justify-content:center}
.frame img{max-width:100%;max-height:100%;border-radius:20px;border:5px solid #fff;box-shadow:0 30px 80px rgba(0,0,0,.6);display:block}
.noimg{position:absolute;inset:0;background:radial-gradient(900px 700px at 70% 20%,#3a3a3a,#0b0b0b 70%)}
.sh{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.45),transparent 14%,transparent 30%,rgba(0,0,0,.7) 50%,rgba(0,0,0,.6) 80%,rgba(0,0,0,.75) 100%)}
body.carte .sh{background:linear-gradient(180deg,rgba(0,0,0,.25),transparent 20%,rgba(0,0,0,.35) 60%,rgba(0,0,0,.45) 100%)}
.c{position:absolute;width:100px;height:100px;border:8px solid #fff}
.top{position:absolute;top:95px;left:100px;right:100px;display:flex;justify-content:space-between;font:700 34px 'JetBrains Mono';text-shadow:0 2px 10px rgba(0,0,0,.6)}
.top b{color:#FF2020}
.col{position:absolute;left:60px;right:170px;bottom:440px;display:flex;flex-direction:column;gap:26px}
.h{font-size:130px}
.w{display:inline-block;background:#0A0A0A;color:#fff;font-family:'Anton';font-size:1em;line-height:1;text-transform:uppercase;padding:.07em .15em .09em;margin:0 .07em .08em 0;border-radius:10px;border-top:3px solid #333;box-shadow:0 10px 30px rgba(0,0,0,.6)}
.w.y{background:#FFE600;color:#000;border-top-color:#fff59a}
p{font:600 44px/1.36 'Inter';color:#fff;background:rgba(0,0,0,.78);padding:22px 26px;border-radius:16px;text-shadow:0 2px 6px rgba(0,0,0,.6)}
p.t{font-size:var(--pf,44px)}
.b{font:700 26px/1.3 'JetBrains Mono';color:#FFE600}
.swipe{align-self:flex-end;font:700 40px 'JetBrains Mono';color:#000;background:#FFE600;padding:10px 18px;border-radius:10px}
.meme{position:absolute;top:360px;right:50px;width:420px;transform:rotate(6deg);z-index:5;filter:drop-shadow(0 14px 24px rgba(0,0,0,.55))}
.meme img{width:100%;height:auto;display:block}
.meme img.rond{border-radius:34px;outline:9px solid #fff;outline-offset:-1px}
.ou{display:inline-block;align-self:flex-start;background:#FFE600;color:#000;font:700 34px/1.2 'JetBrains Mono';padding:12px 20px;border-radius:10px}
.mfull{position:absolute;top:620px;left:40px;right:40px;bottom:440px;display:flex;align-items:center;justify-content:center}
.mfull img{max-width:100%;max-height:100%;border-radius:24px;display:block}
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
    if (mode === 'carte' || mode === 'entier' || r > 0.8 || clair) document.body.classList.add('carte');
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
  const col = document.querySelector('.col'), p = document.querySelector('p.t');
  if (col && p) { let f = 44; while (col.getBoundingClientRect().top < 820 && f > 36) { f -= 2; p.style.fontSize = f + 'px'; } }
  const fr = document.querySelector('body.carte .frame');
  if (fr && col) { const top = 330, bot = col.getBoundingClientRect().top - 30; fr.style.top = top + 'px'; fr.style.height = Math.max(300, bot - top) + 'px';
    const g2 = fr.querySelector('img');
    if (mode === 'entier') {   // image affichée en entier (capture d'interface, schéma)
      const k2 = Math.min((fr.clientWidth - 12) / g2.naturalWidth, (fr.clientHeight - 12) / g2.naturalHeight);
      g2.style.width = Math.round(g2.naturalWidth * k2) + 'px'; g2.style.height = Math.round(g2.naturalHeight * k2) + 'px';
    } else {                   // grand panneau : toute la largeur, recadré si besoin, jamais une petite vignette
      g2.style.width = fr.clientWidth + 'px'; g2.style.height = Math.min(fr.clientHeight, Math.round(fr.clientWidth * 1.25)) + 'px';
      g2.style.objectFit = 'cover'; g2.style.maxWidth = 'none'; g2.style.maxHeight = 'none';
    } }
  const st = document.querySelector('.meme');
  if (st && col) { const sb = st.getBoundingClientRect(), ct = col.getBoundingClientRect().top;
    if (sb.bottom > ct - 20) st.style.top = Math.max(330, parseFloat(getComputedStyle(st).top) - (sb.bottom - ct + 40)) + 'px';
    if (st.getBoundingClientRect().bottom > ct - 20) { st.style.width = '300px'; } }
  const g = document.querySelector('img.anim');
  if (!g) return null;
  const b = g.getBoundingClientRect();
  return {cx: b.left + b.width / 2, cy: b.top + b.height / 2, w: g.offsetWidth, h: g.offsetHeight,
          a: parseFloat(g.dataset.angle || '0'), r: parseFloat(getComputedStyle(g).borderTopLeftRadius) || 0,
          seq: g.dataset.seq || ''};
}"""


PREP_BOX = """() => { const g = document.querySelector('img.anim'); if (!g) return null;
  const b = g.getBoundingClientRect();
  return {cx: b.left + b.width / 2, cy: b.top + b.height / 2, w: g.offsetWidth, h: g.offsetHeight,
          a: parseFloat(g.dataset.angle || '0'), r: parseFloat(getComputedStyle(g).borderTopLeftRadius) || 0}; }"""


def place_sticker(pg):
    """Pose le sticker là où il gêne le moins : zone la plus calme de l'image (peu de détails),
    jamais sur le titre ni le texte, et en débord du panneau image quand il y en a un."""
    import io
    from PIL import Image, ImageFilter
    info = pg.evaluate("""() => { const m = document.querySelector('.meme'); m.style.visibility = 'hidden';
      const c = document.querySelector('.col').getBoundingClientRect();
      const f = document.querySelector('body.carte .frame img');
      const fr = f ? f.getBoundingClientRect() : null;
      return {w: m.offsetWidth, h: m.offsetHeight, colTop: c.top,
              frame: fr ? [fr.left, fr.top, fr.right, fr.bottom] : null}; }""")
    shot = Image.open(io.BytesIO(pg.screenshot())).convert("L").resize((270, 480))
    edges = shot.filter(ImageFilter.FIND_EDGES).load()
    k = 4   # échelle 1080 → 270
    w, h = info["w"], info["h"]
    best = None
    for y in range(330, int(info["colTop"] - h - 20) + 1, 30):
        for x in range(30, 1080 - w - 30 + 1, 30):
            tot = 0; n = 0
            for yy in range(y // k, (y + h) // k, 2):
                for xx in range(x // k, (x + w) // k, 2):
                    tot += edges[xx, yy]; n += 1
            score = tot / max(1, n)
            fr = info["frame"]
            if fr:   # dans un panneau image : on préfère déborder sur le bord plutôt que couvrir l'image
                ix = max(0, min(x + w, fr[2]) - max(x, fr[0])); iy = max(0, min(y + h, fr[3]) - max(y, fr[1]))
                inside = ix * iy / (w * h)
                score += 40 * max(0, inside - 0.45)
            if best is None or score < best[0]:
                best = (score, x, y)
    if best is None:   # pas la place au-dessus du texte : sticker plus petit, en haut à droite
        pg.evaluate("() => { const m = document.querySelector('.meme'); m.style.width = '280px'; m.style.top = '330px'; m.style.right = '40px'; m.style.visibility = 'visible'; }")
        return
    _, x, y = best
    pg.evaluate(f"() => {{ const m = document.querySelector('.meme'); m.style.right = 'auto'; m.style.left = '{x}px'; m.style.top = '{y}px';"
                f" m.style.transform = 'rotate({6 if x > 400 else -6}deg)'; m.style.visibility = 'visible';"
                f" const g = m.querySelector('img'); if (g) g.dataset.angle = '{6 if x > 400 else -6}'; }}")


def court(t, lim=200):
    """Texte TikTok lisible : garde les premières phrases entières jusqu'à ~lim caractères."""
    if len(t) <= lim + 20:
        return t
    out = ""
    for ph in re.split(r"(?<=[.!?])\s+", t):
        if out and len(out) + len(ph) + 1 > lim:
            break
        out = (out + " " + ph).strip()
    return out


def tiles(t):
    out = []
    for part in re.split(r"(\[\[.+?\]\])", t):
        y = part.startswith("[[")
        for w in part.strip("[]").split():
            out.append(f'<span class="w{" y" if y else ""}">{html.escape(w)}</span>')
    return "".join(out)


def plain(t):
    return re.sub(r"\[\[|\]\]", "", t)


def fetch(url, dest_stem, sticker=False):
    """Télécharge un mème ; renvoie (data_uri, chemin_local, est_gif)."""
    url = R.resolve_meme(url, sticker)
    if not url:
        return None, None, False
    try:
        r = R.get(url); b = r.read(15_000_000)
        ct = r.headers.get_content_type()
        gif = ct == "image/gif" or b[:6] in (b"GIF87a", b"GIF89a") or (b[:4] == b"RIFF" and b"ANIM" in b[:64])
        if not ct.startswith("image/"):
            ct = "image/gif" if gif else "image/jpeg"
        path = Path(f"{dest_stem}.{'gif' if gif else 'img'}"); path.write_bytes(b)
        return f"data:{ct};base64,{base64.b64encode(b).decode()}", path, gif
    except Exception as e:
        print("mème KO", url, e)
        return None, None, False


_SESSION = {}

def sticker(raw, dest):
    """Détoure un mème (GIF ou image) : fond supprimé, contour blanc façon sticker.
    Renvoie (data_uri de la 1re image, dossier des PNG pour la vidéo, images/seconde ou 0) ou None."""
    try:
        import io
        from PIL import Image, ImageSequence, ImageFilter
        from rembg import remove, new_session
        im = Image.open(io.BytesIO(raw))
        n = getattr(im, "n_frames", 1); step = max(1, math.ceil(n / 24))
        dur = (im.info.get("duration") or 80) * step
        dest.mkdir(parents=True, exist_ok=True)
        frames = []
        f0 = im.convert("RGBA"); hist = f0.split()[3].histogram()
        deja = sum(hist[:250]) > 0.08 * sum(hist)   # déjà détouré (sticker transparent) : pas besoin de supprimer le fond
        if not deja and "s" not in _SESSION:
            _SESSION["s"] = new_session("isnet-general-use")
        for k, f in enumerate(ImageSequence.Iterator(im)):
            if k % step: continue
            f = f.convert("RGBA"); f.thumbnail((440, 440))
            o = f if deja else remove(f.convert("RGB"), session=_SESSION["s"])
            a = o.split()[3].point(lambda v: 255 if v > 110 else 0)
            cov = sum(a.histogram()[255:]) / (a.size[0] * a.size[1])
            if a.getbbox() is None or (k == 0 and not deja and not 0.12 < cov < 0.97):
                print("détourage raté, sticker arrondi à la place"); return None
            pad = 14; W, H = o.size
            can = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), (0, 0, 0, 0))
            can.paste(Image.new("RGBA", (W, H), (255, 255, 255, 255)), (pad, pad), a.filter(ImageFilter.MaxFilter(19)))
            o = o.copy(); o.putalpha(a); can.paste(o, (pad, pad), o)
            frames.append(can)
        for k, f in enumerate(frames):
            f.save(dest / f"{k:03d}.png")
        b = io.BytesIO(); frames[0].save(b, "PNG")
        fps = max(1, round(1000 / dur)) if len(frames) > 1 else 0
        return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode(), dest, fps
    except Exception as e:
        print("sticker KO", e)
        return None


def dims(uri):
    try:
        import io
        from PIL import Image
        return Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).size
    except Exception:
        return (0, 0)


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
    tz = data.get("teaser")
    if tz in idx and len(idx) > 2:   # la news teasée en couverture passe en avant-dernière position
        idx = [i for i in idx if i != tz]; idx.insert(len(idx) - 1, tz)
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
        if not img:   # jamais de slide sans image : illustration trouvée à partir du sujet, puis capture de la page
            img = R.search_image(it.get("recherche_image") or plain(it.get("titre_tiktok") or it["titre"]))
        w, h = dims(img) if img else (0, 0)
        if not img or w < 500:
            # image absente ou minuscule : on cherche une vraie image verticale sur le sujet
            alt = R.search_image(it.get("recherche_image") or plain(it.get("titre_tiktok") or it["titre"]), tall=True)
            if alt:
                img = alt; it["cadrage"] = it.get("cadrage") or "plein"
        if not img and it.get("lien"):
            img = R.screenshot(it["lien"])
        imgs.append(img)
    cov = None
    if tz in idx:
        cov = imgs[idx.index(tz)]
    cov = cov or (R.image_for({"image": data.get("image_couverture")}) if data.get("image_couverture") else None)
    cov = cov or next((x for x in imgs if x), None)

    slides = []   # (html, durée, cadrage, gif local ou None)
    hook = data.get("couverture_tiktok") or f"Les {n} news IA [[à ne pas rater]]"
    slides.append((page(bg(cov) + CORN + top(data["date"]) +
        f'<div class=col><div class=h data-max=640 style="font-size:170px">{tiles(hook)}</div>'
        f'<p>La réponse, et {n - 1} autres news IA, tech et design, dans ce carrousel.</p><div class=swipe>SWIPE →</div></div>'),
        DUR["cover"], "plein", None))

    memes = {m.get("apres"): m for m in data.get("memes", [])}
    for i, (it, img) in enumerate(zip(sel, imgs), 1):
        uri, gpath, gif = fetch(it.get("meme"), tmp / f"m{i}", sticker=True)
        stk = ""; anim = None
        if uri:
            cut = sticker(gpath.read_bytes(), tmp / f"seq{i}")
            if cut:
                uri, seqdir, fps = cut
                stk = f'<div class=meme><img class="{"anim" if fps else ""}" data-angle=6 src="{uri}"></div>'
                anim = (seqdir, fps) if fps else None
            else:
                stk = f'<div class=meme><img class="rond {"anim" if gif else ""}" data-angle=6 src="{uri}"></div>'
                anim = gpath if gif else None
        txt = (it.get("texte_tiktok") or it["texte"]).strip()
        if it.get("bemol"):
            txt += " " + it["bemol"].strip()
        txt = court(txt)
        ou = it.get("ou")
        slides.append((page(bg(img) + CORN + top(f"{i:02d}/{n:02d}") + stk +
            f'<div class=col><div class=h data-max=340>{tiles(it.get("titre_tiktok") or it["titre"])}</div>'
            f'<p class=t>{html.escape(txt)}</p>'
            + (f'<div class=ou>→ {html.escape(ou)}</div>' if ou else "") + '</div>'),
            DUR["news"], it.get("cadrage") or "auto", anim))
        m = memes.get(i)
        if m:
            uri, gpath, gif = fetch(m.get("image"), tmp / f"full{i}")
            if uri:
                slides.append((page(
                    '<div class=noimg style="background:#0A0A0A"></div>' +
                    f'<div class=col style="bottom:auto;top:330px"><div class=h data-max=280 style="font-size:120px">{tiles(m.get("legende", ""))}</div></div>'
                    f'<div class=mfull><img class="{"anim" if gif else ""}" data-angle=0 src="{uri}"></div>'),
                    DUR["meme"], "plein", gpath if gif else None))
    slides.append((page(
        '<div class=noimg style="background:radial-gradient(900px 800px at 50% 30%,#2a2a2a,#000 70%)"></div>' + CORN + top("FIN") +
        f'<div class=col style="bottom:auto;top:400px"><div class=h data-max=720 style="font-size:180px">{tiles("[[Abonne-toi]] pour ta veille IA chaque matin")}</div>'
        f'<p>Les sources de chaque news sont dans la description.</p></div>'), DUR["end"], "plein", None))

    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    segs = []
    for k, (h, dur, mode, gpath) in enumerate(slides):
        pg.set_content(h); pg.wait_for_timeout(250)
        box = pg.evaluate(PREP, mode)
        if pg.query_selector(".meme"):
            place_sticker(pg)
            box = pg.evaluate(PREP_BOX)
        png = out / f"{k:02d}.png"; pg.screenshot(path=str(png))
        segs.append((png, dur, gpath, box))
    b.close(); pw.stop()

    # Vidéo : chaque slide tient quelques secondes ; les GIF sont rejoués par-dessus (même taille, même angle).
    try:
        parts = []
        for k, (png, dur, gpath, box) in enumerate(segs):
            seg = tmp / f"s{k:02d}.mp4"
            enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-r", "30", "-t", str(dur)]
            if isinstance(gpath, tuple) and box:   # sticker détouré : suite d'images PNG avec transparence
                seqdir, fps = gpath
                a = math.radians(box["a"]); w, hh = round(box["w"]), round(box["h"])
                rw = w * abs(math.cos(a)) + hh * abs(math.sin(a)); rh = w * abs(math.sin(a)) + hh * abs(math.cos(a))
                x, y = round(box["cx"] - rw / 2), round(box["cy"] - rh / 2)
                fc = (f"[1:v]scale={w}:{hh},format=rgba,rotate={a}:c=none:ow=rotw({a}):oh=roth({a})[m];"
                      f"[0:v][m]overlay={x}:{y}:shortest=0,format=yuv420p")
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
                       "-stream_loop", "-1", "-framerate", str(fps), "-i", str(Path(seqdir) / "%03d.png"),
                       "-filter_complex", fc] + enc + [str(seg)]
            elif gpath and box:
                a = math.radians(box["a"]); w, hh = round(box["w"]), round(box["h"])
                rw = w * abs(math.cos(a)) + hh * abs(math.sin(a)); rh = w * abs(math.sin(a)) + hh * abs(math.cos(a))
                x, y = round(box["cx"] - rw / 2), round(box["cy"] - rh / 2)
                mask = tmp / f"mask{k}.png"   # coins arrondis, comme dans la slide
                rad = box.get("r", 0)
                from PIL import Image, ImageDraw
                mk = Image.new("L", (w, hh), 0); ImageDraw.Draw(mk).rounded_rectangle((0, 0, w - 1, hh - 1), radius=rad, fill=255); mk.save(mask)
                fc = (f"[1:v]scale={w}:{hh},format=rgba[g];[2:v]scale={w}:{hh},format=gray[k];[g][k]alphamerge,"
                      f"rotate={a}:c=none:ow=rotw({a}):oh=roth({a})[m];"
                      f"[0:v][m]overlay={x}:{y}:shortest=0,format=yuv420p")
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
                       "-ignore_loop", "0", "-i", str(gpath), "-loop", "1", "-i", str(mask), "-filter_complex", fc] + enc + [str(seg)]
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
        lines.append(f"{i}. {plain(it.get('titre_tiktok') or it['titre'])} — {it.get('lien', '')}"
                     + (f"\n   👉 Où le trouver : {it['ou']}" if it.get("ou") else ""))
    lines += ["", "#ia #intelligenceartificielle #veilleia #chatgpt #claude #design #techtok"]
    (out / "legende_tiktok.txt").write_text("\n".join(lines))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{len(segs)} slides TikTok dans {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
