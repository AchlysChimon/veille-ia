#!/usr/bin/env python3
"""Page de partage TikTok (GitHub Pages, branche « partage ») : sur le téléphone, 1 bouton copie la légende,
1 bouton envoie toutes les photos (ou la vidéo) d'un coup vers l'appli TikTok via le menu Partager.

Usage : python3 partage.py dossier_site AAAA-MM-JJ matin|aprem dossier_tiktok
Copie les slides, la vidéo et la légende dans dossier_site/AAAA-MM-JJ/<moment>/, garde les 3 derniers jours,
et régénère les pages (index.html = le plus récent).
"""
import html, json, shutil, sys
from pathlib import Path

site, date, moment, src = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
dest = site / date / moment
if dest.exists():
    shutil.rmtree(dest)
dest.mkdir(parents=True)
for f in sorted(src.glob("*.png")) + [src / "flash_ia.mp4", src / "legende_tiktok.txt"]:
    if f.exists():
        shutil.copy(f, dest / f.name)

for old in sorted(p for p in site.iterdir() if p.is_dir() and p.name[:2] == "20")[:-3]:   # 3 derniers jours
    shutil.rmtree(old)

NOMS = {"matin": "du matin", "aprem": "de l'après-midi"}
LAB = {"matin": "matin", "aprem": "17 h"}
PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>FLASH IA · %(titre)s</title>
<style>
body{margin:0;background:#0b0b0b;color:#fff;font:16px/1.4 system-ui,sans-serif;padding:16px;max-width:640px;margin:auto}
h1{font-size:22px;margin:4px 0 2px}.sub{color:#aaa;margin:0 0 14px}
nav a{color:#FFE600;margin-right:12px}
button{display:block;width:100%%;margin:10px 0;padding:16px;border:0;border-radius:12px;font:700 18px system-ui;background:#FFE600;color:#000}
button.sec{background:#222;color:#fff}
.ok{color:#7CFC9A;min-height:1.4em;margin:4px 0}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:14px}.grid img{width:100%%;border-radius:8px}
pre{white-space:pre-wrap;background:#161616;padding:12px;border-radius:10px;font-size:13px;color:#ddd}
</style></head><body>
<nav>%(nav)s</nav>
<h1>FLASH IA %(moment)s</h1><p class="sub">%(date)s · %(n)d slides</p>
<button onclick="copier()">1. Copier la légende</button>
<button onclick="partager('photos')">2. Envoyer les %(n)d photos vers TikTok</button>
<button class="sec" onclick="partager('video')">ou envoyer la vidéo</button>
<button class="sec" onclick="telecharger()">Tout télécharger</button>
<p class="ok" id="ok"></p>
<pre id="leg">%(legende)s</pre>
<div class="grid">%(imgs)s</div>
<script>
const PNG=%(pngs)s, VIDEO=%(video)s;
const ok=t=>document.getElementById('ok').textContent=t;
async function copier(){const t=document.getElementById('leg').textContent;
  try{await navigator.clipboard.writeText(t);ok('Légende copiée ✅ Colle-la dans TikTok.')}
  catch(e){const r=document.createRange();r.selectNode(document.getElementById('leg'));getSelection().removeAllRanges();getSelection().addRange(r);ok('Sélectionnée : appuie sur Copier.')}}
async function fichiers(noms,type){return Promise.all(noms.map(async n=>new File([await (await fetch(n)).blob()],n,{type})))}
async function partager(q){try{ok('Préparation…');
  const f=q==='video'?await fichiers([VIDEO],'video/mp4'):await fichiers(PNG,'image/png');
  if(!navigator.canShare||!navigator.canShare({files:f})){ok('Partage impossible ici : ouvre la page sur ton téléphone, ou utilise « Tout télécharger ».');return}
  await navigator.share({files:f});ok('Choisis TikTok dans le menu, puis colle la légende.')}catch(e){ok(e.name==='AbortError'?'':'Oups : '+e.message)}}
async function telecharger(){for(const n of [...PNG,VIDEO]){const a=document.createElement('a');a.href=n;a.download=n.split('/').pop();document.body.appendChild(a);a.click();a.remove();await new Promise(r=>setTimeout(r,400))}}
</script></body></html>"""

pages = []   # (chemin relatif, libellé)
for d in sorted((p for p in site.iterdir() if p.is_dir() and p.name[:2] == "20"), reverse=True):
    for m in ("aprem", "matin"):
        if (d / m).is_dir():
            pages.append((d, m))
for d, m in pages:
    rel = f"{d.name}/{m}/"
    pngs = sorted(p.name for p in (d / m).glob("*.png"))
    leg = (d / m / "legende_tiktok.txt").read_text(encoding="utf-8") if (d / m / "legende_tiktok.txt").exists() else ""
    nav = " ".join(f'<a href="../../{x.name}/{y}/">{x.name[8:]}/{x.name[5:7]} {LAB[y]}</a>' for x, y in pages)
    (d / m / "index.html").write_text(PAGE % {
        "titre": f"{d.name} {m}", "moment": NOMS[m], "date": d.name, "n": len(pngs), "nav": nav,
        "legende": html.escape(leg), "imgs": "".join(f'<img src="{p}" loading="lazy">' for p in pngs),
        "pngs": json.dumps(pngs), "video": json.dumps("flash_ia.mp4")}, encoding="utf-8")
if pages:
    d, m = pages[0]
    (site / "index.html").write_text(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={d.name}/{m}/">'
                                     f'<a href="{d.name}/{m}/">Dernier FLASH IA</a>', encoding="utf-8")
(site / ".nojekyll").write_text("")
print("Page de partage :", f"{date}/{moment}/")
