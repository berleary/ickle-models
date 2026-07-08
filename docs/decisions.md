# Decisions

Newest first.

## 2026-07-08 — Add `describe_models` rather than change `list_models`

**Context.** ickle only exposed a raw model id list; callers had no guidance on
which model to use or how to structure queries per family (DeepSeek/Qwen/GLM/…
differ on system prompts, reasoning quirks, JSON mode, temperature). Past model
assessments were scattered across sessions. (Ber, 2026-07-08.)

**Options.**
1. Enrich `list_models` to return the full catalogue, with a `raw` flag for the
   flat id list.
2. Add a separate `describe_models` tool; keep `list_models` as the raw list.

**Decision: option 2.** `list_models()` keeps returning `list[str]` — its
documented contract, which other callers may already depend on. A new
`describe_models(model="")` tool returns the curated catalogue. This is purely
additive (zero breakage), and the split is honest: `list_models` = "what can I
call", `describe_models` = "what should I call and how". `list_models` and
`call_model` docstrings now point at `describe_models`, so an LLM caller
discovers it. The mission that commissioned this change was dispatched from EDI,
which authorises the interface change; keeping it additive means it does not
break the `list_models` contract other apps read.

**Catalogue format: YAML, not JSON.** The catalogue is hand-maintained and Ber
reviews it (it feeds `model-policy`'s fast_cheap tier), so YAML's comments and
readability win. This adds a `PyYAML` dependency; the loader degrades gracefully
(JSON sidecar, then an error marker) so the server still starts without it and
`list_models`/`call_model` keep working.

**Freshness: monthly n8n review.** Rather than let the catalogue rot, a monthly
n8n workflow diffs OpenRouter's live list against it, probes newcomers through
the gateway, and pings Ber over ntfy. See `docs/n8n-monthly-review.md`.

**Repo vs deployment.** This repo is the clean, shareable version (localhost
gateway default, no secrets). Ber's live instance at `~/.config/ickle-mcp/`
keeps its own `ICKLE_BASE_URL` default (the ickle tailnet Serve URL). That
divergence is intentional, not drift.

**Deploy to the live instance (not done automatically — run when ready).** The
enriched server + catalogue are verified in-repo but the live
`~/.config/ickle-mcp/` copy is unchanged. To push it live, preserving its
tailnet default:

```bash
DST=~/.config/ickle-mcp
cp ickle_models.py "$DST/ickle_models.py"
sed -i 's#"http://localhost:4000"#"https://ickle.tail55835e.ts.net:4000"#' "$DST/ickle_models.py"
mkdir -p "$DST/data" && cp data/approved-models.yaml "$DST/data/approved-models.yaml"
"$DST/venv/bin/python" -m pip install 'PyYAML>=6'
```

Then restart Claude Code (the MCP is stdio-spawned per session) and call
`describe_models`. The `data/` path resolves next to the script by default; set
`ICKLE_CATALOGUE` to override. Verified 2026-07-08 that the enriched loader
imports and serves the catalogue under the deployed venv layout.
