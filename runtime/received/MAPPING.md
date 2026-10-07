# Packages as received from GPT

Kept exactly as they arrived (documents and code), for reference. The code that actually runs is in `runtime/server/`.

| Folder | Was | What it is | Status |
|---|---|---|---|
| `runtime_v0.7.0/` | `09_Operations/from_GPT_v0.7.0/` | documents of runtime v0.7.0 (daily operations, roadmap, rehearsal) | superseded by v0.8.x |
| `runtime_v0.8.0/` | `09_Operations/from_GPT_v0.8.0/` | documents of runtime v0.8.0 (handoff, staging with a dynamic IP) | superseded by v0.8.1; the same documents are in `runtime/server/operations/` |
| `runtime_v0.8.1/` | `09_Operations/from_GPT_v0.8.1/` | acceptance note of v0.8.1 | installed version |
| `bro_bridge_v0.1.0/` | `09_Operations/from_GPT_bro_v0.1.0/` | Bro queue bridge v0.1.0 | superseded by the v0.1.1 patch; `test_bro_worker.py` of this version is the one on the server |
| `bro_bridge_v0.1.1/` | `09_Operations/from_GPT_bro_v0.1.1/` | patch v0.1.1 of the queue bridge | installed |
| `bro_http_v0.2.0/` | `09_Operations/from_GPT_bro_v0.2.0/` | Bro HTTP bridge v0.2.0 | installed (service active, not enabled) |
| `bro_edge_v0.2.0/` | `09_Operations/from_GPT_bro_edge_v0.2.0/` | edge acceptance checks v0.2.0 | superseded by v0.2.1 |
| `bro_edge_v0.2.1/` | `09_Operations/from_GPT_bro_edge_v0.2.1/` | edge acceptance checks v0.2.1 | the version used for the acceptance |

The code of the runtime releases themselves (v0.7.x, v0.8.x) was never in the repository; it came as zip packages and was installed on the server. `runtime/server/` now holds it as installed. The v0.8.1 zip is kept outside git.

`runtime/server_patches/` (was `09_Operations/patches_by_claude/`) holds Claude's copy of the installed `ops_views.py` (same sha256 as `runtime/server/ops_views.py`) and an edge-check patch made before GPT's v0.2.1.
