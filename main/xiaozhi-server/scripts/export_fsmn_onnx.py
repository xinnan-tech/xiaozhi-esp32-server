#!/usr/bin/env python3
"""
Export FSMN VAD model to ONNX format for faster inference on CPU.

Usage:
    python scripts/export_fsmn_onnx.py

Output:
    ./models/fsmn_vad_onnx/  - ONNX model files
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def export_fsmn_to_onnx(
    model_name: str = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    model_revision: str = "v2.0.4",
    output_dir: str = "./models/fsmn_vad_onnx",
    quantize: bool = True,
    device: str = "cpu",
):
    """
    Export FSMN VAD model to ONNX format.
    
    Args:
        model_name: ModelScope model name
        model_revision: Model revision/version
        output_dir: Output directory for ONNX files
        quantize: Whether to quantize to INT8 (smaller, faster on CPU)
        device: Device for loading PyTorch model
    """
    from funasr import AutoModel
    
    print(f"Loading FSMN VAD model: {model_name} (revision: {model_revision})")
    print(f"Device: {device}")
    
    # Load PyTorch model
    model = AutoModel(
        model=model_name,
        model_revision=model_revision,
        device=device,
        disable_pbar=False,
    )
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nExporting to ONNX...")
    print(f"  Output directory: {output_dir}")
    print(f"  Quantize (INT8): {quantize}")
    
    # Export to ONNX
    res = model.export(
        quantize=quantize,
        output_dir=output_dir,
    )
    
    print(f"\n✅ Export success!")
    print(f"   ONNX files saved to: {output_dir}")
    
    # List exported files
    print(f"\nExported files:")
    for f in Path(output_dir).glob("*"):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name} ({size_mb:.2f} MB)")
    
    return res


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export FSMN VAD to ONNX")
    parser.add_argument(
        "--model", 
        default="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        help="ModelScope model name"
    )
    parser.add_argument(
        "--revision", 
        default="v2.0.4",
        help="Model revision"
    )
    parser.add_argument(
        "--output-dir", 
        default="./models/fsmn_vad_onnx",
        help="Output directory"
    )
    parser.add_argument(
        "--no-quantize", 
        action="store_true",
        help="Disable INT8 quantization (use FP32)"
    )
    parser.add_argument(
        "--device", 
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device for loading model"
    )
    
    args = parser.parse_args()
    
    export_fsmn_to_onnx(
        model_name=args.model,
        model_revision=args.revision,
        output_dir=args.output_dir,
        quantize=not args.no_quantize,
        device=args.device,
    )

