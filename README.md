# ickle-models

A small [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that
exposes a [LiteLLM](https://github.com/BerriAI/litellm) gateway to an MCP client such
as Claude Code. It gives the model two tools for reaching **any** model behind the
gateway -- local [Ollama](https://ollama.com) models and any cloud model routed
through [OpenRouter](https://openrouter.ai) (OpenAI, Perplexity, DeepSeek, Gemini, and
so on) -- through **one endpoint and one key**, instead of configuring a separate
provider integration for each.

It is deliberately tiny: a single file, standard-library HTTP only, one dependency
(`mcp`). It is meant as a clean, readable example of an MCP server you can run,
extend, or read in five minutes.

## Tools

| Tool | Description |
|------|-------------|
| `list_models()` | Returns every model id callable through the gateway. Call this first to discover valid `model` values. |
| `call_model(model, prompt, system="", max_tokens=1024)` | Sends a prompt to any of those models and returns its text reply. Useful for getting a second opinion from another model mid-task, or routing a sub-question to a web-search model. |

## Why

When you work inside one assistant (Claude Code) but want to consult other models --
a search-grounded model for fresh facts, a cheap local model for bulk work, a
different frontier model for a second opinion -- you normally juggle several SDKs and
keys. A LiteLLM gateway already unifies those providers behind one OpenAI-compatible
endpoint. This server simply surfaces that gateway to the assistant as MCP tools, so
the model can pick and call any of them itself.

## Requirements

- Python 3.10+
- A running LiteLLM gateway (or any OpenAI-compatible `/v1/models` and
  `/v1/chat/completions` endpoint)
- `pip install mcp`

## Configuration

All configuration is via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ICKLE_BASE_URL` | `http://localhost:4000` | Gateway base URL |
| `LITELLM_MASTER_KEY` | (unset) | Gateway auth key |
| `ICKLE_MCP_ENV` | `~/.config/ickle-mcp/env` | Fallback file holding a `LITELLM_MASTER_KEY=...` line, if the env var is unset |

No secrets are committed. Copy `.env.example` to your key file (or export the env
var) and point `ICKLE_BASE_URL` at your gateway.

## Use with Claude Code

Add it as a stdio MCP server. Example `.mcp.json` (or the `mcpServers` block in
Claude Code settings):

```json
{
  "mcpServers": {
    "ickle-models": {
      "command": "python",
      "args": ["/path/to/ickle-models/ickle_models.py"],
      "env": {
        "ICKLE_BASE_URL": "http://localhost:4000",
        "LITELLM_MASTER_KEY": "sk-your-gateway-key"
      }
    }
  }
}
```

Then, inside Claude Code:

```
> list the models available through ickle
> ask openrouter/perplexity/sonar what changed in the MCP spec this month
```

## Run standalone

```bash
LITELLM_MASTER_KEY=sk-... ICKLE_BASE_URL=http://localhost:4000 python ickle_models.py
```

The server speaks MCP over stdio, so it is normally launched by an MCP client rather
than run by hand.

## License

MIT -- see [LICENSE](LICENSE).
