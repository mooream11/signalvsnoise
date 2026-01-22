#!/usr/bin/env bash
set -e

if [ -z "$TOPIC" ]; then
  echo "Error: set TOPIC env var"
  exit 1
fi

echo "▶ Generating article: $TOPIC"
python3 generate_post.py

echo "▶ Committing source"
git add .
git commit -m "Add article: $TOPIC" || true
git push

echo "▶ Building site"
hugo

echo "▶ Ensuring CNAME"
echo "signalvsnoise.to" > public/CNAME
touch public/.nojekyll

echo "▶ Publishing to gh-pages"
cd public
git add .
git commit -m "Publish site" || true
git push -f origin gh-pages
cd ..

echo "✅ Done. Site updated."
