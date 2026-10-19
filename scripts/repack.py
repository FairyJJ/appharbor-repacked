#!/usr/bin/env python3
"""
Repack an upstream APK so it can squat on a system package name.

Steps:
  1. apktool d  -> work/src
  2. text replace  old.dot -> new.dot   and   old/slash -> new/slash
  3. optionally move the smali class tree
  4. optionally rename Compose Multiplatform resource dirs in assets/
  5. force versionCode in apktool.yml
  6. rm -rf work/src/build   (apktool caches manifest+resources; without this
                              the new versionCode is silently NOT written)
  7. apktool b
  8. verify with aapt (falls back to a second apktool pass)
  9. uber-apk-signer
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TEXT_SUFFIXES = {".smali", ".xml", ".yml", ".yaml", ".json", ".txt", ".prop"}


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.exit(f"command failed ({r.returncode}): {' '.join(str(c) for c in cmd)}")
    return r


def replace_in_tree(root: Path, old_dot: str, new_dot: str) -> int:
    old_slash = old_dot.replace(".", "/")
    new_slash = new_dot.replace(".", "/")
    changed = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # apktool keeps the pristine manifest here; never touch it
        if "original" in p.parts:
            continue
        if p.suffix not in TEXT_SUFFIXES and p.suffix != "":
            continue
        try:
            s = p.read_text("utf-8", errors="surrogateescape")
        except (OSError, UnicodeError):
            continue
        if old_dot not in s and old_slash not in s:
            continue
        s = s.replace(old_dot, new_dot).replace(old_slash, new_slash)
        p.write_text(s, "utf-8", errors="surrogateescape")
        changed += 1
    return changed


def move_classes(root: Path, old_dot: str, new_dot: str) -> bool:
    """Only needed when applicationId == code package name."""
    moved = False
    for smali_dir in sorted(root.glob("smali*")):
        if not smali_dir.is_dir():
            continue
        src = smali_dir.joinpath(*old_dot.split("."))
        if not src.is_dir():
            continue
        dst = smali_dir.joinpath(*new_dot.split("."))
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # merge
            for f in src.rglob("*"):
                rel = f.relative_to(src)
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(target))
            shutil.rmtree(src)
        else:
            shutil.move(str(src), str(dst))
        # prune empty parents
        parent = src.parent
        while parent != smali_dir and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
        moved = True
        print(f"  moved classes: {src} -> {dst}")
    return moved


def rename_assets(root: Path, old_dot: str, new_dot: str) -> bool:
    """Compose Multiplatform stores resources at assets/composeResources/<pkg>.resources."""
    done = False
    base = root / "assets" / "composeResources"
    if base.is_dir():
        old = base / f"{old_dot}.resources"
        if old.exists():
            new = base / f"{new_dot}.resources"
            if new.exists():
                shutil.rmtree(new)
            shutil.move(str(old), str(new))
            print(f"  renamed assets: {old.name} -> {new.name}")
            done = True
    # catch any leftover filesystem path in assets
    for p in root.rglob(f"*{old_dot}*"):
        if p.name.endswith(".resources"):
            p.rename(p.with_name(p.name.replace(old_dot, new_dot)))
            print(f"  renamed resource dir: {p.name}")
            done = True
    return done


def set_version_code(root: Path, version_code: int):
    yml = root / "apktool.yml"
    s = yml.read_text()
    s2, n = re.subn(r"^(\s*versionCode:\s*).*$", rf"\g<1>{version_code}", s, count=1, flags=re.M)
    if n == 0:
        sys.exit("apktool.yml has no versionCode field")
    yml.write_text(s2)
    print(f"  versionCode -> {version_code}")


def verify(apk: Path, want_pkg: str, want_vc: int, apktool_jar: Path):
    aapt = shutil.which("aapt")
    if aapt:
        out = subprocess.run([aapt, "dump", "badging", str(apk)],
                             capture_output=True, text=True).stdout
        first = out.splitlines()[0] if out else ""
        m = re.search(r"package: name='([^']+)' versionCode='(\d+)'", first)
        if m:
            pkg, vc = m.group(1), int(m.group(2))
            print(f"  verify(aapt): {pkg} / {vc}")
            if pkg != want_pkg or vc != want_vc:
                sys.exit(f"verify FAILED: got {pkg}/{vc}, want {want_pkg}/{want_vc}")
            return
        print("  verify: aapt output unparsable, falling back")
    # fallback: cheap re-dump of the manifest only
    with tempfile.TemporaryDirectory() as td:
        run(["java", "-jar", str(apktool_jar), "d", "-f", "-s", "-o", td, str(apk)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        yml = Path(td) / "apktool.yml"
        s = yml.read_text()
        m = re.search(r"versionCode:\s*(\d+)", s)
        vc = int(m.group(1)) if m else -1
        pkg = re.search(r"renameManifestPackage|^package:", s, re.M)
        print(f"  verify(apktool): versionCode={vc}")
        if vc != want_vc:
            sys.exit(f"verify FAILED: got versionCode {vc}, want {want_vc}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--version-code", type=int, default=99999999)
    ap.add_argument("--move-classes", action="store_true")
    ap.add_argument("--rename-assets", action="store_true")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--apktool", default=os.environ.get("APKTOOL_JAR", "apktool.jar"))
    ap.add_argument("--signer", default=os.environ.get("SIGNER_JAR", "uber-apk-signer.jar"))
    ap.add_argument("--keep-work", action="store_true")
    args = ap.parse_args()

    apk = Path(args.apk).resolve()
    apktool = Path(args.apktool).resolve()
    signer = Path(args.signer).resolve()
    if not apk.is_file():
        sys.exit(f"no such apk: {apk}")
    if not apktool.is_file():
        sys.exit(f"no such apktool jar: {apktool}")
    if not signer.is_file():
        sys.exit(f"no such signer jar: {signer}")

    work = Path(tempfile.mkdtemp(prefix="repack-"))
    src = work / "src"
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    print(f"== decode {apk.name}")
    run(["java", "-jar", str(apktool), "d", "-f", "-o", str(src), str(apk)])

    print(f"== replace {args.old} -> {args.new}")
    n = replace_in_tree(src, args.old, args.new)
    print(f"  rewritten files: {n}")

    if args.move_classes:
        move_classes(src, args.old, args.new)
    if args.rename_assets:
        rename_assets(src, args.old, args.new)

    set_version_code(src, args.version_code)

    # apktool caches the compiled manifest; without this the versionCode is dropped
    build_cache = src / "build"
    if build_cache.is_dir():
        shutil.rmtree(build_cache)
        print("  cleared apktool build cache")

    unsigned = work / "unsigned.apk"
    print("== build")
    run(["java", "-jar", str(apktool), "b", str(src), "-o", str(unsigned)])

    print("== verify")
    verify(unsigned, args.new, args.version_code, apktool)

    print("== sign")
    signed_dir = work / "signed"
    signed_dir.mkdir()
    run(["java", "-jar", str(signer), "-a", str(unsigned), "-o", str(signed_dir), "--allowResign"])

    produced = sorted(signed_dir.glob("*aligned-debugSigned.apk"))
    if not produced:
        produced = sorted(signed_dir.glob("*.apk"))
    if not produced:
        sys.exit("signer produced nothing")
    final = out / produced[0].name
    shutil.copy2(produced[0], final)
    print(f"== done: {final} ({final.stat().st_size} bytes)")

    if not args.keep_work:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
