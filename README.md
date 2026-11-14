# WAN 2.2 I2V-A14B ComfyUI Runpod bundle

Version profile: `versions/2.2/`. Bundle revision: `0.1.0`. Container image: `ghcr.io/acdevmedia/wan-comfyui:2.2`. **Reference bundle. Every `develop` build passes the source, container and CPU schema checks before publishing. GPU generation was verified on an RTX PRO 6000 (see docs/VALIDATION.md); the latest canvas and Exact Frame changes have not yet run on a GPU.**

Available modes: standard (20 steps), turbo (8-step three-stage schedule: two high-noise steps on the base model at CFG 3.5 to set real motion, then the matched high/low LightX2V adapters at CFG 1), remix (v3.0 checkpoints; experimental 12-step publisher-example schedule). Default: `all`: every workflow (each mode, image-to-video and text-to-video) is installed and its weights downloaded, about 97 GB. Set `MODEL_MODE` to a single mode for a smaller download (about 36–42 GB) and only that mode's workflows. Workflows (Workflows sidebar → **WAN 2.2 video (reference)**): 01/02 **Turbo** image/text to video, 03/04 **Standard 20-step**, 05 **Remix** image to video.

Every workflow uses the same canvas as the LTX and Eros bundles: **01 · Describe your shot** (the prompt), **Starting image** (image-to-video only), **02 · Shot settings** and **03 · Your video** (the MP4, with the seed actually used saved in its metadata). Shot settings holds width, height, Exact Frame, duration in seconds (no upper limit; very long clips are untested and slow), seed and the negative prompt; the whole pipeline sits inside it (double-click to inspect or edit). The seed is randomized *before* every queue by the same seed extension as LTX and Eros, so the number shown is the one used; switch its *seed mode* to fixed, increment or decrement to control takes. A seed of 0, which the shipped API graphs use, makes the server draw a fresh random seed per job, so API clients also randomize. With a starting image, Width × Height sets the frame's area and the image sets its shape, so a portrait upload renders portrait at the same cost; turn on **Exact Frame** to use your exact Width and Height instead, which centre-crops the image (same rule as LTX and Eros).

WAN uses 16 fps with `4k+1` frames; H3 uses 24 fps with `17k+5`. A five-second request rounds up to 81 / 124 frames respectively. Dimensions must be multiples of 32. Upload your own reference image into Load Image before queueing; `reference.png` is a placeholder, not a packaged asset. H3 also generates audio from the positive prompt. The Videos & Audio button opens recent outputs inside ComfyUI.

## Build and launch

