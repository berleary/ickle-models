# Model assessments — consolidated evidence

The durable record behind [`data/approved-models.yaml`](../data/approved-models.yaml).
Every verdict in the catalogue traces to one of the assessment sessions below.
Harvested 2026-07-08 from scattered Claude sessions (there was no single prior
home for these findings — that scatter is the problem this repo now fixes).

## How to read this

- **Reviewed-on** dates and **session ids** are the provenance. Sessions live in
  `~/.claude/projects/<slug>/<uuid>.jsonl`.
- Evidence strength is graded honestly: **primary** (real prompts + data +
  explicit verdict), **medium** (failure observed but confounded), **thin**
  (catalogue mention only → marked `unassessed` in the YAML).

## Headline (as of 2026-07-08)

| Use case | Winner | Runner-up / note |
|---|---|---|
| Structured extraction, reasoning-at-low-cost | **deepseek-v3.2** | matched GPT-5.2 at ~1/10 cost; the fast_cheap default |
| Triage / classification / summary / compose | **gemini-3.1-flash-lite** | ~1s/item, clean JSON; won source-manager bakeoff |
| Relevance ranking / semantic search | **nomic-embed-text** (local) | top-N ranker only, not a threshold |
| Short dense compression (background) | qwen2.5:3b (local) | conditional — fails all judgment tasks |

DeepSeek V3.2 is favoured for the ickle fast_cheap tier as of 2026-07 and is
what the `model-policy` slug points at.

## Assessment sessions (primary evidence)

### 1. Local-model test on ickle — 2026-06-16
`~/.claude/projects/-home-ber-Claude/cea814ae-405c-4b2b-80b8-ebc2638b1a8e.jsonl`
Tested `qwen2.5:3b` + `nomic-embed-text` vs Haiku for source-manager tasks.
- **qwen2.5:3b**: valid JSON 10/10 but classification agreement 1/10 (rubber-
  stamped 9/10 as "deeper"); 94s/item avg, 5.6 tok/s, 3.3 GB RAM; >3000-word
  prompts timed out; truncation degraded judgment. Hallucinates on thin input.
  Verdict: "a clean, measured 'no' for this workload."
- **nomic-embed-text**: winner for relevance ranking — surfaced the reader's
  niche, buried noise; 768-dim; now powers source-manager hybrid search.

### 2. source-manager digest bakeoff — 2026-06-17
`~/.claude/projects/-home-ber-Data-Projects-source-manager/98052add-83cc-4bcc-833a-0dcba721b1f0.jsonl`
Cheap cloud models for triage/summary/compose.
- **Winner: `gemini-3.1-flash-lite`** — clean JSON (37/37), correct classes,
  real theses, named specifics; ~1s/item; 5× faster than gemini-2.5-flash.
  Now the committed model for all generative source-manager tasks.
- **`deepseek-chat-v3.1`**: dropped — slowest (~6s), weakest.
- **`gpt-5-nano`**: dropped — returns null content (reasoning model via gateway).
- Methodology caveat: exact-label agreement is a poor metric — `claude-haiku-4.5`
  self-agreed only 27%; the real bottleneck was input text quality, not model.

### 3. Representation-Profiles / StackForGood extractor bakeoff — 2026-07-04/05
`~/.claude/projects/-home-ber-Claude/0db06511-71ae-431d-a24f-ae08e9987076.jsonl`
`~/.claude/projects/-home-ber-Data-Projects-engaging-words/bf6a0a1a-cff7-4afb-911e-2b0bc976b106.jsonl`
- **Winner: `deepseek/deepseek-v3.2`** — matched GPT-5.2 on hard extraction,
  arguably reasoned better (labelled a fabrication "confabulation", cited the
  ground-truth contradiction), broke self-grading bias. 87% raw field agreement
  with GPT-5.2, **97% on report-driving fields**, diverges conservatively.
  Cost ~$0.30-0.50/run vs ~$7 for gpt-5.2. Now the committed extractor.
- **Failed through the gateway** (reasoning-content/empty issue, confounded —
  medium evidence, not proven quality problems): `gpt-5-mini`, `glm-5.1`,
  `minimax-m2.5`, `mimo-v2.5` (truncated), some Gemini tiers.
- **`gpt-5.2-chat`**: reference extractor, clean — the bar DeepSeek matched.

### 4. Cross-model temperament priors — 2026-06-17
`~/.claude/projects/-home-ber-Data-Projects-Representation-Profiles/4209fb9c-5dda-4f8e-a3e9-10f497418560.jsonl`
- Boundary-tightness axis: **Claude tight/abstaining, GPT-5.2 moderate,
  DeepSeek loose/expansive** (affirms broadly, confabulated payroll for Helios).
- Gateway operating notes: `call_model` exposes only model/prompt/system/
  max_tokens (no temperature/tools); `max_tokens < 16` → HTTP 400; `:online`
  suffix injects ~27k tokens (~$0.17); concurrency is clean.

## Correction: the penpal-bakeoff dirs are NOT cheap-model bakeoffs

The mission flagged `~/.claude/projects/-tmp-penpal-bakeoff-A` and `-B` as
assessment transcripts. They are not. Both were run by `claude-sonnet-4-6` and
contain zero ickle/`call_model`/LiteLLM calls — they are two runs of the
**PenPal content pipeline** on the same Helios HR article (2026-06-30), a
prompt-structure comparison of Sonnet against itself. No cheap-model verdict
appears. Corollary: **PenPal draft generation runs on Claude**, not a cheap
model; ickle was only ever discussed as a future option there.

## Live confirmations (2026-07-08, this session, via ickle gateway)

- `deepseek-r1` returned clean merged content at max_tokens=400 (no empty-content
  failure at that budget) but was verbose and ignored a terseness instruction.
- `deepseek-chat` wrapped JSON in ```json fences despite "only JSON".
- `qwen2.5:3b` hallucinated on a simple factual question ("MCP = Master Control
  Processor for game servers") — reconfirms: not for knowledge/judgment.
- Gateway config on ickle (`/home/ber/ai-stack/litellm-config.yaml`) currently
  sets NO `merge_reasoning_content_in_choices`, so LiteLLM defaults apply; the
  empty-content risk for heavy reasoners at low max_tokens still stands.

## Not yet pulled (next-review sources)

Referenced deliverable docs that live in project working dirs, not transcripts,
and would deepen the catalogue if harvested later:
`Representation-Profiles/docs/cross-model-findings-2026-06-17.md`,
`docs/runbook-v2-cross-model.md`, `data/derived/xmodel-compare-2026-06-17.md`,
and the RP/StackForGood config `models.extract` blocks. Solon notes #6639 and
#8833 are also referenced. Consolidated durable notes already exist at
`~/.claude/projects/-home-ber-Claude/memory/ickle.md` and
`.../memory/llm_workload_topology.md`.
