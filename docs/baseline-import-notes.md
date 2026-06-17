# ScienceClaw Baseline Import Notes

Updated: 2026-06-18

## Import Scope

This repository now contains the ScienceClaw baseline application shell imported
from the local reference copy:

```text
E:\Self-Project\_references\ScienceClaw
```

Imported baseline directories and files include:

- `ScienceClaw/`
- `Skills/`
- `Tools/`
- `images/`
- `docker-compose.yml`
- `docker-compose-china.yml`
- `docker-compose-release.yml`
- `release.sh`
- `windows_run.bat`
- `.dockerignore`
- `README_zh.md`
- `docs/deployment-guide-zh.md`

The reference repository's `.git` directory was not copied. The current Git
history remains owned by this repository.

## Attribution Boundary

The public attribution boundary is intentionally kept in:

- `README.md`
- `THIRD_PARTY_NOTICES.md`

If future work copies, edits, or moves upstream files that contain license or
copyright headers, keep those headers with the files.

`AGENTS.md` remains local-only and must stay outside Git history.

## Baseline Verification

The following checks were run after import:

```powershell
python -m compileall ScienceClaw\backend
```

Result: passed. The imported backend Python files compile successfully.

```powershell
npm.cmd ci
```

Working directory: `ScienceClaw\frontend`

Result: passed. Frontend dependencies installed from `package-lock.json`.

```powershell
npm.cmd run build
```

Working directory: `ScienceClaw\frontend`

Result: passed. Vite production build completed.

Observed upstream build warnings:

- Browserslist data is stale.
- One Vue-generated object literal has a duplicate `bg-amber-400` key.
- CSS minification reports syntax warnings.
- The main frontend chunk is larger than Vite's default warning threshold.

These warnings do not block the baseline import. They should be handled in a
later stabilization pass if they affect development speed, production packaging,
or UI correctness.

## Research Assistant Development Entry

The next development work should keep the ScienceClaw shell as the operating
baseline and add Research Assistant capability in this order:

1. Paper upload and parsing.
2. Paper RAG.
3. Citation evidence versus context-only memory boundaries.
4. SSE trace / ActivityPanel mapping to real backend events.
5. Evidence Audit.
6. Report generation.
7. Three-layer memory.

Do not claim any of these capabilities as complete until the backing backend
behavior, UI surface, and verification evidence exist.

## AgentMentor Rule

Each non-trivial Research Assistant feature iteration must use AgentMentor gates:

- Start Gate before implementation.
- Knowledge Retrieval when prior project context may affect the work.
- Knowledge Capture before completion claims, commit readiness, PR readiness, or
  handoff.
- Change Narrative for commit, PR, release, or handoff explanations.

This keeps development traceable while the project transitions from imported
baseline to Research Assistant-specific capability.
