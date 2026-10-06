# Submitting LoomDesk to registries and directories

Everything here is prepared and checked; nothing has been published, pushed or submitted. Each step below says what is ready and what only the operator can do (accounts, claims, the publish key).

Check the files any time: `python3 scripts/check.py` (add `--live` to have the registry validate server.json; set `MCP_PUBLISHER` to an mcp-publisher binary). `python3 scripts/test_check.py` proves the checker catches each kind of mistake.

## 0. First: ship the site

Version 2.3.0 and its description promise the arena. Publish nothing until loomdesk.trade serves:

- the arena tools and agent keys on `/mcp`, and `serverInfo.version` 2.3.0;
- `/brand/loomdesk-icon-512.png`, `/.well-known/mcp/server.json`, `/.well-known/mcp/server-card.json` and `/.well-known/ai-catalog.json` (all in `web/public/`, deployed with the arena, not before: they describe it);
- the arena and keys in `llms.txt`.

`publish.sh` refuses to publish while the live version or the arena tools are missing.

## 1. The public repo (unlocks most of the rest)

Ready: this repo (README, LICENSE, server.json, plugin files for Claude Code, Cursor and Gemini CLI, the skill).

Operator:
1. Choose the owner. Every file says `Romovow/loomdesk-mcp`; for another owner, replace that string everywhere (`grep -rl --exclude-dir=.git Romovow/loomdesk-mcp . | xargs sed -i 's#Romovow/loomdesk-mcp#OWNER/loomdesk-mcp#g'`).
2. Fill the Privacy section of README.md (the `TODO(operator)` line).
3. Decide whether `listings/` stays in the public repo (nothing secret in it).
4. Create the repo as public, push `main`, add the topics `mcp`, `mcp-server`, `gemini-cli-extension`, `claude-code-plugin`.
5. Put the repo id into `server.json` (`gh api repos/OWNER/loomdesk-mcp --jq .id`, as a string), then copy the file over `web/public/.well-known/mcp/server.json` so the site serves the same entry. `scripts/check.py` must show 0 warnings.

## 2. Official MCP Registry (registry.modelcontextprotocol.io)

Published 2.4.0 on 2026-10-07 (the arena in the description; 1.0.0 and the stock-pool blurb are history). Glama, PulseMCP and the GitHub MCP Registry copy from it. Next version: bump server.json and run the script again.

Ready: `server.json` 2.3.0 (registry-validated), `listings/official-registry/publish.sh` (pinned mcp-publisher v1.8.1 with its sha256; HTTP domain proof; never prints the key).

Operator, after step 0 (and step 1 if the entry should name the repo):
- `DRY_RUN=1 bash listings/official-registry/publish.sh` runs every check and stops before logging in.
- `bash listings/official-registry/publish.sh` publishes. Before the repo exists, pass the site's copy instead: `bash listings/official-registry/publish.sh ~/loomdesk.trade/web/public/.well-known/mcp/server.json`.
- A version is published once and never changes: 2.3.0 can go out only once, so choose the copy (with or without the repo) before running it.
- Needs `~/.config/loomdesk/mcp-registry-key.pem` (or `MCP_REGISTRY_KEY`), whose public half the site serves at `/.well-known/mcp-registry-auth`.

## 3. Glama (glama.ai)

Already lists the connector (imported from the registry); it refreshes after step 2.

Operator: sign in, open the claim panel for `trade.loomdesk/loomdesk`, copy the `glama_claim_...` token into `web/public/.well-known/glama.json` (template: `listings/glama/glama.json`), deploy, press verify. Keep the file published: the claim lasts only while it is served.

## 4. PulseMCP

Nothing to do. New submissions are paused (since 2026-09-03); it picks up the official registry when it reopens.

## 5. Smithery (smithery.ai)

Ready: nothing to prepare; the scanner reads the live server, and `/.well-known/mcp/server-card.json` is its fallback.

