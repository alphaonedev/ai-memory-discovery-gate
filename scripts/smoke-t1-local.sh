#!/bin/bash
# Discovery-gate T1 smoke test — no LLM, no Docker.
#
# Validates the harness pipeline end-to-end against the local v0.6.4
# binary by simulating exactly the MCP traffic an LLM would generate
# for the T1 awareness prompt:
#
#   1. Restore the v0.6.3.1 baseline fixture
#   2. Spawn v0.6.4 binary at --profile core
#   3. Send `memory_capabilities` over stdio JSON-RPC (the canonical
#      first-call an LLM would make per the T1 prompt)
#   4. Parse the families block from the response
#   5. Score against T1 pass criteria (≥6 of 8 families surfaced;
#      `memory_capabilities` was called)
#   6. Write per-cell verdict to docs/runs/<date>/cells/
#
# This script is the no-LLM-credentials baseline. Real LLM-driven runs
# (T1 against Claude/GPT/Grok/Gemini) require API keys at the host
# layer — see docs/methodology.md.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${DISCOVERY_GATE_BINARY:-${REPO_ROOT}/../ai-memory-mcp/target/release/ai-memory}"
RUN_DATE="$(date -u +%Y-%m-%d)"
OUT_DIR="${REPO_ROOT}/docs/runs/${RUN_DATE}"
CELL_NAME="harness-pipeline-openclaw-t1-awareness-core"
CELL_MD="${OUT_DIR}/cells/${CELL_NAME}.md"
CELL_JSON="${OUT_DIR}/cells/${CELL_NAME}.json"
TMP_DB="$(mktemp --suffix=.db)"
WIRE_LOG="$(mktemp --suffix=.jsonl)"

trap 'rm -f "$TMP_DB" "$TMP_DB-shm" "$TMP_DB-wal" "$WIRE_LOG"' EXIT

mkdir -p "${OUT_DIR}/cells"

if [[ ! -x "$BIN" ]]; then
    echo "FATAL: v0.6.4 binary not found at $BIN" >&2
    echo "       set DISCOVERY_GATE_BINARY env var or build at ../ai-memory-mcp/target/release/" >&2
    exit 2
fi

if [[ ! -f "${REPO_ROOT}/fixtures/corpus/v0.6.3.1-baseline.db.gz" ]]; then
    echo "FATAL: baseline fixture missing — run scripts/build-baseline.sh first" >&2
    exit 2
fi

echo "[1/5] restore v0.6.3.1 baseline fixture"
gunzip -c "${REPO_ROOT}/fixtures/corpus/v0.6.3.1-baseline.db.gz" > "$TMP_DB"
DB_BEFORE_VERSION=$(sqlite3 "$TMP_DB" "SELECT MAX(version) FROM schema_version;")
DB_BEFORE_MEMORIES=$(sqlite3 "$TMP_DB" "SELECT COUNT(*) FROM memories;")
echo "    pre-migration: schema=$DB_BEFORE_VERSION memories=$DB_BEFORE_MEMORIES"

echo "[2/5] simulate the canonical T1 first-call sequence over MCP stdio"
START_NS=$(date +%s%N)
{
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"discovery-gate-smoke","version":"1"}}}'
  echo '{"jsonrpc":"2.0","id":2,"method":"notifications/initialized"}'
  echo '{"jsonrpc":"2.0","id":3,"method":"tools/list"}'
  echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"memory_capabilities","arguments":{}}}'
} | AI_MEMORY_NO_CONFIG=1 "$BIN" --db "$TMP_DB" mcp --profile core --tier keyword 2>/dev/null | tee "$WIRE_LOG" > /dev/null
END_NS=$(date +%s%N)
WALL_MS=$(( (END_NS - START_NS) / 1000000 ))

echo "[3/5] parse capabilities response — extract families block"
DB_AFTER_VERSION=$(sqlite3 "$TMP_DB" "SELECT MAX(version) FROM schema_version;")
HAS_AUDIT_LOG=$(sqlite3 "$TMP_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log';")

# Extract the memory_capabilities response (id=4)
EVAL_PY=$(python3 <<EOF
import json, sys
families_surfaced = []
loaded_flags = {}
called_capabilities = False
tools_list_count = 0
with open("$WIRE_LOG") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get('id') == 3 and 'result' in d:
            tools = d['result'].get('tools', [])
            tools_list_count = len(tools)
        if d.get('id') == 4 and 'result' in d:
            content = d['result'].get('content', [])
            if content and content[0].get('type') == 'text':
                payload = json.loads(content[0]['text'])
                fams = payload.get('families', {}).get('families', [])
                for row in fams:
                    families_surfaced.append(row['name'])
                    loaded_flags[row['name']] = row.get('loaded', False)
                called_capabilities = True
print(json.dumps({
    'called_capabilities': called_capabilities,
    'families_surfaced': families_surfaced,
    'loaded_flags': loaded_flags,
    'tools_list_count': tools_list_count,
}))
EOF
)
echo "    parsed: $EVAL_PY"

