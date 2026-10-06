#!/usr/bin/env bash
# Publish a new version of trade.loomdesk/loomdesk to the official MCP Registry (registry.modelcontextprotocol.io)
# by HTTP domain proof (https://loomdesk.trade/.well-known/mcp-registry-auth). For the operator, from a shell
# (in Claude Code: `! bash listings/official-registry/publish.sh`):
#
#   DRY_RUN=1 bash publish.sh [server.json]   every check, then stop before logging in
#   bash publish.sh [server.json]              the same checks, then log in, publish, log out
#
# The default file is the repo's server.json, which carries the repository block; it is refused while the repo id
# still says REPLACE. Before the public repo exists, publish the site's copy instead:
#   bash publish.sh ~/loomdesk.trade/web/public/.well-known/mcp/server.json
#
# A version can be published once and never changed, so everything the entry promises is checked against the live
# site first: the icons, the endpoint, serverInfo.version, and the arena tools when the description names the arena.
# Never prints the private key. Needs OpenSSL 3, curl, python3.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_JSON="${1:-$HERE/../../server.json}"
KEY="${MCP_REGISTRY_KEY:-$HOME/.config/loomdesk/mcp-registry-key.pem}"
DOMAIN="loomdesk.trade"
REGISTRY="https://registry.modelcontextprotocol.io"
PUBLISHER_VERSION="v1.8.1"
# sha256 of mcp-publisher_linux_amd64.tar.gz in that release (the asset digest GitHub lists for it)
PUBLISHER_SHA256="a06c9096dcb9727c13555b6be26c7effa707b01f06a4c561ba7a3635443cf2cc"
# Cloudflare refuses Python-urllib; any ordinary agent string gets through
UA="Mozilla/5.0 (X11; Linux x86_64) loomdesk-publish"
BIN_DIR="${BIN_DIR:-$HOME/.local/share/mcp-publisher/$PUBLISHER_VERSION}"
PUB="$BIN_DIR/mcp-publisher"

stop() { echo "STOP: $*" >&2; exit 1; }
field() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get(sys.argv[2], ""))' "$SERVER_JSON" "$1"; }
mcp() { curl -fsS -m 30 -A "$UA" -X POST "https://$DOMAIN/mcp" -H 'content-type: application/json' -H 'accept: application/json, text/event-stream' -d "$1"; }

[ -f "$SERVER_JSON" ] || stop "no $SERVER_JSON"
grep -q 'REPLACE' "$SERVER_JSON" && stop "$SERVER_JSON still has a REPLACE placeholder (fill the repository id: gh api repos/<owner>/loomdesk-mcp --jq .id), or publish the site's copy"

# 1. The publisher, pinned and checked.
if [ ! -x "$PUB" ]; then
  mkdir -p "$BIN_DIR"
  curl -fsSL -o "$BIN_DIR/p.tgz" "https://github.com/modelcontextprotocol/registry/releases/download/$PUBLISHER_VERSION/mcp-publisher_linux_amd64.tar.gz"
  echo "$PUBLISHER_SHA256  $BIN_DIR/p.tgz" | sha256sum -c --quiet - || { rm -f "$BIN_DIR/p.tgz"; stop "mcp-publisher download does not match its pinned sha256"; }
  tar -xzf "$BIN_DIR/p.tgz" -C "$BIN_DIR" mcp-publisher && rm "$BIN_DIR/p.tgz"
fi

# 2. The file: the registry's own validation (schema, 100-character description), and a version not yet taken.
NAME=$(field name); VERSION=$(field version); DESCRIPTION=$(field description)
"$PUB" validate "$SERVER_JSON"
ENC_NAME=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "$NAME")
code=$(curl -s -o /dev/null -w '%{http_code}' "$REGISTRY/v0.1/servers/$ENC_NAME/versions/$VERSION")
[ "$code" = 404 ] || stop "$NAME $VERSION answers $code at the registry: already published (versions never change), bump the version"
echo "ok   $NAME $VERSION is not published yet"

# 3. Everything the entry points at answers.
for u in $(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(" ".join([i["src"] for i in d.get("icons", [])] + [d.get("websiteUrl", ""), d.get("repository", {}).get("url", "")]))' "$SERVER_JSON"); do
  [ -z "$u" ] && continue
  code=$(curl -s -m 20 -A "$UA" -o /dev/null -w '%{http_code}' "$u")
  [ "$code" = 200 ] || stop "$u answers $code: deploy it (or make the repo public) first"
  echo "ok   200 $u"
done

# 4. The live server is the version the entry says, and has what the description promises.
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"publish-check","version":"0"}}}'
LIVE_VER=$( (mcp "$INIT" || true) | sed -n 's/.*"serverInfo":{[^}]*"version":"\([^"]*\)".*/\1/p' | head -1)
[ -n "$LIVE_VER" ] || stop "https://$DOMAIN/mcp did not answer initialize"
if [ "$LIVE_VER" != "$VERSION" ]; then
  [ "${ALLOW_VERSION_DRIFT:-}" = 1 ] || stop "the live server reports $LIVE_VER, the file says $VERSION: deploy the site first (ALLOW_VERSION_DRIFT=1 to publish anyway)"
  echo "warn the live server reports $LIVE_VER, the file says $VERSION (ALLOW_VERSION_DRIFT=1)"
else
  echo "ok   the live server reports $LIVE_VER"
fi
TOOLS=$( (mcp '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' || true) | grep -oE '"name":"[a-z_]+"' | sed 's/"name":"\(.*\)"/\1/' | sort -u | tr '\n' ' ' || true)
[ -n "$TOOLS" ] || stop "https://$DOMAIN/mcp did not answer tools/list"
echo "ok   tools: $TOOLS"
if echo "$DESCRIPTION" | grep -qi 'arena'; then
  echo "$TOOLS" | grep -q 'arena_' || stop "the description names the arena but the live server has no arena_ tools: ship the arena first"
fi

# 5. The key's public half is the one the proof file serves. Only public material is compared.
if [ -f "$KEY" ]; then
  LOCAL_PUB=$(openssl pkey -in "$KEY" -pubout -outform DER | tail -c 32 | base64)
  LIVE_PUB=$(curl -fsS -A "$UA" "https://$DOMAIN/.well-known/mcp-registry-auth" | sed -n 's/.*p=\([A-Za-z0-9+/=]*\).*/\1/p')
  [ -n "$LOCAL_PUB" ] && [ "$LOCAL_PUB" = "$LIVE_PUB" ] || stop "the key's public half is not the one served at /.well-known/mcp-registry-auth"
  echo "ok   the proof file matches the key"
else
  [ "${DRY_RUN:-}" = 1 ] || stop "no key at $KEY (MCP_REGISTRY_KEY)"
  echo "skip no key at $KEY (dry run)"
fi

if [ "${DRY_RUN:-}" = 1 ]; then echo "DRY_RUN: all checks passed, nothing published"; exit 0; fi

# 6. Log in (a short-lived registry token), publish, log out. The hex never reaches the terminal.
( PRIV=$(openssl pkey -in "$KEY" -noout -text | grep -A3 'priv:' | tail -n +2 | tr -d ' :\n')
  "$PUB" login http --domain "$DOMAIN" --private-key "$PRIV" >/dev/null )
"$PUB" publish "$SERVER_JSON"
"$PUB" logout >/dev/null 2>&1 || true

# 7. What the registry now says.
curl -fsS "$REGISTRY/v0.1/servers?search=loomdesk" | python3 -m json.tool
