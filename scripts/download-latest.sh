#!/usr/bin/env bash
# Download the newest repacked AppHarbor APK from this repo's public releases.
# Pure download — never touches adb, never installs anything.
#
#   ./scripts/download-latest.sh
#   OUT=/tmp/apk ./scripts/download-latest.sh
set -euo pipefail

REPO="${REPO:-FairyJJ/appharbor-repacked}"
APP="appharbor"
OUT="${OUT:-./dist}"
mkdir -p "$OUT"

info=$(curl -fsSL -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/$REPO/releases?per_page=50" \
| python3 -c '
import json,sys
app=sys.argv[1]
rels=[r for r in json.load(sys.stdin) if not r.get("draft") and r["tag_name"].startswith(app+"-")]
rels.sort(key=lambda r: r.get("published_at") or "", reverse=True)
if not rels: sys.exit(1)
r=rels[0]
apk=[a for a in r["assets"] if a["name"].endswith(".apk")][0]
print(r["tag_name"]); print(apk["name"]); print(apk["browser_download_url"])
' "$APP") || { echo "no release yet" >&2; exit 1; }

tag=$(echo "$info" | sed -n 1p)
name=$(echo "$info" | sed -n 2p)
url=$(echo "$info" | sed -n 3p)
dest="$OUT/$name"

echo "== $tag"
curl -fsSL --retry 3 -o "$dest" "$url"
echo "   -> $dest  ($(stat -c%s "$dest") bytes)"
echo "   install: adb install -r -t \"$dest\""
