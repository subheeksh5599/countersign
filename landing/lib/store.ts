import raw from "@/data/store.json";

export type Observation = { path: string; digest: string; via: string; at: string | null };
export type TaskRecord = {
  scene: string;
  task: string;
  commit: string | null;
  opened_at: string | null;
  implicit: boolean;
  observations: Observation[];
  commands: number;
  contradictions: number;
};
export type Verdict = {
  at?: string;
  scene: string;
  task: string;
  path?: string;
  verdict: string;
  codes?: string[];
  receipt?: string;
  evidence_digest?: string;
};
export type StoreEvent = {
  at?: string;
  scene: string;
  event: string;
  task?: string;
  path?: string;
  digest?: string;
  receipt?: string;
  verdict?: string;
  codes?: string[];
  via?: string;
};
export type SceneSummary = {
  name: string;
  events: number;
  observations: number;
  verdicts: number;
  refusals: number;
  admissions: number;
  tasks: number;
};

type Store = {
  generated_at: string;
  source: string;
  scenes: SceneSummary[];
  codes: Record<string, number>;
  totals: {
    scenes: number;
    tasks: number;
    events: number;
    observations: number;
    verdicts: number;
    refusals: number;
    admissions: number;
    first_at: string | null;
    last_at: string | null;
  };
  verdicts: Verdict[];
  tasks: TaskRecord[];
  events: StoreEvent[];
};

export const store = raw as Store;

export const short = (value?: string | null, length = 12) =>
  value ? value.slice(0, length) : "none";

export const stamp = (value?: string | null) => (value ? value.replace("T", " ").replace("Z", "Z") : "unknown");

/** Codes the gate can emit. Recorded counts come from the store; the rest are
 *  listed as declared by the gate so the dashboard never overstates coverage. */
export const DECLARED_CODES = [
  "EVIDENCE_SUPERSEDED",
  "CROSS_TASK_EVIDENCE",
  "REVISION_MOVED",
  "COMMAND_RESULT_CHANGED",
  "UNSUPPORTED_SUBTASK_EVIDENCE",
  "UNVERIFIED_TARGET",
  "OUTSIDE_WORKSPACE",
  "NO_MANIFEST",
];
