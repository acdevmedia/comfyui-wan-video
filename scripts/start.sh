#!/usr/bin/env bash
set -Eeuo pipefail
source /opt/video/scripts/cpu-threads.sh
configure_cpu_threads
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-$OMP_NUM_THREADS}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-$OMP_NUM_THREADS}"
export TOKENIZERS_PARALLELISM=false
root="${COMFYUI_DIR:-/workspace/ComfyUI}"
mkdir -p "$root"/{models,input,output,user}
# Shared volumes must not have two provisioning processes writing the same weights.
exec 9>"$root/.video-provision.lock"
flock 9
python3 /opt/video/scripts/provision.py
flock -u 9
exec 9>&-
source /opt/video/scripts/copyparty.sh
start_copyparty "$root/output" "ACDEV Video Outputs"
args=()
case "${COMFYUI_ATTENTION:-pytorch}" in
 pytorch) args+=(--use-pytorch-cross-attention) ;;
 sage)
  # Opt-in speed experiment. Fall back rather than serve NaNs if the Triton kernel
  # cannot compile or run on this GPU/driver.
  if timeout 300 python3 -c 'import torch; from sageattention import sageattn; q=torch.randn(1,8,256,128,device="cuda",dtype=torch.bfloat16); o=sageattn(q,q,q,tensor_layout="HND",is_causal=False); torch.cuda.synchronize(); assert o.isfinite().all()'; then
   args+=(--use-sage-attention)
  else
   echo '[attention] WARNING: SageAttention failed its GPU check; using PyTorch attention instead.' >&2
   args+=(--use-pytorch-cross-attention)
  fi ;;
 *) echo 'COMFYUI_ATTENTION must be pytorch (default) or sage.' >&2; exit 2 ;;
esac
echo "[attention] ComfyUI starts with ${args[0]}."
if [[ -n "${COMFYUI_RESERVE_VRAM:-}" ]]; then args+=(--reserve-vram "$COMFYUI_RESERVE_VRAM"); fi
# Optional ComfyUI --fast features, space separated (e.g. "fp8_matrix_mult"). Off by default:
# upstream labels them potentially quality-reducing. Unknown names make ComfyUI exit.
if [[ -n "${COMFYUI_FAST:-}" ]]; then read -ra fast <<< "$COMFYUI_FAST"; args+=(--fast "${fast[@]}"); fi
exec python3 /opt/ComfyUI/main.py --listen 0.0.0.0 --port 8188 --base-directory "$root" --input-directory "$root/input" --output-directory "$root/output" --user-directory "$root/user" "${args[@]}"
