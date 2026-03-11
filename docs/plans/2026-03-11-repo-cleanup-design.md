# Repository Cleanup Design

**Date:** 2026-03-11

**Goal:** Archive obsolete code, release artifacts, runtime outputs, and scratch files into a structured cleanup area while preserving the current runnable product path.

## Scope

This cleanup is intentionally aggressive. It includes:

- runtime caches and generated outputs
- packaged release directories and build artifacts
- temporary reference files and scratch materials
- obsolete or duplicate source files and tests
- legacy documentation that does not support the current product path

This cleanup does not permanently delete files. Every removed item is moved into `archive/cleanup/2026-03-11-repo-reset/`.

## Retained Product Path

The repository must remain able to support the current Qt launcher flow:

- `gui_launcher.py`
- `gui_qt/`
- `launcher/`
- `agent/py_service/` modules still used by launcher and task execution
- active task and pipeline definitions under `assets/`
- packaging files required for the current launcher build
- repository policy and API documentation
- tests that validate the retained product path

## Archive Layout

All cleanup targets are moved into a dated archive root with original relative paths preserved under category buckets:

- `archive/cleanup/2026-03-11-repo-reset/runtime/`
- `archive/cleanup/2026-03-11-repo-reset/release/`
- `archive/cleanup/2026-03-11-repo-reset/docs/`
- `archive/cleanup/2026-03-11-repo-reset/source/`
- `archive/cleanup/2026-03-11-repo-reset/scratch/`

A machine-readable manifest is generated at:

- `archive/cleanup/2026-03-11-repo-reset/manifest.json`

Each manifest entry records:

- original path
- archived path
- category
- reason
- whether the item was tracked by git before relocation

## Classification Rules

### Runtime

Move generated outputs and caches:

- `__pycache__/`
- `.pytest_cache/`
- `logs/`
- generated `data/`

### Release

Move packaged and release-facing outputs:

- `build/`
- `dist/`
- `release/`
- standalone release notes or release staging materials not needed for active development

### Scratch

Move ad hoc reference or temporary files:

- downloaded HTML reference files
- temporary integration notes
- root-level scratch documents

### Docs

Move historical docs that are not required for current maintenance and release work.

### Source

Move obsolete or duplicate product code and tests that are no longer part of the retained launcher path.

## Safety Rules

- No destructive deletion during this cleanup pass
- Preserve directory structure beneath archive buckets
- Generate manifest before final verification report
- Do not archive files still required by the retained launcher path
- Validate launcher/update-related tests after the move

## Verification

After cleanup:

- confirm archive root and manifest exist
- confirm removed paths are absent from their original locations
- confirm retained launcher/update tests still pass
- summarize anything intentionally left in place because it is still on the active path
