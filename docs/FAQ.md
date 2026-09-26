# FAQ

**Does this stop the agent from working?**
It stops the specific call whose evidence is stale, and it prints the four recovery
steps. A fresh observation, in this task or a new one, allows the same edit.

**Why not just check whether the file changed before writing?**
That is exactly what it does; the difference is that the check is not the agent's
judgement. The digest comparison is arithmetic, and the refusal is an exit code, so
it cannot be talked out of.

**Why not ask an agent to verify?**
An agent can say what changed. It cannot produce a copy of what was read, and its
answer is an opinion. This gate's verdict is a comparison.

**Will it block unrelated work?**
An unrelated commit no longer blocks anything: revisions are compared per path, not
per repository. A commit that touches the path a task is editing does block, because
the task's picture of that path is now behind history.

**Does it need the vendor's API?**
No. It consumes the hook payload and the workspace. There is no API key and no
network call.

**What if a hook crashes?**
The gate fails closed on its own errors. A crashing *other* hook in the runtime may
behave differently; that is the runtime's documented behaviour, not this gate's.
