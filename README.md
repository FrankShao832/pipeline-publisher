# Pipeline Publisher

Publishing for VFX/animation pipelines: copy a file out of a DCC to the path the
convention decides, and record it. No uploads, no asset browser to hunt through
— a published version is a file at a predictable path.

> **Current Version:** 2.3.0
> **Status:** Development preview — Python 3.11 + PySide6, 128 tests

---

## What it actually does

**Publishing is a copy.** The source file is copied byte-for-byte to

```
<publish_root>/<show>/<seq>/<shot>/<department>[/<dcc>]/<type>/v<NNN>/<file>
```

So a published version is visible in Finder, diffable in git, and findable
without a database. The `dcc` segment only appears when one department owns
several applications; a shot whose work lives in `lighting/` publishes to
`lighting/cache/`, one that lives in `fx/houdini/` publishes to `fx/houdini/...`.

**The path is computed, never typed.** Department and DCC come from the launch
context that Pipeline Hatch injects into the DCC process. The publish type comes
from the file extension, not from a dropdown the artist has to get right:

| extension | type |
|:--|:--|
| `.usd` `.usda` `.usdc` `.usdz` | `CACHE` |
| `.abc` `.bgeo` | `CACHE` |
| `.hip` `.hipnc` `.ma` `.nk` | `SCRIPT` |

**Version counters are scoped to the directory.** The counter's scope is
`<department>[/<dcc>]/<type>/` — it lives in the tree, so two departments can
both be at `v001` and neither can collide with the other.

**Cache publishes resolve the artifact for you.** Choosing `Cache` while the
source is still `<name>.hip` can only produce a `.hip` inside a cache folder.
Instead of silently copying the wrong file, the publisher looks for the exported
artifact beside the work file, names it, and asks before switching the source
over. When there is nothing there, it says so and refuses. The DCC still owns
the export; this only decides *which file to copy*.

**DCCs flush before publishing.** Houdini, Maya and Nuke each have a
pre-publish hook, because "publish" means "copy what is on disk": without a
flush, the newest work stays in memory and the publisher copies a stale file
while reporting success. The hook is skipped when the publish source is not the
live session, so publishing an exported USD cache does not hijack the scene.

**Every publish can be recorded.** With the database enabled, a publish also
creates or updates the asset row and its version, so Asset Manager shows the new
version immediately.

---

## Running it

```bash
conda env create -f environment.yml      # or reuse the checked-out ./env
./env/bin/python -m publisher.main
```

In production it is not started by hand: Pipeline Hatch launches the DCC with
`PIPELINE_PROJECT` / `PIPELINE_SEQUENCE` / `PIPELINE_SHOT` /
`PIPELINE_DEPARTMENT` / `PIPELINE_DCC` in the environment, and the publisher is
opened from the DCC's menu.

## Tests

```bash
./env/bin/python -m pytest -q            # 128 passed
```

The suite runs without a database and without a DCC: the file-system layer, the
path builder, the department resolution and the cache lookup are all unit-tested
in isolation.

---

## Repository layout

```
publisher/
  core/file_system/     path_builder.py · department_path.py · cache_lookup.py
  core/services/        publish_service.py
  dcc/                  houdini/ · maya/ · nuke/   (launcher + pre-publish hook)
  ui/                   main_window · widgets/ · viewmodels
tests/                  128 tests
plan/                 working notes (local only, not tracked)
```

---

## Known gaps

- **Standalone launch reads a fallback context** (`fx/houdini`). Always start it
  from the launcher so department and DCC are real; the fallback exists so the
  window opens at all, not so it can be trusted.
- **The database counter is coarser than the disk counter, and publishing is a
  blunt copy.** On disk a version is scoped to (department[, dcc], publish type);
  in the asset database it belongs to the asset (`<shot>_<department>`), so two
  publish types of one department share a sequence. There is no queue, no retry
  and no review state: a large cache blocks the UI while it copies, and
  "approved" is not a concept here yet.
