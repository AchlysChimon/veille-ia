#!/usr/bin/env python3
"""Prépare le TikTok de l'après-midi à partir de la veille du matin.

Usage : python3 tiktok_aprem.py news/AAAA-MM-JJ/news.json sortie.json
puis   python3 render_tiktok.py sortie.json dossier/

Champs lus dans news.json (écrits par la veille du matin) :
  "tiktok_aprem": [4, 12, 6, ...]   indices (à partir de 1) des news de l'après-midi, différentes de "tiktok"
  "couverture_tiktok_aprem": "Une boîte d'IA vient de battre [[un record historique]]"
  "teaser_aprem": 9                 news teasée (placée en avant-dernière)
  "memes_aprem": [...]              optionnel, même format que "memes"
  Par news : "titre_tiktok", "texte_tiktok", "image_tiktok", "cadrage", "meme" servent aux deux TikTok.
             "meme_aprem" remplace "meme" l'après-midi ("" pour l'enlever).
"""
import json, sys

src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
if not d.get("tiktok_aprem"):
    sys.exit("Pas de champ tiktok_aprem dans " + src)
d["tiktok"] = d["tiktok_aprem"]
d["couverture_tiktok"] = d.get("couverture_tiktok_aprem") or d.get("couverture_tiktok", "")
d["teaser"] = d.get("teaser_aprem")
d["memes"] = d.get("memes_aprem", [])
for it in d["items"]:
    if "meme_aprem" in it:
        it["meme"] = it["meme_aprem"]
        if not it["meme"]:
            it.pop("meme")
json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("TikTok après-midi :", d["tiktok"], "teaser", d["teaser"])
