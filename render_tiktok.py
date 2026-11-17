#!/usr/bin/env python3
"""Carrousel TikTok « FLASH IA » (1080x1920) : couverture, une slide par news, slide de fin.

Usage : python3 render_tiktok.py news.json sortie/

Champs utilisés dans news.json (en plus de ceux de render.py) :
  "tiktok": [3, 1, 7, ...]        indices (à partir de 1) des news retenues pour TikTok, dans l'ordre.
                                  Absent : les 7 premières news.
  item "titre_tiktok": "Claude peint de [[vrais tableaux]]"
                                  titre court pour les tuiles ; [[...]] = tuiles jaunes. Absent : "titre".
  item "texte_tiktok": "..."      texte court (≤ 220 caractères). Absent : "texte".
  item "bemol": "Démo partagée sur X, pas encore vérifiée"   ligne d'avertissement (optionnelle).
  "couverture_tiktok": "Les news IA qui ont [[tout changé]]"  accroche de couverture (optionnelle).
"""
import html, json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import render as R   # récupération des images (og:image, capture d'écran de secours)

NAME = "FLASH IA"

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1920px;overflow:hidden;position:relative;background:#000;color:#fff;font-family:'Inter'}
.ph{position:absolute;inset:0}.ph img{width:100%;height:100%;object-fit:cover;display:block}
.noimg{position:absolute;inset:0;background:radial-gradient(900px 700px at 70% 20%,#3a3a3a,#0b0b0b 70%);display:flex;align-items:flex-start;justify-content:center;padding-top:330px}
.noimg>div{width:100%;padding:0 80px}.noimg .big{font:400 240px/0.95 'Anton';color:#FFE600;text-align:center}
.noimg .leg{font:600 40px/1.25 'Inter';color:#ddd;text-align:center;margin-top:20px;padding:0 120px}
.sh{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.45),transparent 15%,transparent 42%,rgba(0,0,0,.88) 64%,#000 86%)}
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
"""
CORN = ('<i class=c style="top:50px;left:50px;border-right:0;border-bottom:0"></i>'
        '<i class=c style="top:50px;right:50px;border-left:0;border-bottom:0"></i>'
        '<i class=c style="bottom:50px;left:50px;border-right:0;border-top:0"></i>'
        '<i class=c style="bottom:50px;right:50px;border-left:0;border-top:0"></i>')

FIT = """() => { const g=document.querySelector('.big'); if(g){ let s=240; while((g.offsetHeight>520||g.scrollWidth>g.clientWidth+2)&&s>80){s-=10;g.style.fontSize=s+'px';} } const h=document.querySelector('.h'); if(!h) return;
  const max=parseInt(h.dataset.max||'720'); let s=parseInt(getComputedStyle(h).fontSize);
  while((h.offsetHeight>max || h.scrollWidth>h.clientWidth+2) && s>70){ s-=4; h.style.fontSize=s+'px'; } }"""


def tiles(t):
    out = []
    for part in re.split(r"(\[\[.+?\]\])", t):
        y = part.startswith("[[")
        for w in part.strip("[]").split():
            out.append(f'<span class="w{" y" if y else ""}">{html.escape(w)}</span>')
    return "".join(out)


def bg(img, visuel=None):
    if img:
        return f'<div class=ph><img src="{img}"></div><div class=sh></div>'
    v = visuel or {}
    big = v.get("valeur") or (v.get("mots") or ["IA"])[0]
    return (f'<div class=noimg><div><div class=big>{html.escape(big)}</div>'
            f'<div class=leg>{html.escape(v.get("legende", ""))}</div></div></div><div class=sh></div>')


def page(body):
    return f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>{body}</body></html>"


def main(src, out):
    data = json.loads(Path(src).read_text())
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    items = data["items"]
    idx = data.get("tiktok") or list(range(1, min(7, len(items)) + 1))
    sel = [items[i - 1] for i in idx if 0 < i <= len(items)]
    n = len(sel)

    pw = sync_playwright().start(); b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 760}, user_agent=R.UA["User-Agent"], locale="fr-FR")
    R.SHOT["page"] = ctx.new_page()
    imgs = [R.image_for(it) for it in sel]
    cov = R.image_for({"image": data.get("image_couverture")}) or next((x for x in imgs if x), None)

    pages = []
    hook = data.get("couverture_tiktok") or f"Les {n} news IA [[du jour]]"
    pages.append(page(
        bg(cov) + CORN +
        f'<div class=top><span><b>●</b> REC · {NAME}</span><span>{html.escape(data["date"])}</span></div>'
        f'<div class=col><div class=h data-max=900 style="font-size:180px">{tiles(hook)}</div>'
        f'<p>IA, tech et design : l\'essentiel en {n} slides.</p></div><div class=swipe>SWIPE →</div>'))
    for i, (it, img) in enumerate(zip(sel, imgs), 1):
        bem = it.get("bemol")
        pages.append(page(
            bg(img, it.get("visuel")) + CORN +
            f'<div class=top><span><b>●</b> REC · {NAME}</span><span>{i:02d}/{n:02d}</span></div>'
            f'<div class=col><div class=h data-max=640>{tiles(it.get("titre_tiktok") or it["titre"])}</div>'
            f'<p>{html.escape(it.get("texte_tiktok") or it["texte"])}</p>'
            + (f'<div class=b>⚠ {html.escape(bem.upper())}</div>' if bem else "") + '</div>'))
    pages.append(page(
        '<div class=noimg style="background:radial-gradient(900px 800px at 50% 30%,#2a2a2a,#000 70%)"></div>' + CORN +
        f'<div class=top><span><b>●</b> REC · {NAME}</span><span>FIN</span></div>'
        f'<div class=col style="bottom:auto;top:620px"><div class=h data-max=800 style="font-size:190px">{tiles("[[Abonne-toi]] pour ta veille IA chaque matin")}</div>'
        f'<p>Les sources de chaque news sont dans la description.</p></div>'))

    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    for k, h in enumerate(pages):
        pg.set_content(h); pg.wait_for_timeout(200); pg.evaluate(FIT)
        pg.screenshot(path=str(out / f"{k:02d}.png"))
    b.close(); pw.stop()

    # Légende TikTok : accroche + sources + hashtags
    lines = [re.sub(r"\[\[|\]\]", "", hook) + " 👇", ""]
    for i, it in enumerate(sel, 1):
        t = re.sub(r"\[\[|\]\]", "", it.get("titre_tiktok") or it["titre"])
        lines.append(f"{i}. {t} — {it.get('lien', '')}")
    lines += ["", "#ia #intelligenceartificielle #veilleia #chatgpt #claude #design #techtok"]
    (out / "legende_tiktok.txt").write_text("\n".join(lines))
    print(f"{len(pages)} slides TikTok dans {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
