# Contributing

- Every behaviour change arrives with a case in `tests/test_matrix.py` or
  `tests/test_gate.py`. A refusal without a test is an opinion.
- New refusal codes must be added to `docs/DECISION_ORDER.md` in the order they are
  evaluated, or the matrix will not exercise them.
- Do not add a model call to a verdict path. The decision is arithmetic by design.
- Keep failure modes closed: unreadable input, unresolvable workspace and unknown
  modes refuse rather than permit.
