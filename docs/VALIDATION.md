# Validation status

Checked 13 November 2026.

Passed locally: control frame-grid rounding and dimension/range rejection; backend random seed generation; manifest revision/hash structure; UI/API graph link consistency; model filename coverage; no duplicate acceleration adapters on merged Eros/Remix; Docker context excludes credentials; CPU quota/affinity/override fixtures; deterministic regeneration; Python compilation and shell syntax; current pinned ComfyUI proxy-guard patch application. PyTorch CUDA 13 wheel versions and the CUDA image digest were checked against upstream registries.

Local Docker attempt: `docker info` could not connect to the Docker Desktop daemon. No image build was started. Pinned upstream node input names were additionally checked from the exact ComfyUI source revision.

Also passed locally: Video controls are deterministic and the separate seed node is the only uncached input to sampling and saving; real-CFG negatives carry the reference image; the provisioner hashes once, skips re-hashing while the file is unchanged, re-hashes after a rewrite, forces a re-download of a corrupt file and honors `VERIFY_MODELS=full` (stubbed Hub download).

Not run: Docker image build, image-time ComfyUI schema smoke test, authenticated Copyparty integration test, frontend browser import/playback, actual model loading, Runpod deployment, GPU generation, peak VRAM, timing, reference fidelity and H3 audio synchronization. CI definitions for image build/schema/file-browser tests are included, but this is not a record that CI passed. No model weights were downloaded locally.

Before deployment, run the image checks and the generation/restart matrix in research.md. Use separate measured results for standard H3, each H3 turbo, Eros beta7 fix1, standard WAN, WAN turbo and Remix v3. No benchmark or compatibility claim transfers automatically between them.

First GitHub image build: installation and all live ComfyUI API schema checks passed. The output-download smoke test then caught a missing `unzip` executable. The Dockerfile now installs zip/unzip; a candidate rebuild must pass the entire test sequence before release publication.