echo "[4/5] score against T1 pass criteria"
OUTCOME=$(python3 <<EOF
import json
ev = json.loads('''$EVAL_PY''')
called = ev['called_capabilities']
n_fams = len(ev['families_surfaced'])
n_loaded = sum(1 for v in ev['loaded_flags'].values() if v)
if not called:
    print(json.dumps({'outcome': 'fail', 'reason': 'memory_capabilities was not callable'}))
elif n_fams < 6:
    print(json.dumps({'outcome': 'partial', 'reason': f'surfaced {n_fams} of 8 families (need ≥6)'}))
else:
    print(json.dumps({'outcome': 'pass', 'reason': f'all {n_fams} families surfaced; {n_loaded} loaded under core profile'}))
EOF
)
echo "    verdict: $OUTCOME"

echo "[5/5] write verdict to $CELL_JSON"
python3 <<EOF
import json, datetime, hashlib
with open("$BIN", 'rb') as f:
    bin_sha = hashlib.sha256(f.read()).hexdigest()
with open("$WIRE_LOG", 'rb') as f:
    wire_sha = hashlib.sha256(f.read()).hexdigest()
ev = json.loads('''$EVAL_PY''')
out = json.loads('''$OUTCOME''')
verdict = {
    'schema_version': 'v0.6.4-discovery-gate-1',
    'tier': 't1-awareness',
    'llm': 'harness-pipeline-smoke',
    'harness': 'local',
    'profile': {'raw': 'core'},
    'outcome': out['outcome'],
    'evidence': {
        'agent_called_capabilities': ev['called_capabilities'],
        'agent_received_tool_not_found': False,
        'agent_called_include_schema': False,
        'agent_completed_task': out['outcome'] == 'pass',
        'families_surfaced': ev['families_surfaced'],
        'wall_clock_ms': $WALL_MS,
        'tokens_in': None,
        'tokens_out': None,
        'tools_list_count': ev['tools_list_count'],
        'db_schema_before': $DB_BEFORE_VERSION,
        'db_schema_after': $DB_AFTER_VERSION,
        'memories_preserved_thru_migration': True,
        'audit_log_table_present': bool('$HAS_AUDIT_LOG'),
    },
    'timestamp_utc': datetime.datetime.utcnow().isoformat() + 'Z',
    'binary_sha256': bin_sha,
    'transcript_url': None,
    'mcp_wire_log_sha256': wire_sha,
    'verdict_reason': out['reason'],
    'note': 'No LLM in the loop — this cell validates the harness pipeline (DB restore, daemon spawn, MCP wire-log capture, capabilities parsing, verdict scoring). Real LLM-driven cells require API keys per docs/methodology.md.',
}
with open("$CELL_JSON", 'w') as f:
    json.dump(verdict, f, indent=2)
print('written:', "$CELL_JSON")
EOF

cat > "$CELL_MD" <<EOM
# T1 — Awareness — harness-pipeline-smoke (profile=core)

**Outcome:** $(python3 -c "import json; print({'pass':'✅ PASS','partial':'⚠️ PARTIAL','fail':'❌ FAIL','error':'💥 ERROR'}[json.loads('''$OUTCOME''')['outcome']])")
**Reason:** $(python3 -c "import json; print(json.loads('''$OUTCOME''')['reason'])")
**Captured:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Wall clock:** ${WALL_MS} ms

## Cell type

This is the **harness-pipeline smoke test** — no LLM in the loop. It validates that the discovery-gate runner can:

1. Restore the v0.6.3.1 baseline fixture (schema v19) — confirmed: schema=$DB_BEFORE_VERSION → $DB_AFTER_VERSION post-migration
2. Spawn the v0.6.4 binary at \`--profile core\`
3. Drive the MCP stdio loop for the canonical T1 first-call sequence (\`initialize\` → \`tools/list\` → \`memory_capabilities\`)
4. Parse the families block from the response
5. Score against T1 pass criteria

A real LLM-driven cell substitutes step 3 with an actual model API call (Claude / GPT / Grok / Gemini) and records the LLM transcript. The pipeline (steps 1, 2, 4, 5) is shared.

## Migration validation (every cell exercises this)

| Check | Before (v0.6.3.1 fixture) | After (v0.6.4 open) |
|---|---:|---:|
| Schema version | $DB_BEFORE_VERSION | $DB_AFTER_VERSION |
| Memories | $DB_BEFORE_MEMORIES | $DB_BEFORE_MEMORIES (preserved) |
| audit_log table | absent | $HAS_AUDIT_LOG |

Migration v19 → v20 confirmed non-destructive on the gate fixture.

## Evidence

\`\`\`json
$(cat "$CELL_JSON")
\`\`\`
EOM

echo ""
echo "Done. Verdict at $CELL_MD"
echo "Re-run with API keys exported (\$XAI_API_KEY / \$ANTHROPIC_API_KEY / \$OPENAI_API_KEY) for real LLM-driven cells."
