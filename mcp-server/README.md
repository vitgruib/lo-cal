# Lo-Cal MCP server

Lets any MCP client (Claude Desktop, Claude Code, Cursor, LM Studio, a local model's chat app) search Lo-Cal's
upcoming Berkeley events with filters. It reads the public `events.json`, so it needs no key and no server.

Tools: `search_events` (words, date range, topics, regions, free only) and `get_event` (one event in full).

Needs [uv](https://docs.astral.sh/uv/). Add to your client's MCP config:

```json
{
  "mcpServers": {
    "lo-cal": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/vitgruib/lo-cal#subdirectory=mcp-server", "lo-cal-mcp"]
    }
  }
}
```

Claude Code: `claude mcp add lo-cal -- uvx --from "git+https://github.com/vitgruib/lo-cal#subdirectory=mcp-server" lo-cal-mcp`

Tests: `cd mcp-server && uv run pytest`.
