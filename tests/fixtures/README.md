Fixture payloads

- `real_payloads.json` — captured verbatim from a live session with probe mode.
  Seven payloads: SessionStart, three PreToolUse calls (read_file, apply_diff,
  search_and_replace) and their PostToolUse results.
- `synthetic_payloads.json` — the earlier field-name shape the gate also accepts,
  used by recorded tests so both schemas run through one code path.
