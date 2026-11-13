# WAN 2.2 I2V-A14B ComfyUI Runpod bundle

Version profile: `versions/2.2/`. Bundle revision: `0.1.0`. Proposed image: `ghcr.io/acdevmedia/wan-comfyui:2.2`. **Source-ready; image build, Runpod deployment and GPU generation are pending.**

Available modes: standard (20 steps), turbo (four steps with matched high/low LightX2V adapters), remix (v3.0 checkpoints; experimental 12-step publisher-example schedule). Default: `turbo`. Use `MODEL_MODE=all` only when you want every workflow and its model downloads. Normal selected-mode downloads are approximately 36–42 GB, depending on the family and mode.

All workflows include one Video controls node: editable width/height, duration or frame count, positive prompt, and a prefilled editable negative prompt. Seeds randomize in the backend on every queued job, including API jobs, and the actual seed is saved in MP4 metadata. Turbo/Remix CFG 1 omits negative guidance; the workflow labels this. Standard CFG enables it and requires quality validation.

WAN uses 16 fps with `4k+1` frames; H3 uses 24 fps with `17k+5`. A five-second request rounds up to 81 / 124 frames respectively. Dimensions must be multiples of 32. Upload your own reference image into Load Image before queueing; `reference.png` is a placeholder, not a packaged asset. H3 also generates audio from the positive prompt. The Videos & Audio button opens recent outputs inside ComfyUI.

## Build and launch

1. Put this directory in its own GitHub repository. The included Actions workflow validates source, builds the image, starts ComfyUI in CPU mode to check node schemas, tests the authenticated output browser, and publishes version and immutable `sha-<commit>` image tags. Builds are not performed automatically from this local directory.
2. Start with a candidate 48 GB or 80 GB NVIDIA GPU, CUDA 13-compatible host driver and 200 GB container disk. Neither VRAM minimum nor performance has been validated. For repeated use attach persistent storage at `/workspace`.
3. Inspect `config/runpod-template.json`. Generate its full payload with `python3 scripts/create-runpod-template.py`. After the image is published and tested, use `RUNPOD_API_KEY` in the environment with `python3 scripts/create-runpod-template.py --apply --image <published-image-or-digest>` to create or update the private template. No API keys are embedded in its payload. The checked-in image name is a proposed destination, not a claimed published image.
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

Initial test releases use `v0.1.0-rc.2` and are marked prerelease. Hub submission and public Pod template publication wait for GPU tests. The `.runpod` files are prepared for that later submission.

Hub serves ComfyUI through the load-balanced proxy at 8000, with readiness at 8001. This readiness test does not generate a video.
