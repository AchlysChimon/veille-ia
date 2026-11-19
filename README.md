# Veille IA quotidienne

Chaque matin à 8h, une routine Claude dépose `news/AAAA-MM-JJ/news.json` + `message.md`.
Le push déclenche `.github/workflows/discord.yml`, qui :
1. récupère les vraies images des sources (champ `image`, sinon l'og:image de `lien`),
2. fabrique le carrousel 1080×1350 avec `render.py`,
3. poste les visuels puis le message des sources sur Discord (secret `DISCORD_WEBHOOK_URL`).

Relancer un envoi à la main : onglet Actions → « Envoi Discord » → Run workflow.

## TikTok de l'après-midi
La veille du matin choisit aussi, dans `news.json`, une 2e série de news (`tiktok_aprem`, `couverture_tiktok_aprem`, `teaser_aprem`).
Chaque jour à 17 h (heure de Paris), `.github/workflows/tiktok_aprem.yml` fabrique ce 2e TikTok avec `tiktok_aprem.py` + `render_tiktok.py`
et l'envoie sur Discord pour validation (slides, vidéo, légende). Relance à la main : Actions → « TikTok de l'après-midi » → Run workflow.
