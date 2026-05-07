# SimSat (vendored)

This directory contains a snapshot of [DPhi-Space/SimSat](https://github.com/DPhi-Space/SimSat),
the official satellite-imagery simulation API for the Liquid AI "AI in Space" hackathon.

- **Upstream:** https://github.com/DPhi-Space/SimSat
- **Snapshot SHA:** `52f5619330c1edbb2e330b2961a1a551bebc0d69` (HEAD as of 2026-04-25)
- **License:** GNU Affero General Public License v3 — see `LICENSE`.

The snapshot is included verbatim except for two operational config files we
added during Spike 2 to make the build work on our setup:

- `.dockerignore` — excludes `src/dashboard/frontend/node_modules` (210 MB)
  to work around a BuildKit symlink-mode error we hit on `node_modules/.bin/acorn`
  during build.
- `.env` — sets a dummy `MAPBOX_ACCESS_TOKEN` so the `MapboxProvider` doesn't
  raise at init. The SatDiff pipeline only exercises the Sentinel path; a real
  Mapbox token is unnecessary.

Neither file modifies SimSat source code.

## Why vendored, not submoduled

We chose vendoring over a git submodule so the rubric's fresh-clone test
remains a single command (`git clone <repo> && docker compose up`). With a
submodule the judge would need `git clone --recurse-submodules`, which is an
easy footgun.

Per AGPL-v3, the redistribution preserves the full upstream `LICENSE` and
attributes upstream above. Source is available at the upstream URL.
