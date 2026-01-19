#!/usr/bin/env python3
"""
Diagnostic script to check which compute types are supported by faster-whisper
on your system.
"""

import sys
from faster_whisper import WhisperModel

def test_compute_type(model_size: str, compute_type: str, device: str = "auto") -> tuple[bool, str]:
    """Test if a specific compute type works."""
    try:
        print(f"  Testing {compute_type}...", end=" ", flush=True)
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print("✓ SUPPORTED")
        return True, ""
    except Exception as e:
        error_msg = str(e)
        print(f"✗ NOT SUPPORTED: {error_msg[:80]}")
        return False, error_msg

def main():
    print("=" * 70)
    print("faster-whisper Compute Type Compatibility Checker")
    print("=" * 70)
    print()
    
    # Test with the smallest model for speed
    test_model = "tiny"
    
    print(f"Testing with model: {test_model}")
    print(f"Device: auto (will detect CPU/CUDA/MPS)")
    print()
    
    # Common compute types to test
    compute_types = [
        "int8",
        "int8_float16",
        "int8_float32",
        "float16",
        "float32",
        "auto",  # Let faster-whisper decide
    ]
    
    supported = []
    unsupported = []
    
    for ct in compute_types:
        works, error = test_compute_type(test_model, ct)
        if works:
            supported.append(ct)
        else:
            unsupported.append((ct, error))
    
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    
    if supported:
        print("✓ SUPPORTED compute types:")
        for ct in supported:
            print(f"  - {ct}")
        print()
    
    if unsupported:
        print("✗ UNSUPPORTED compute types:")
        for ct, error in unsupported:
            print(f"  - {ct}")
            if "int8_float16" in error:
                print(f"    → This typically means your device doesn't support mixed precision")
        print()
    
    print("RECOMMENDATION:")
    if "int8" in supported:
        print("  → Use 'int8' for best performance (fastest, lower memory)")
    elif "float16" in supported:
        print("  → Use 'float16' for good performance (fast, moderate memory)")
    elif "float32" in supported:
        print("  → Use 'float32' (slower but most compatible)")
    elif "auto" in supported:
        print("  → Use 'auto' to let faster-whisper choose automatically")
    else:
        print("  → No compute types supported! Check your faster-whisper installation.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
