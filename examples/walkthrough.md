# Walkthrough

```sh
# 1. install
sh install.sh --global

# 2. a workspace to govern
git clone <some repository> /tmp/demo && cd /tmp/demo
export COUNTERSIGN_WORKSPACE=/tmp/demo

# 3. run a task that reads a file, then let something write that file
#    (any second task, another developer, or scripts/concurrent_writer.sh)

# 4. the next edit in the reading task is refused with both digests

# 5. see the record
python3 ~/.local/share/countersign/lens.py /tmp/demo -o /tmp/demo/lens.html
```

The four refusal codes to expect, and the honest recovery for each:

| code | meaning | recovery |
|---|---|---|
| `EVIDENCE_SUPERSEDED` | the file changed after this task read it | re-read, then edit |
| `CROSS_TASK_EVIDENCE` | the only observation belongs to another task | observe it in this task |
| `REVISION_MOVED` | the path was committed at a different revision | re-read at the new revision |
| `COMMAND_RESULT_CHANGED` | a recorded command now answers differently | rerun the command, acknowledge the change |