Operator: create an account and a namespace, then paste `https://loomdesk.trade/mcp` at smithery.ai/new (or `npx @smithery/cli login`, then `smithery mcp publish "https://loomdesk.trade/mcp" -n @NAMESPACE/loomdesk`), then Settings, Verification.

Watch: Smithery relays every user's calls from Cloudflare Workers, which reach the site as one address. Without keys those users share one anonymous quota; tell them to add a key.

## 6. awesome-remote-mcp-servers (punkpeye)

Ready: `listings/awesome-remote-mcp-servers.md` (the entry for the Finance section; the lock and key marks are that list's legend).

Operator: star the repo (required), fork it, add the entry after "Loophole Tape", open a PR titled "Add LoomDesk". Its CI calls initialize and checks the Glama badge.

## 7. mcp.so

Ready: `listings/mcp-so-issue.md` (title and body).

Operator: open an issue at github.com/chatmcp/mcpso from your GitHub account. After step 1 the mcp.so/submit form works too (it wants a sign-in and a repo URL). Optional paid lane lists at once.

## 8. mcpservers.org

Ready: `listings/mcpservers-org-form.txt`.

Operator: fill the form at mcpservers.org/submit with a contact email. Free queue about two weeks; optional paid lane 24 h.

## 9. MCP Market (mcpmarket.com)

Waits for step 1 (it needs a GitHub repo URL). Operator: submit the repo URL at mcpmarket.com/submit. Free queue 4 to 6 weeks; optional paid lane 24 h.

## 10. Docker MCP Catalog

Ready: `listings/docker/servers/loomdesk/` (server.yaml, tools.json, readme.md in their remote format, no OAuth).

Operator: fork docker/mcp-registry, copy the folder to `servers/loomdesk`, optionally test with `task catalog -- loomdesk` and `docker mcp catalog import $PWD/catalogs/loomdesk/catalog.yaml`, open a PR. Docker reviews every PR.

## 11. GitHub MCP Registry (github.com/mcp, VS Code's gallery)

Nothing to submit: a curated subset of the official registry, weighted by repo stars. Steps 1 and 2 are the way in.

## 12. Claude Code plugin

Ready: `.claude-plugin/` and `.mcp.json` (`claude plugin validate --strict` passes; the header carries `LOOMDESK_KEY` when it is set and is empty otherwise, tested).

After step 1, anyone can run `/plugin marketplace add OWNER/loomdesk-mcp` then `/plugin install loomdesk@loomdesk`. Nothing to submit.

## 13. Cursor

Ready: the "Add to Cursor" link in the README, and `plugin.json` with `mcp.json` (Agent Plugins 1.0.0, schema-valid).

Nothing to submit for MCP. The Cursor Marketplace (reviewed plugins from a Git repo) and cursor.directory (community, sign-in) are optional after step 1.

## 14. Gemini CLI extensions gallery

Ready: `gemini-extension.json` and `GEMINI.md` at the root.

After step 1 with the `gemini-cli-extension` topic, the gallery crawls it daily. Nothing to submit.

## 15. Claude Connectors Directory

Not ready, by policy: Anthropic's Software Directory Policy 4.A excludes software that executes financial transactions for users, which the planning tools come close to. Users can still add the URL as a custom connector. A separate arena-only endpoint (play money, `trade.loomdesk/arena`) would be the submittable one; not built.

## 16. ChatGPT apps directory

Skip: its guidelines prohibit crypto transfers and trades. Users can add the URL as a connector in developer mode.

## What is left on the server side

- Tool annotations (`readOnlyHint`, `destructiveHint`) and `title` on every tool raise Glama's score and are required by the Claude directory.
- Cloudflare: Python-urllib gets 403 on `/mcp`; turn off what blocks it (likely Browser Integrity Check) for `/mcp*`, `/.well-known/*`, `/llms.txt` and `/api/agent/*`.
- Optional CORS on `/mcp` for MCP clients that run in a browser.
