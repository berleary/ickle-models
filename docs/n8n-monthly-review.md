# n8n monthly model review — setup

The workflow `n8n/monthly-model-review.workflow.json` keeps the ickle
[approved-models catalogue](../data/approved-models.yaml) from going stale.
Once a month it:

1. Pulls OpenRouter's live model list (`GET /api/v1/models`).
2. Diffs it against the ids ickle already knows (the catalogue baseline).
3. Runs one cheap **standard probe prompt** against each newcomer through the
   ickle LiteLLM gateway (instruction-following + JSON + arithmetic in one
   call, capped at 8 models/run so a review stays cheap).
4. Files a review note to Ber over **ntfy** (topic `ickle-model-review`) so he
   can eyeball newcomers and, if one beats DeepSeek, update the catalogue and
   the `model-policy` slug's `fast_cheap` tier.

## Where things run

- **n8n**: docker container `n8n` on host **ickle** (tailnet `100.72.113.45`),
  bound `127.0.0.1:5678`. Editor over the tailnet: `https://ickle.tail55835e.ts.net:8443/`.
- **LiteLLM gateway** (`litellm` container, same host, `127.0.0.1:4000`). From
  the n8n container it is reached at `http://host.docker.internal:4000`.
- **ntfy**: container on **shard**, published to the tailnet at
  `https://shard.tail55835e.ts.net:8452` (same endpoint the "Shard Sentry"
  workflow already posts to).

## Current status

The workflow is shipped here as importable JSON and **staged inactive** in the
live n8n instance. It is **not activated** because it needs two credentials
created in the n8n UI first (secrets are not committed and not injected from
here). Once the credentials exist and the topic is confirmed, flip it active.

## Setup steps (one-time, in the n8n UI)

1. **Import** the workflow: n8n → Workflows → Import from File →
   `monthly-model-review.workflow.json`. (Already imported inactive if the
   deploy step below was run.)

2. **Create credential "OpenRouter Bearer"** (type: *Header Auth*):
   - Name: `Authorization`
   - Value: `Bearer <OPENROUTER_KEY>` — the same key already in the litellm
     container env (`docker exec litellm printenv OPENROUTER_KEY` on ickle).
   - Attach it to the **Fetch OpenRouter models** node.

3. **Create credential "ickle LiteLLM master key"** (type: *Header Auth*):
   - Name: `Authorization`
   - Value: `Bearer <LITELLM_MASTER_KEY>` (from `~/.config/ickle-mcp/env`, or
     the litellm container env).
   - Attach it to the **Probe via ickle** node.

4. **Confirm the ntfy topic.** The **Build review note** node uses topic
   `ickle-model-review`. Subscribe to it in the ntfy app, or change it to an
   existing topic you already watch. The **Send ntfy** node posts to
   `https://shard.tail55835e.ts.net:8452` (change if your ntfy base differs).

5. **Test**: open the workflow, click **Manual run**. Confirm you get an ntfy
   push listing this month's newcomers with their probe replies.

6. **Activate** the workflow (toggle top-right). It then fires on the 1st of
   each month at 08:00 Europe/Dublin.

## Keeping the diff baseline in sync

The **Diff vs catalogue** node holds a `KNOWN_IDS` set — the catalogue's bare
OpenRouter ids at authoring time. It is intentionally self-contained (n8n on
ickle cannot read the repo on Garrus). **When you edit
`data/approved-models.yaml`, update `KNOWN_IDS` to match**, or (better, later)
host the catalogue at a URL the workflow can fetch and replace the constant
with an HTTP node. Until then, a newcomer already in the catalogue but missing
from `KNOWN_IDS` would just get re-probed once — harmless, only mildly wasteful.

## Deploying updates to the live instance

```bash
# copy the workflow into the container and import it (inactive)
scp n8n/monthly-model-review.workflow.json ickle:/tmp/mmr.json
ssh ickle 'docker cp /tmp/mmr.json n8n:/tmp/mmr.json && \
  docker exec n8n n8n import:workflow --input=/tmp/mmr.json'
```

Re-importing updates the same workflow id.
