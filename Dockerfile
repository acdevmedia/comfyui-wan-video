FROM nvidia/cuda:13.0.2-runtime-ubuntu24.04@sha256:6a0e31b59e70890446f2c17356d6efc0d54260090a8c63d6ca7c2ad049db95d2
LABEL org.opencontainers.image.source="https://github.com/acdevmedia/comfyui-wan-video"
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive PATH=/opt/venv/bin:$PATH VIDEO_VERSION=2.2 MODEL_MODE=turbo COMFYUI_ATTENTION=pytorch HF_HOME=/workspace/.cache/huggingface PYTHONUNBUFFERED=1 HF_HUB_DISABLE_TELEMETRY=1 HF_XET_HIGH_PERFORMANCE=1
# gcc/libc6-dev/python3-dev let Triton build its launcher at runtime for opt-in SageAttention.
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv git curl ca-certificates ffmpeg libgl1 libglib2.0-0 tini util-linux zip unzip gcc libc6-dev python3-dev && rm -rf /var/lib/apt/lists/* && python3 -m venv /opt/venv
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu130 torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0
RUN mkdir /opt/ComfyUI && curl -fsSL https://github.com/Comfy-Org/ComfyUI/archive/46659e65e95920e5d29cae011b43b02699c0bfd3.tar.gz | tar xz --strip-components=1 -C /opt/ComfyUI && pip install --no-cache-dir -r /opt/ComfyUI/requirements.txt huggingface_hub==2.3.0 copyparty==1.20.26 sageattention==1.0.6 && pip check && python3 -c 'import hf_xet, sageattention, triton' && pip freeze > /opt/python-lock.txt
# Isolate AWS CLI dependencies from the ComfyUI environment.
RUN python3 -m venv /opt/awscli && /opt/awscli/bin/pip install --no-cache-dir 'awscli==1.46.3' && \
    ln -s /opt/awscli/bin/aws /usr/local/bin/aws && aws --version
COPY scripts /opt/video/scripts
COPY versions /opt/video/versions
COPY custom_nodes/acdev_video /opt/ComfyUI/custom_nodes/acdev_video
RUN python3 /opt/video/scripts/patch-comfyui-proxy-guard.py /opt/ComfyUI/server.py
WORKDIR /opt/ComfyUI
EXPOSE 8188 3923
HEALTHCHECK --interval=30s --timeout=5s --start-period=30m CMD curl -fsS http://localhost:8188/system_stats || exit 1
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "bash", "/opt/video/scripts/start.sh"]
