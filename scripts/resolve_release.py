#!/usr/bin/env python3
"""Resolve the newest upstream release (including prereleases) and pick an APK asset."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def api(url: str, token: str | None):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "sysapp-replacer")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--asset-hint", default="", help="substring the asset name should contain")
    ap.add_argument("--prefix", required=True, help="prefix for our release tag, e.g. appharbor")
    ap.add_argument("--out", default="", help="write key=value lines to this file (GITHUB_OUTPUT)")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    releases = api(f"https://api.github.com/repos/{args.repo}/releases?per_page=30", token)
    if isinstance(releases, dict):
        sys.exit(f"API error: {releases.get('message')}")

    candidates = [r for r in releases if not r.get("draft")]
    if not candidates:
        sys.exit("no releases found")
    # GitHub returns newest first, but sort defensively
    candidates.sort(key=lambda r: r.get("published_at") or r.get("created_at") or "", reverse=True)
    rel = candidates[0]

    assets = [a for a in rel.get("assets", []) if a["name"].lower().endswith(".apk")]
    if not assets:
        sys.exit(f"release {rel['tag_name']} has no .apk asset")

    picked = None
    if args.asset_hint:
        hint = args.asset_hint.lower()
        for a in assets:
            if hint in a["name"].lower():
                picked = a
                break
    if picked is None:
        # prefer arm64 / universal-ish builds, then just take the first
        for a in assets:
            name = a["name"].lower()
            if "arm64" in name or "universal" in name:
                picked = a
                break
    if picked is None:
        picked = assets[0]

    tag = rel["tag_name"]
    values = {
        "tag": tag,
        "name": rel.get("name") or tag,
        "prerelease": str(bool(rel.get("prerelease"))).lower(),
        "published_at": rel.get("published_at") or "",
        "asset_name": picked["name"],
        "asset_url": picked["browser_download_url"],
        "asset_size": str(picked["size"]),
        "release_tag": f"{args.prefix}-{tag}",
    }
    for k, v in values.items():
        print(f"{k}={v}")
    if args.out:
        with open(args.out, "a", encoding="utf-8") as fh:
            for k, v in values.items():
                fh.write(f"{k}={v}\n")


if __name__ == "__main__":
    main()
