# Testing

Two suites, both real: real git workspaces, real files, real subprocesses, real exit
codes. Nothing is mocked.

```sh
python3 tests/test_gate.py      # 15 behaviour cases, one per decision and failure mode
python3 tests/test_matrix.py    # 500 cases across the whole decision table
python3 tests/test_matrix.py -j 8
```

The matrix builds its cases from the decision order in `docs/DECISION_ORDER.md`:
evidence states, disk states, revision states, policy, four write tools, six path
forms, command contradictions, subtask attribution, payload-schema compatibility,
receipts, exports, lens rendering and concurrency orderings. Failures print the case
name and the observed output.

The suites found three real defects during development, all fixed: a resumed task
reopening its manifest and erasing its own evidence, a hook merge that duplicated
entries, and a payload that was valid JSON but not an object crashing the gate
instead of failing closed.
