# Validation status

Checked 13 November 2026.

Container build and all CPU smoke checks passed for release candidate `v0.1.0-rc.2`: [GitHub Actions](https://github.com/acdevmedia/comfyui-wan-video/actions/runs/43521502232). Both image installation and ComfyUI startup succeeded. Every packaged API workflow passed live node-schema validation. Authenticated output listing, downloads, thumbnails, ZIP downloads and read-only access checks passed; zip/unzip and AWS CLI are installed, and `aws --version` succeeds. Source control/frame-grid/seed/hash-cache tests and CPU thread quota tests also passed.

Release images are public in GHCR; anonymous manifest access was verified. A private, digest-pinned Runpod test template has been created. Creating the template does not start a Pod or incur GPU usage.

Image digest: `ghcr.io/acdevmedia/wan-comfyui@sha256:622680e3baade3efc5a1d0f530262588e56aba7e00b5661ad1f44f010696b806`.

Not yet validated: GPU weight loading/generation, peak VRAM, timing, warm re-roll caching on GPU, reference fidelity, frontend playback, and H3 audio synchronization. No GPU performance or minimum-VRAM claim follows from these CPU results. Public template/Hub submission remains deferred until GPU tests pass.
