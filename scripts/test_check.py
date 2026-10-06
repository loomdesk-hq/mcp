#!/usr/bin/env python3
"""Proves check.py catches what it is for: each case copies this repo and the site's listing files to a scratch
directory, breaks one thing, and expects check.py to fail on it. The unbroken copy must pass.

    python3 scripts/test_check.py [--site PATH/web]
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_FILES = [".well-known/mcp/server.json", ".well-known/mcp/server-card.json", ".well-known/ai-catalog.json", "brand/loomdesk-icon-512.png"]


def edit_json(path: Path, fn) -> None:
    d = json.loads(path.read_text())
    fn(d)
    path.write_text(json.dumps(d, indent=2) + "\n")


def append(path: Path, text: str) -> None:
    path.write_text(path.read_text() + text)


CASES = {
    "description over 100 characters": lambda r, s: edit_json(r / "server.json", lambda d: d.update(description="x" * 101)),
    "site copy drifts from the repo": lambda r, s: edit_json(s / "public/.well-known/mcp/server.json", lambda d: d.update(version="2.3.1")),
    "site copy serves a placeholder": lambda r, s: edit_json(s / "public/.well-known/mcp/server.json", lambda d: d.update(repository={"url": "https://github.com/x/y", "source": "github", "id": "REPLACE"})),
    "card version is not the entry's": lambda r, s: edit_json(s / "public/.well-known/mcp/server-card.json", lambda d: d["serverInfo"].update(version="2.2.0")),
    "card breaks its schema": lambda r, s: edit_json(s / "public/.well-known/mcp/server-card.json", lambda d: d.update({"$schema": "https://example.com/card.json"})),
    "catalog points at nothing": lambda r, s: edit_json(s / "public/.well-known/ai-catalog.json", lambda d: d["entries"][0].update(url="https://loomdesk.trade/.well-known/mcp/nope.json")),
    "icon is not 512 px": lambda r, s: shutil.copy(ROOT.parent / "loomdesk.trade/web/src/app/apple-icon.png", s / "public/brand/loomdesk-icon-512.png"),
    "plugin version drifts": lambda r, s: edit_json(r / ".claude-plugin/plugin.json", lambda d: d.update(version="2.2.0")),
    "agent plugin breaks its schema": lambda r, s: edit_json(r / "plugin.json", lambda d: d.update(extra=True)),
    "gemini points elsewhere": lambda r, s: edit_json(r / "gemini-extension.json", lambda d: d["mcpServers"]["loomdesk"].update(httpUrl="https://example.com/mcp")),
    "GEMINI.md out of step with the skill": lambda r, s: append(r / "GEMINI.md", "\nmore\n"),
    "docker description drifts": lambda r, s: (r / "listings/docker/servers/loomdesk/server.yaml").write_text((r / "listings/docker/servers/loomdesk/server.yaml").read_text().replace("for agents.", "for bots.")),
    "a tool missing from one list": lambda r, s: append(r / "README.md", "\n`arena_extra`\n"),
    "an em dash in copy": lambda r, s: append(r / "README.md", "\nsay less \u2014 always\n"),
    "an emoji in copy": lambda r, s: append(r / "listings/mcp-so-issue.md", "\n\U0001F680\n"),
}


def run(repo: Path, site: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(repo / "scripts/check.py"), "--site", str(site)], capture_output=True, text=True)


def copy(tmp: Path, site_src: Path) -> tuple[Path, Path]:
    repo = tmp / "loomdesk-mcp"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git"))
    site = tmp / "web"
    for f in SITE_FILES:
        (site / "public" / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(site_src / "public" / f, site / "public" / f)
    return repo, site


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=str(ROOT.parent / "loomdesk.trade" / "web"))
    site_src = Path(ap.parse_args().site)
    failed = 0
    with tempfile.TemporaryDirectory() as t:
        repo, site = copy(Path(t) / "clean", site_src)
        r = run(repo, site)
        ok = r.returncode == 0
        failed += not ok
        print(f"{'pass' if ok else 'FAIL'}  the unbroken copy passes" + ("" if ok else "\n" + r.stdout))
        for name, breakit in CASES.items():
            repo, site = copy(Path(t) / name.replace(" ", "_"), site_src)
            breakit(repo, site)
            r = run(repo, site)
            ok = r.returncode == 1 and "ERROR" in r.stdout
            failed += not ok
            first = next((ln for ln in r.stdout.splitlines() if ln.startswith("ERROR")), r.stdout.strip()[-200:])
            print(f"{'pass' if ok else 'FAIL'}  {name}: {first}")
    print(f"{len(CASES) + 1 - failed} of {len(CASES) + 1} pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