1. Put this directory in its own GitHub repository. The included Actions workflow validates source, builds the image, starts ComfyUI in CPU mode to check node schemas, tests the authenticated output browser, and publishes version and immutable `sha-<commit>` image tags. Builds are not performed automatically from this local directory.
2. Start with a candidate 48 GB or 80 GB NVIDIA GPU, CUDA 13-compatible host driver and 200 GB container disk. Neither VRAM minimum nor performance has been validated. For repeated use attach persistent storage at `/workspace`.
3. Inspect `config/runpod-template.json`. Generate its full payload with `python3 scripts/create-runpod-template.py`. With `RUNPOD_API_KEY` in the environment, `python3 scripts/create-runpod-template.py --apply` creates or updates the private template. It always uses the model-version tag from that file, which every passing `develop` build moves forward, so the template never needs re-pointing; digests and `sha-<commit>` tags are refused. To freeze one Pod on a build, set its image to a `sha-<commit>` tag by hand. No API keys are embedded in its payload.
4. Expose HTTP 8188 for ComfyUI and optional HTTP 3923 for the read-only output file browser. Configure Runpod secrets `COPYPARTY_USERNAME` and `COPYPARTY_SECRET` to enable 3923. Without both, the file browser stays off. Protect access to ComfyUI using your Runpod proxy/access configuration.
5. Set `MODEL_MODE` to one of `remix, standard, turbo` or `all`. Optional `HF_TOKEN` must be supplied privately if a repository requires acceptance. Startup resumes downloads, verifies SHA256 (once per file; later boots reuse the record while the file's inode, size, mtime and ctime are unchanged), installs only selected versioned workflows and then launches ComfyUI. It preserves edited workflows across restarts. Download progress is not generation progress.

`VIDEO_VERSION=2.2` identifies this image; changing it cannot switch to a different model generation. New generations get their own version directory and image tag. Models, inputs, outputs and users live under `/workspace/ComfyUI`; scripts/core live under `/opt`. Container disk data disappears when the Pod is deleted unless backed up. The image does not contain weights or credentials.

## Runtime options

- `COMFYUI_ATTENTION=pytorch`: supported default. `sage` is an opt-in speed experiment (Triton SageAttention 1.0.6). It runs a GPU kernel check at boot and falls back to PyTorch with a warning if that fails. Compare quality before adopting it. Other values fail explicitly.
- `COMFYUI_FAST`: optional, space-separated ComfyUI `--fast` features (`fp16_accumulation fp8_matrix_mult cublas_ops autotune`). Off by default because upstream labels them potentially quality-reducing. `fp8_matrix_mult` is the relevant candidate for WAN's FP8 weights on Ada/Hopper/Blackwell.
- `VERIFY_MODELS=full`: re-hash every selected weight on this boot instead of trusting the verification record.
- `COMFYUI_RESERVE_VRAM`: optional ComfyUI reserved VRAM in GB. Native offloading remains enabled.
- `OMP_NUM_THREADS`, `MKL_NUM_THREADS`: optional overrides; defaults honor cgroup CPU quota and affinity. OpenBLAS/NumExpr use the same budget unless overridden; tokenizer parallelism is off.
- `COMFYUI_DIR`: optional persistent root, default `/workspace/ComfyUI`.

No attention cache, sparse attention or torch.compile is enabled by default. No extra acceleration LoRA is added to Eros or Remix checkpoints with acceleration already merged. Python dependency versions resolved during the image build are recorded in `/opt/python-lock.txt`; the transitive dependency set is not yet fully locked before build.

## Validation and maintenance

Run `python3 tests/test-bundle.py`, `bash tests/test-cpu-threads.sh`, and `python3 scripts/build-workflows.py`. Workflow generation is deterministic and uses no network. Check generated files into version control. `scripts/smoke-schemas.py` runs inside the built image and checks API input names, required inputs, combo choices and link types against actual ComfyUI schemas without downloading weights.

See [research and adapter decisions](docs/research.md) for sources, sampling details, the existing projects' acceleration inventory and the GPU evaluation matrix. See [validation status](docs/VALIDATION.md) for what has actually been tested. Eros and Remix are experimental integrations until a real generation passes; source and schema checks cannot establish temporal quality, identity fidelity or audio synchronization.

## Releases and Runpod Hub

Pushes to `main` build and CPU-smoke-test containers before publishing model-version and immutable commit tags to GHCR. A `v*` Git tag repeats these checks, publishes a matching container tag, and creates a GitHub release with versioned UI/API workflow ZIPs, a Runpod template payload and SHA256 checksums. Container tags describe bundle releases separately from model versions.

Runpod Hub publication uses the released image after image smoke checks. GPU quality and performance require separate Runpod generation tests. See release notes for the exact validation scope.

Images follow the model version, like the LTX (`ltx-studio:2.5`) and Eros (`eros-comfyui:1.5`) bundles: every passing build of `develop` publishes `ghcr.io/acdevmedia/wan-comfyui:2.2` plus an immutable `sha-<commit>` tag for pinning or rollback. Hub submission and public Pod template publication wait for GPU tests. The `.runpod` files are prepared for that later submission.

For private test Pods, the template tool accepts `--registry-auth-id` pointing to an existing Runpod GHCR authorization. Before public Hub submission, make the GHCR package public and verify an anonymous pull; never embed registry passwords or tokens in Hub files.

[Container build and CPU smoke results](https://github.com/acdevmedia/comfyui-wan-video/actions/runs/43521502232). A private test template following the model tag is available; public Hub submission remains deferred.
