#!/usr/bin/env python3
"""Checks every listing file in this repo, and the copies the site serves, before anything is published.

    python3 scripts/check.py                    this repo, plus ../loomdesk.trade/web when it is there
    python3 scripts/check.py --site PATH/web    the site's public/ files at PATH
    python3 scripts/check.py --live             also asks the registry to validate server.json (mcp-publisher
                                                validate, nothing is published) and checks the live endpoint

Errors exit 1. Warnings (placeholders the operator still has to fill) do not: they say the repo is not ready to be
made public yet. The JSON schemas are fetched from where their owners publish them and cached in .cache/.
Needs python3 with jsonschema and PyYAML.
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import urllib.request
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "schemas"
ENDPOINT = "https://loomdesk.trade/mcp"
UA = "Mozilla/5.0 (X11; Linux x86_64) loomdesk-mcp-check"
SCHEMAS = {
    "server": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
    # not served from static.modelcontextprotocol.io yet; the extension repo is where it lives
    "card": "https://raw.githubusercontent.com/modelcontextprotocol/ext-server-card/main/schema.json",
    "ap-plugin": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
    "ap-mcp": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
}
# The one place an emoji is allowed: the awesome list's own auth legend, which an entry must use.
EMOJI_OK = {"listings/awesome-remote-mcp-servers.md": {"\U0001F513", "\U0001F511"}}
TEXT = (".md", ".json", ".txt", ".yaml", ".yml", ".sh", ".py")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"user-agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def schema(name: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{name}.json"
    if not p.exists():
        p.write_bytes(get(SCHEMAS[name]))
    return json.loads(p.read_text())


def load(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        err(f"{rel(path)}: missing")
    except json.JSONDecodeError as e:
        err(f"{rel(path)}: not JSON ({e})")
    return None


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def validate(doc, sch: dict, where: str, cls=None) -> None:
    cls = cls or jsonschema.validators.validator_for(sch)
    for e in sorted(cls(sch).iter_errors(doc), key=lambda e: list(e.path)):
        err(f"{where}: {'/'.join(map(str, e.path)) or '(root)'}: {e.message}")


def check_server(path: Path) -> dict | None:
    d = load(path)
    if d is None:
        return None
    validate(d, schema("server"), rel(path))
    desc = d.get("description", "")
    if len(desc) > 100:
        err(f"{rel(path)}: description is {len(desc)} characters, the registry takes 100")
    if not re.fullmatch(r"\d+\.\d+\.\d+", d.get("version", "")):
        err(f"{rel(path)}: version {d.get('version')!r} is not plain semver")
    if [r.get("url") for r in d.get("remotes", [])] != [ENDPOINT]:
        err(f"{rel(path)}: remotes should be exactly {ENDPOINT}")
    return d


def png_size(path: Path) -> tuple[int, int] | None:
    b = path.read_bytes()[:24]
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", b[16:24])


def skill_body(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def tools_named(text: str) -> set[str]:
    return set(re.findall(r"`((?:market|ladder|plan|my|book|arena|agent)_[a-z_]+)`", text))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", help="the site's web/ directory (default: ../loomdesk.trade/web when it exists)")
    ap.add_argument("--live", action="store_true", help="also validate with the registry and check the live endpoint")
    args = ap.parse_args()
    site = Path(args.site) if args.site else ROOT.parent / "loomdesk.trade" / "web"
    if not (site / "public").is_dir():
        site = None

    # --- server.json: the repo's, and the copy the site serves -------------------------------------------------
    srv = check_server(ROOT / "server.json")
    version = srv.get("version") if srv else None
    if srv and "repository" not in srv:
        err("server.json: the repo's copy should carry the repository block")
    site_srv = None
    if site:
        site_srv = check_server(site / "public/.well-known/mcp/server.json")
        if srv and site_srv:
            a = {k: v for k, v in srv.items() if k != "repository"}
            b = {k: v for k, v in site_srv.items() if k != "repository"}
            if a != b:
                diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
                err(f"server.json: the site's copy differs from the repo's in {diff} (only repository may differ)")
            if "repository" in site_srv and "REPLACE" in json.dumps(site_srv["repository"]):
                err("site server.json: serves a REPLACE placeholder")

        # --- the server card and the AI catalog that points at it ---------------------------------------------
        card_path = site / "public/.well-known/mcp/server-card.json"
        card = load(card_path)
        if card is not None:
            sch = schema("card")
            validate(card, {**sch, "$ref": "#/$defs/ServerCard"}, rel(card_path), jsonschema.Draft202012Validator)
            if srv:
                for k in ("name", "title", "description", "version", "websiteUrl"):
                    if card.get(k) != srv.get(k):
                        err(f"server-card.json: {k} {card.get(k)!r} is not server.json's {srv.get(k)!r}")
                if [r.get("url") for r in card.get("remotes", [])] != [ENDPOINT]:
                    err(f"server-card.json: remotes should be exactly {ENDPOINT}")
                if card.get("serverInfo", {}).get("version") != version:
                    err("server-card.json: serverInfo.version is not the version")
                srcs = {i["src"] for i in srv.get("icons", [])}
                for i in card.get("icons", []):
                    if i.get("src") not in srcs:
                        err(f"server-card.json: icon {i.get('src')} is not one of server.json's")
        cat_path = site / "public/.well-known/ai-catalog.json"
        cat = load(cat_path)
        if cat is not None:
            if cat.get("specVersion") != "1.0" or not isinstance(cat.get("entries"), list):
                err("ai-catalog.json: needs specVersion \"1.0\" and an entries array")
            for e in cat.get("entries", []):
                if not all(isinstance(e.get(k), str) for k in ("identifier", "type")) or ("url" in e) == ("data" in e):
                    err(f"ai-catalog.json: entry {e.get('identifier')} needs identifier, type and exactly one of url, data")
                if e.get("type") == "application/mcp-server-card+json":
                    u = e.get("url", "")
                    local = site / "public" / u.removeprefix("https://loomdesk.trade/")
                    if not u.startswith("https://loomdesk.trade/") or not local.exists():
                        err(f"ai-catalog.json: {u} is not a file the site serves")
            if "displayName" not in cat.get("host", {"displayName": ""}):
                err("ai-catalog.json: host needs a displayName")

        # --- the icon every entry points at ----------------------------------------------------------------
        icon = site / "public/brand/loomdesk-icon-512.png"
        if not icon.exists():
            err(f"{icon}: missing")
        elif png_size(icon) != (512, 512):
            err(f"{icon}: is {png_size(icon)}, not a 512 x 512 PNG")
        glama = site / "public/.well-known/glama.json"
        if glama.exists() and "REPLACE" in glama.read_text():
            err("site glama.json: serves a placeholder claim token")
    else:
        warn("no site directory found: the site's server.json, server card, AI catalog and icon were not checked")

    # --- plugin manifests ------------------------------------------------------------------------------------
    for f, s in (("plugin.json", "ap-plugin"), ("mcp.json", "ap-mcp")):
        d = load(ROOT / f)
        if d is not None:
            validate(d, schema(s), f)
    ap_mcp = load(ROOT / "mcp.json") or {}
    if ap_mcp.get("mcpServers", {}).get("loomdesk", {}).get("url") != ENDPOINT:
        err(f"mcp.json: loomdesk should point at {ENDPOINT}")
    cc = load(ROOT / ".claude-plugin/plugin.json") or {}
    mk = load(ROOT / ".claude-plugin/marketplace.json") or {}
    cc_mcp = load(ROOT / ".mcp.json") or {}
    gem = load(ROOT / "gemini-extension.json") or {}
    agp = load(ROOT / "plugin.json") or {}
    for where, d in ((".claude-plugin/plugin.json", cc), ("gemini-extension.json", gem), ("plugin.json", agp)):
        if d.get("name") != "loomdesk":
            err(f"{where}: name should be loomdesk")
        if version and d.get("version") != version:
            err(f"{where}: version {d.get('version')} is not server.json's {version}")
    if [p.get("name") for p in mk.get("plugins", [])] != ["loomdesk"] or mk.get("plugins", [{}])[0].get("source") != "./":
        err(".claude-plugin/marketplace.json: should list the one plugin loomdesk at ./")
    if cc_mcp.get("mcpServers", {}).get("loomdesk", {}).get("url") != ENDPOINT:
        err(f".mcp.json: loomdesk should point at {ENDPOINT}")
    if gem.get("mcpServers", {}).get("loomdesk", {}).get("httpUrl") != ENDPOINT:
        err(f"gemini-extension.json: loomdesk httpUrl should be {ENDPOINT}")
    if not (ROOT / gem.get("contextFileName", "GEMINI.md")).exists():
        err("gemini-extension.json: its context file is missing")
    for where, d in (("plugin.json", agp), (".claude-plugin/plugin.json", cc)):
        if version and srv and srv.get("repository", {}).get("url") != d.get("repository"):
            err(f"{where}: repository is not server.json's repository url")

    # --- the skill, and GEMINI.md which is its body --------------------------------------------------------
    skill_path = ROOT / "skills/loomdesk/SKILL.md"
    front, body = skill_body(skill_path.read_text())
    if front.get("name") != "loomdesk" or not front.get("description"):
        err("SKILL.md: frontmatter needs name loomdesk and a description")
    elif len(front["description"]) > 1024:
        err("SKILL.md: description is over 1024 characters")
    if (ROOT / "GEMINI.md").read_text() != body:
        err("GEMINI.md: is not the skill's body (regenerate it from skills/loomdesk/SKILL.md)")

    # --- Docker MCP catalog ------------------------------------------------------------------------------------
    dk = ROOT / "listings/docker/servers/loomdesk"
    y = yaml.safe_load((dk / "server.yaml").read_text())
    if y.get("type") != "remote" or y.get("remote", {}).get("url") != ENDPOINT or y.get("remote", {}).get("transport_type") != "streamable-http":
        err("docker server.yaml: should be a remote streamable-http entry for the endpoint")
    if srv and y.get("about", {}).get("description") != srv.get("description"):
        err("docker server.yaml: description is not server.json's")
    if json.loads((dk / "tools.json").read_text()) != []:
        err("docker tools.json: must be [] for a remote server")
    if not re.search(r"https://\S+", (dk / "readme.md").read_text()):
        err("docker readme.md: needs the documentation link")

    # --- tool names are the same everywhere they are listed --------------------------------------------------
    named = {f: tools_named((ROOT / f).read_text()) for f in ("README.md", "listings/mcp-so-issue.md")}
    if len({frozenset(v) for v in named.values()}) != 1:
        a, b = named.values()
        err(f"tool lists differ between README.md and mcp-so-issue.md: {sorted(a ^ b)}")
    readme_tools = named["README.md"]

    # --- copy rules: no em or en dashes, no emojis (but the awesome list's legend) ---------------------------
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or ".git" in p.parts or ".cache" in p.parts or p.suffix not in TEXT:
            continue
        r = rel(p)
        t = p.read_text()
        for n, line in enumerate(t.splitlines(), 1):
            if "\u2014" in line or "\u2013" in line:
                err(f"{r}:{n}: em or en dash")
            for ch in line:
                if (0x1F000 <= ord(ch) <= 0x1FAFF or 0x2600 <= ord(ch) <= 0x27BF) and ch not in EMOJI_OK.get(r, set()):
                    err(f"{r}:{n}: emoji {ch!r}")
        for m in re.finditer(r"REPLACE\w*|TODO\(operator\)", t):
            # the publish script names REPLACE to refuse it, the Glama file is a template that stays one, SUBMIT.md tells of both
            if p.name not in ("check.py", "test_check.py") and not r.startswith(("listings/official-registry/", "listings/glama/", "listings/SUBMIT.md")):
                warn(f"{r}: placeholder {m.group(0)} (fill it before the repo is public)")

    # --- live: the registry's validation and the endpoint itself ---------------------------------------------
    if args.live:
        pub = os.environ.get("MCP_PUBLISHER") or shutil.which("mcp-publisher")
        if not pub:
            warn("--live: no mcp-publisher (set MCP_PUBLISHER), registry validation skipped")
        else:
            for f in [ROOT / "server.json"] + ([site / "public/.well-known/mcp/server.json"] if site else []):
                r = subprocess.run([pub, "validate", str(f)], capture_output=True, text=True)
                (err if r.returncode else print)(f"mcp-publisher validate {rel(f)}: {(r.stdout + r.stderr).strip().splitlines()[-1]}")
        for i in (srv or {}).get("icons", []):
            try:
                get(i["src"])
            except Exception as e:  # noqa: BLE001
                warn(f"{i['src']}: {e} (deploy it before publishing)")
        try:
            req = urllib.request.Request(ENDPOINT, method="POST", data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
                                         headers={"user-agent": UA, "content-type": "application/json", "accept": "application/json, text/event-stream"})
            with urllib.request.urlopen(req, timeout=30) as r:
                live = set(re.findall(r'"name":"([a-z_]+)"', r.read().decode()))
            missing = sorted(readme_tools - live)
            if missing:
                warn(f"tools the listings name that the live server does not have yet: {missing}")
        except Exception as e:  # noqa: BLE001
            warn(f"{ENDPOINT} tools/list: {e}")

    for w in warnings:
        print(f"warn  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"{len(errors)} errors, {len(warnings)} warnings" + ("" if errors else f" (version {version})"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
