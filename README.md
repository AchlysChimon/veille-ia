# Veille IA quotidienne

Chaque matin à 8h, une routine Claude dépose `news/AAAA-MM-JJ/news.json` + `message.md`.
Le push déclenche `.github/workflows/discord.yml`, qui :
1. récupère les vraies images des sources (champ `image`, sinon l'og:image de `lien`),
2. fabrique le carrousel 1080×1350 avec `render.py`,
3. poste les visuels puis le message des sources sur Discord (secret `DISCORD_WEBHOOK_URL`).

Relancer un envoi à la main : onglet Actions → « Envoi Discord » → Run workflow.
