#!/bin/bash
# Met à jour la branche « partage » (GitHub Pages) avec le TikTok du jour, puis affiche le lien de la page.
# Usage : .github/partage.sh AAAA-MM-JJ matin|aprem dossier_tiktok
set -e
date=$1; moment=$2; src=$3
site=$(mktemp -d)
git config user.name "github-actions"; git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
if git fetch -q origin partage 2>/dev/null; then git worktree add -q "$site" origin/partage; else git worktree add -q --detach "$site"; (cd "$site" && git rm -rqf . >/dev/null 2>&1 || true); fi
python3 partage.py "$site" "$date" "$moment" "$src" >&2
cd "$site"
b="partage-$$"; git checkout -q --orphan "$b"
git add -A && git commit -qm "Partage TikTok $date $moment" && git push -qf origin HEAD:partage
git checkout -q --detach && git branch -qD "$b"
owner=$(echo "$GITHUB_REPOSITORY" | cut -d/ -f1 | tr 'A-Z' 'a-z'); repo=$(echo "$GITHUB_REPOSITORY" | cut -d/ -f2)
echo "https://${owner}.github.io/${repo}/${date}/${moment}/"
