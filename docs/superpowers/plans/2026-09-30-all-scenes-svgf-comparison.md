# All test_vision scenes SVGF comparison plan

> **For agentic workers:** Execute inline using superpowers:executing-plans; track the steps below.

**Goal:** For each loadable distinct scene under test_vision, compare current 1 spp/frame SVGF against 2048 spp PT from five cameras.

**Architecture:** Discover native scene configurations, classify unsupported formats and duplicate variants, render low-resolution camera previews, then render matched full-resolution pairs with the existing bounded Windows launcher. Keep engine code and source assets unchanged. Store reproducible inputs, logs, hashes, images and a self-contained offline report under build/all-scenes-svgf-20260930.

**Tech Stack:** vision-eval, PowerShell Job Object launcher, Python/Pillow/NumPy.

**Spec:** User request in this conversation: 当前参数，test_vision 下的每个能打开的场景，5 个视角，对比 1 spp + SVGF 与 2048 spp PT.

## Global constraints

- Current SVGF binary/configuration; no tuning during the batch.
- SVGF 64 warmup + 128 profile frames, accumulation off; PT 64 + 1984, accumulation on.
- Match camera, resolution, exposure, materials and PT settings within each pair.
- Preserve native scene resolution; Kitchen/Staircase may reuse verified matching prior results at their established comparison resolutions.
- Every external process has a hard timeout, logs, noninteractive stdin and PID-scoped Job Object cleanup; batches also bounded.
- Scene files/asset files remain unchanged; record any test-copy adapter (e.g. a normal frame buffer for a light-field configuration).

## Review focus

- Unsupported legacy/Tungsten configurations: classify using importer schema evidence, list all exclusions.
- Commented JSON: accept comments as the native importer does.
- Camera clipping/empty images: visually inspect previews before full render.
- Cached results: require matching settings, successful process receipts and binary hashes.
- Fair sampling: verify final frame counts, accumulation flags and absence of a postprocess denoiser for PT.

## Tasks

- [x] Inventory every scene configuration and record loadability and duplicates.
- [x] Prepare five camera poses per supported scene and visually inspect previews.
- [x] Render/reuse all matched full-resolution pairs under bounded execution.
- [x] Generate comparison sheets, per-view metrics, scene summaries and offline report.
- [x] Verify coverage, image dimensions, frame counts, settings/hashes, all report links, and list failures/timeouts/skips.

## Completed scope

- Excluded cbox-spec at the user's request.
- Delivered 12 scenes, 60 matched camera pairs and 120 original images; 20 images reused after checking settings and historical process/binary receipts.
- Coverage and reproducibility verification passed 2,677 checks. No render failures or timeouts. Four verification fault tests passed.
- Static images only; display-space metrics do not establish linear HDR convergence or dynamic stability. Unsupported configuration formats and duplicate variants are listed in the report.
