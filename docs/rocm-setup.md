# ROCm Setup Guide — AMD RX 7700 XT on Ubuntu 24.04

This guide documents the exact steps to get ROCm 7.x, PyTorch, and Ollama running
on an AMD Radeon RX 7700 XT (gfx1101) on Ubuntu 24.04.4 LTS. This is the environment
used to develop and run infra-copilot.

## Hardware

| Component | Spec |
|---|---|
| GPU | AMD Radeon RX 7700 XT (gfx1101, RDNA3) |
| VRAM | 12GB GDDR6 |
| CPU | AMD Ryzen 7 8700F |
| RAM | 32GB DDR5 |
| OS | Ubuntu 24.04.4 LTS |
| Kernel | 6.11.0-29-generic |

---

## 1. Verify GPU detection

Before installing anything, confirm the kernel already sees your GPU:

```bash
lspci | grep -i vga
```

Expected output:
XX:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Navi 32 [Radeon RX 7700/7800 XT]

---

## 2. Add user to required groups

ROCm requires your user to be in the `render` and `video` groups:

```bash
sudo usermod -aG render,video $USER
```

> **Important:** This does not take effect until you log out and back in, or run `newgrp render`.

---

## 3. Install ROCm

Download and install the AMD GPU installer helper:

```bash
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/noble/amdgpu-install_7.2.3.70203-1_all.deb
sudo apt install -y ./amdgpu-install_7.2.3.70203-1_all.deb
```

Install ROCm. Use `--no-dkms` because Ubuntu 24.04 already ships the `amdgpu` kernel
module — no need to recompile:

```bash
sudo amdgpu-install -y --usecase=rocm --no-dkms
```

This downloads several hundred MB of ROCm packages. It takes 5-10 minutes.

---

## 4. Verify ROCm

```bash
rocminfo | grep -A 10 "Agent 2"
```

Expected output (look for your GPU as Agent 2):
Agent 2

Name:                    gfx1101
Marketing Name:          AMD Radeon RX 7700 XT
Vendor Name:             AMD
Feature:                 KERNEL_DISPATCH
Device Type:             GPU
Compute Unit:            54
Fast F16 Operation:      TRUE

Also verify with:
```bash
rocm-smi
```

---

## 5. Install PyTorch with ROCm

Create a dedicated Python virtual environment and install the ROCm build of PyTorch:

```bash
python3 -m venv ~/.venvs/ml
source ~/.venvs/ml/bin/activate
pip install --index-url https://download.pytorch.org/whl/rocm6.3 torch torchvision torchaudio
```

Verify GPU access:

```bash
# Apply group changes without logging out
newgrp render

source ~/.venvs/ml/bin/activate
python3 -c "
import torch
print('PyTorch version:', torch.__version__)
print('GPU available:', torch.cuda.is_available())
print('GPU name:', torch.cuda.get_device_name(0))
"
```

Expected output:
PyTorch version: 2.9.1+rocm6.3
GPU available: True
GPU name: AMD Radeon RX 7700 XT

> **Note:** If `GPU available: False`, make sure you ran `newgrp render` or logged out
> and back in after the `usermod` command in step 2.

---

## 6. Install Ollama

Ollama auto-detects ROCm and uses the GPU automatically:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

During installation you should see:



AMD GPU ready.




Verify:
```bash
ollama --version
# ollama version is 0.24.0
```

Pull and test the model:
```bash
ollama pull qwen2.5-coder:14b
ollama run qwen2.5-coder:14b "Reply in one sentence: what is Kubernetes?"
```

---

## Troubleshooting

### GPU available: False in PyTorch

Run `newgrp render` or log out and back in. The `render` group must be active in
your current shell session.

### rocminfo shows CPU only

ROCm did not install correctly. Try:
```bash
sudo amdgpu-install --uninstall
sudo amdgpu-install -y --usecase=rocm --no-dkms
```

### amdgpu-install .deb 404 Not Found

The version number in the URL may have changed. Check the current version at:
https://repo.radeon.com/amdgpu-install/latest/ubuntu/noble/

### Ollama does not use GPU

Verify ROCm is installed and run:
```bash
rocm-smi
ollama run qwen2.5-coder:14b "hello"
# Check GPU memory usage in rocm-smi while model loads
```

---

## References

- [ROCm Linux installation docs](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/)
- [PyTorch ROCm installation](https://rocm.docs.amd.com/projects/radeon/en/latest/docs/install/install-pytorch.html)
- [Ollama AMD GPU support](https://ollama.com)
- [ROCm GitHub issues](https://github.com/ROCm/ROCm/issues)
