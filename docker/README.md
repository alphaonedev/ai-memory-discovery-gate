# Discovery-gate Docker assets

These Dockerfiles + compose files + helper scripts were imported from
[`alphaonedev/ai-memory-a2a-v0.6.3.1`](https://github.com/alphaonedev/ai-memory-a2a-v0.6.3.1)
where they were authored during the v0.6.3.1 A2A campaign that
shipped 9/9 substrate streaks across OpenClaw / IronClaw / Hermes.

They are reused verbatim here so the discovery gate runs in the
same containerized topology that already proved out the substrate.
The discovery-gate runner adds **only** the orchestration layer on
top: per-cell DB restore, prompt dispatch, transcript capture,
verdict evaluation.

## Files

| File | Source | Reused for |
|---|---|---|
| `Dockerfile.base` | v0.6.3.1 | Common Rust + Python toolchain image |
| `Dockerfile.openclaw` | v0.6.3.1 | OpenClaw 16GB harness image |
| `Dockerfile.ironclaw` | v0.6.3.1 | IronClaw 8GB harness image (Postgres + pgvector) |
| `Dockerfile.hermes` | v0.6.3.1 | Hermes 16GB harness image (Python + httpx 0.27.2) |
| `docker-compose.openclaw.yml` | v0.6.3.1 | 4-node mesh, bridge `10.88.1.0/24` |
| `docker-compose.ironclaw.yml` | v0.6.3.1 | 4-node mesh, bridge `10.88.2.0/24` |
| `docker-compose.hermes.yml` | v0.6.3.1 | 4-node mesh, bridge `10.88.3.0/24` |
| `entrypoint.sh` | v0.6.3.1 | Per-harness MCP-server bootstrap |
| `drive_agent.sh` | v0.6.3.1 | Per-harness LLM driver (xAI Grok 4.3 default) |
| `run-testbook.sh` | v0.6.3.1 | 105-scenario substrate test runner |
| `healthcheck.sh` | v0.6.3.1 | Per-container liveness probe |
| `gen-tls.sh` | v0.6.3.1 | Generate test mTLS certs |

## Discovery-gate-specific overrides

**v0.6.4 binary bind-mount.** The compose files pull `ai-memory` from a
release artifact; the discovery-gate runner overrides `image:` to mount
the v0.6.4-rc binary instead. See `runner/src/transcript.rs` for the
override mechanism.

**v0.6.3.1 DB baseline restore.** Each cell starts with a clean
restore of `fixtures/corpus/v0.6.3.1-baseline.db.gz` to the agent
container's `/var/lib/ai-memory/` volume. The v0.6.4 binary then
opens the v0.6.3.1-shape DB on first start, runs the v18/v19 → v20
migration, and proceeds with the discovery test. This exercises the
migration path AND the discovery mechanisms in a single run.

**Profile injection.** Each cell sets `--profile <name>` via
`AI_MEMORY_PROFILE` env in the compose override so the runner
doesn't need to rewrite the compose file per cell.

## Reproducing locally

```bash
# Build base + per-harness images
docker buildx build -f Dockerfile.base -t ai-memory-base:v0.6.4 .
docker buildx build -f Dockerfile.openclaw -t openclaw-discovery:v0.6.4 .
docker buildx build -f Dockerfile.ironclaw -t ironclaw-discovery:v0.6.4 .
docker buildx build -f Dockerfile.hermes -t hermes-discovery:v0.6.4 .

# Run one cell (replaces all of run-testbook.sh's substrate suite —
# the discovery-gate runner orchestrates this from Rust):
../runner/target/release/discovery-gate run \
  --binary /path/to/ai-memory-mcp/target/release/ai-memory \
  --tier t1 \
  --llm grok-4.3 \
  --harness openclaw \
  --profile core \
  --output ../docs/runs/$(date +%Y-%m-%d)
```

## Out-of-scope additions

The 105-scenario substrate suite (run-testbook.sh) is **not** invoked
by the discovery gate — it's preserved here only because the harness
images depend on its support scripts. The substrate suite belongs to
the v0.6.3.1 A2A campaign; the discovery gate uses the same containers
to host an entirely different testbook (the four discovery-gate prompts).
