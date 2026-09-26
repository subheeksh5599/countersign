/**
 * Build the dashboard's data file from recorded evidence stores.
 *
 * Reads every scene under ../docs/evidence-store/<scene>/ and writes
 * data/store.json. Nothing is invented: every number the dashboard shows comes
 * from a gate that really ran, in a workspace that really existed.
 *
 * Usage: npm run sync-store   (or: node scripts/sync-store.mjs [source-dir])
 */
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const sourceRoot = resolve(process.argv[2] || join(here, "..", "..", "docs", "evidence-store"));
const outFile = join(here, "..", "data", "store.json");

function readJsonLines(path) {
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));
}

const scenes = [];
const events = [];
const verdicts = [];
const tasks = [];
const codes = {};

for (const name of readdirSync(sourceRoot).sort()) {
  const dir = join(sourceRoot, name);
  const eventsPath = join(dir, "events.jsonl");
  if (!existsSync(eventsPath)) continue;
  const sceneEvents = readJsonLines(eventsPath);
  const sceneTasks = [];
  const tasksDir = join(dir, "tasks");
  if (existsSync(tasksDir)) {
    for (const file of readdirSync(tasksDir).sort()) {
      if (!file.endsWith(".json")) continue;
      const manifest = JSON.parse(readFileSync(join(tasksDir, file), "utf8"));
      sceneTasks.push({
        scene: name,
        task: manifest.task,
        commit: manifest.commit || null,
        opened_at: manifest.opened_at || null,
        implicit: Boolean(manifest.implicit),
        observations: Object.entries(manifest.files || {}).map(([path, o]) => ({
          path,
          digest: o.digest,
          via: o.via || "direct",
          at: o.at || null,
        })),
        commands: Object.keys(manifest.commands || {}).length,
        contradictions: (manifest.contradictions || []).length,
      });
    }
  }
  const sceneVerdicts = sceneEvents.filter((e) => e.event === "verdict");
  for (const e of sceneEvents) events.push({ ...e, scene: name });
  for (const v of sceneVerdicts) {
    verdicts.push({ ...v, scene: name });
    for (const code of v.codes || []) codes[code] = (codes[code] || 0) + 1;
  }
  tasks.push(...sceneTasks);
  scenes.push({
    name,
    events: sceneEvents.length,
    observations: sceneEvents.filter((e) => e.event === "evidence_recorded").length,
    verdicts: sceneVerdicts.length,
    refusals: sceneVerdicts.filter((v) => v.verdict === "REFUSED").length,
    admissions: sceneVerdicts.filter((v) => v.verdict === "ADMITTED").length,
    tasks: sceneTasks.length,
  });
}

const refused = verdicts.filter((v) => v.verdict === "REFUSED");
const store = {
  generated_at: new Date().toISOString(),
  source: sourceRoot,
  scenes,
  codes,
  totals: {
    scenes: scenes.length,
    tasks: tasks.length,
    events: events.length,
    observations: events.filter((e) => e.event === "evidence_recorded").length,
    verdicts: verdicts.length,
    refusals: refused.length,
    admissions: verdicts.length - refused.length,
    first_at: events.map((e) => e.at).filter(Boolean).sort()[0] || null,
    last_at: events.map((e) => e.at).filter(Boolean).sort().slice(-1)[0] || null,
  },
  verdicts: verdicts.sort((a, b) => String(b.at).localeCompare(String(a.at))),
  tasks: tasks.sort((a, b) => String(b.opened_at).localeCompare(String(a.opened_at))),
  events: events.sort((a, b) => String(b.at).localeCompare(String(a.at))),
};

mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, JSON.stringify(store, null, 2) + "\n");
console.log(
  `synced ${store.totals.scenes} scenes, ${store.totals.tasks} tasks, ` +
    `${store.totals.events} events, ${store.totals.refusals} refusals -> data/store.json`
);
