# Installing

```sh
sh install.sh --global                        # gate, CLI wrapper, global hooks
sh install.sh /path/to/workspace              # print the workspace block
sh install.sh /path/to/workspace --write      # merge it into that workspace
```

The machine-wide install places:

```
~/.local/share/countersign/countersign.py     the gate
~/.local/share/countersign/lens.py            the evidence page renderer
~/.local/bin/countersign                      a wrapper on the PATH
~/.bob/settings/settings.json                 the global hook block
```

Both installs are idempotent: a second run adds no duplicate hook entries. Verify a
hook is live by running one task and checking that `.countersign/tasks/` gained a
manifest named after the task id the runtime reports.

Set `COUNTERSIGN_WORKSPACE` before a session, or rely on the `cwd` each hook payload
carries. Add `COUNTERSIGN_REQUIRE_PRIOR_READ=1` to refuse writes to paths a task
never observed.
