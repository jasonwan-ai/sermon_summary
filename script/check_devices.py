#!/usr/bin/env python3
"""
Quick hardware check to report which torch devices are available: CUDA, MPS, CPU.
"""

from __future__ import annotations

import sys
from typing import List

try:
    import torch
except Exception as exc:  # pragma: no cover - import guard
    print("torch is not available; unable to probe CUDA/MPS. Falling back to CPU only.")
    print(f"Import error: {exc}")
    sys.exit(1)


def describe_cuda() -> List[str]:
    if not torch.cuda.is_available():
        return []
    names = []
    for idx in range(torch.cuda.device_count()):
        try:
            names.append(torch.cuda.get_device_name(idx))
        except Exception:  # pragma: no cover - defensive
            names.append(f"GPU {idx}")
    return names


def has_mps() -> bool:
    mps_backend = getattr(torch.backends, "mps", None)
    return bool(mps_backend and mps_backend.is_available())


def main() -> int:
    print("=" * 60)
    print("Device Availability Check")
    print("=" * 60)
    print()

    cuda_devices = describe_cuda()
    mps_available = has_mps()

    if cuda_devices:
        print("✓ CUDA available")
        for i, name in enumerate(cuda_devices):
            print(f"  - GPU {i}: {name}")
    else:
        print("✗ CUDA not available")
    print()

    if mps_available:
        print("✓ MPS available")
    else:
        print("✗ MPS not available")
    print()

    print("✓ CPU available (always)\n")

    recommendations: List[str] = []
    if cuda_devices:
        recommendations.append("Use CUDA for best performance")
    elif mps_available:
        recommendations.append("Use MPS if on Apple Silicon")
    else:
        recommendations.append("Fallback to CPU")

    print("Recommendation:")
    for rec in recommendations:
        print(f"  → {rec}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
