#!/usr/bin/env python3
"""Fabrique le message Discord (JSON) de la légende TikTok à partir de legende_tiktok.txt.
Écrit en Python pour éviter les ``` dans le shell (bash les prenait pour une commande)."""
import json, sys
t = open(sys.argv[1], encoding="utf-8").read().strip()
fence = "`" * 3
print(json.dumps({"content": "**Légende TikTok :**\n" + fence + "\n" + t[:1850] + "\n" + fence, "flags": 4}, ensure_ascii=False))
