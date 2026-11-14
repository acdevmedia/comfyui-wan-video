# Validation status

Checked 13 November 2026.

Container build and all CPU smoke checks passed for release candidate `v0.1.0-rc.2`: [GitHub Actions](https://github.com/acdevmedia/comfyui-wan-video/actions/runs/43521502232). Both image installation and ComfyUI startup succeeded. Every packaged API workflow passed live node-schema validation. Authenticated output listing, downloads, thumbnails, ZIP downloads and read-only access checks passed; zip/unzip and AWS CLI are installed, and `aws --version` succeeds. Source control/frame-grid/seed/hash-cache tests and CPU thread quota tests also passed.

Release images are public in GHCR; anonymous manifest access was verified. A private, digest-pinned Runpod test template has been created. Creating the template does not start a Pod or incur GPU usage.

Image digest: `ghcr.io/acdevmedia/wan-comfyui@sha256:622680e3baade3efc5a1d0f530262588e56aba7e00b5661ad1f44f010696b806`.

GPU smoke test, 14 November 2026, Runpod RTX PRO 6000 Blackwell Server Edition 96 GB (Community Cloud, driver 580.82, CUDA 13.0), image `v0.1.0-rc.4` with its own ComfyUI startup (no workaround), `MODEL_MODE=all` (~97 GB, ~29 min at ~55 MB/s; all five workflows installed). PyTorch attention, API workflows, 832×480, 5 s requested (81 frames, 16 fps):

| Workflow | Result | Execution | Sampled peak VRAM | Motion vs standard |
|---|---|---|---|---|
| turbo I2V (LoRA-only, rc.4), cold | success | 29.9 s | ~35 GB | ~60% |
| turbo I2V (LoRA-only, rc.4), re-roll | success | 20.0 s | ~39 GB | ~60% |
| turbo T2V (LoRA-only, rc.4) | success | 23.4 s | ~35 GB | — |
| remix I2V | success | 66.7 s | ~39 GB | ~54% |
| standard I2V (20 steps, CFG 3.5) | success | 176.0 s | ~43 GB | 100% |
| three-stage turbo I2V (now the turbo default) | success | 47.0 s | ~43 GB | ~94% |

"Motion" is mean absolute frame-to-frame luminance change on downscaled frames, a crude proxy confirmed by eye: LoRA-only turbo looked slow-motion; three-stage matched standard's action (turn, step, push-in) without visible detail loss. The new subgraph workflow loaded in ComfyUI 1.59.1 with three visible nodes; the Seed node and three-stage turbo arrive in rc.5 and were not loaded in the UI on GPU.

Not yet validated: GPU weight loading/generation, peak VRAM, timing, warm re-roll caching on GPU, reference fidelity, frontend playback, and H3 audio synchronization. No GPU performance or minimum-VRAM claim follows from these CPU results. Public template/Hub submission remains deferred until GPU tests pass.
