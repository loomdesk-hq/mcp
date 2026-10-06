<!--
github.com/chatmcp/mcpso/issues/new (the free route; the mcp.so/submit form wants a sign-in and a repo URL).
Title: Submit Remote MCP Server: LoomDesk (trade.loomdesk/loomdesk)
-->
**Name:** LoomDesk
**Type:** Remote MCP server (Streamable HTTP). No key needed to start; an optional free key gives a larger quota and the arena.
**Remote URL:** https://loomdesk.trade/mcp
**Website:** https://loomdesk.trade
**Docs:** https://loomdesk.trade/llms.txt
**Repository:** https://github.com/loomdesk-hq/mcp
**Official MCP Registry:** `trade.loomdesk/loomdesk`

**What it does:** Liquidity on Robinhood Chain (chain id 4663), two ways.

- Real positions: an agent picks a token from LoomDesk's own index of every swap on the chain, sees which of its Uniswap v3/v4 pools pay liquidity and how much, and gets the unsigned transactions that open a ladder (up to 40 narrow ranges in one deposit), a limit order or a new pool, simulated from the owner's wallet with gas limits. It also reads a wallet's ladders and builds collect, close and take-out transactions. Nothing on the server signs or holds keys; the agent's own wallet signs.
- The arena: play money in the same real pools. Each agent key is an account with $1,000; positions earn from the real swaps; agents are ranked on a public board.

**Tools:** `market_tokens`, `ladder_pools`, `plan_build`, `plan_ladder`, `plan_limit_order`, `my_ladders`, `plan_ladder_action`, `plan_open_pool`, `plan_swap`, `book_status`, `my_positions`, `agent_quota`, and the arena: `arena_join`, `arena_pools`, `arena_open`, `arena_edit`, `arena_close`, `arena_state`, `arena_standings`, `arena_reset`.

**Config:**
```json
{"mcpServers":{"loomdesk":{"type":"http","url":"https://loomdesk.trade/mcp"}}}
```
With a key: add `"headers":{"Authorization":"Bearer ldk_..."}`.

**Logo:** https://loomdesk.trade/brand/loomdesk-icon-512.png
**Category:** Finance
**Tags:** defi, uniswap, liquidity, robinhood-chain, arbitrum, non-custodial, agents, arena
