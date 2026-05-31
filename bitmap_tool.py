#!/usr/bin/env python3
"""
ESC/POS Thermal Printer Bitmap Conversion Tool
================================================
Production-grade image conversion utility for thermal printers.
Supports SVG, PNG, JPG → ESC/POS raster, C/C++ header, binary, hex output.

Compatible with: ESP32, STM32, AVR, RP2040 + ESC/POS thermal printers over UART.
"""

import argparse
import io
import os
import struct
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class OutputFormat(Enum):
    ESCPOS  = "escpos"
    CHEADER = "cheader"
    BINARY  = "binary"
    HEX     = "hex"
    ALL     = "all"


class DitherMode(Enum):
    NONE          = "none"
    FLOYD_STEINBERG = "floyd-steinberg"
    ATKINSON      = "atkinson"
    ORDERED       = "ordered"


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConversionStats:
    original_width:  int = 0
    original_height: int = 0
    final_width:     int = 0
    final_height:    int = 0
    bytes_per_row:   int = 0
    total_bytes:     int = 0
    compression_ratio: float = 0.0
    processing_time_ms: float = 0.0
    input_format:    str = ""
    dither_mode:     str = ""
    threshold:       int = 128


@dataclass
class ConversionResult:
    preview_image:   Optional[Image.Image] = None
    bitmap_bytes:    bytes = b""
    escpos_stream:   bytes = b""
    cheader_text:    str  = ""
    hex_text:        str  = ""
    stats:           ConversionStats = field(default_factory=ConversionStats)


# ─────────────────────────────────────────────────────────────────────────────
# Dithering algorithms
# ─────────────────────────────────────────────────────────────────────────────

class Ditherer:
    """Collection of dithering algorithms operating on float32 [0,255] arrays."""

    @staticmethod
    def floyd_steinberg(gray: np.ndarray, threshold: int) -> np.ndarray:
        """Classic Floyd-Steinberg error diffusion."""
        img = gray.astype(np.float32).copy()
        h, w = img.shape
        out = np.zeros((h, w), dtype=np.uint8)

        for y in range(h):
            for x in range(w):
                old_px = img[y, x]
                new_px = 0.0 if old_px < threshold else 255.0
                out[y, x] = int(new_px)
                err = old_px - new_px

                if x + 1 < w:
                    img[y,     x + 1] += err * 7 / 16
                if y + 1 < h:
                    if x - 1 >= 0:
                        img[y + 1, x - 1] += err * 3 / 16
                    img[y + 1, x    ] += err * 5 / 16
                    if x + 1 < w:
                        img[y + 1, x + 1] += err * 1 / 16

        return out

    @staticmethod
    def atkinson(gray: np.ndarray, threshold: int) -> np.ndarray:
        """Atkinson dithering (used in early Mac software)."""
        img = gray.astype(np.float32).copy()
        h, w = img.shape
        out = np.zeros((h, w), dtype=np.uint8)

        for y in range(h):
            for x in range(w):
                old_px = img[y, x]
                new_px = 0.0 if old_px < threshold else 255.0
                out[y, x] = int(new_px)
                err = (old_px - new_px) / 8.0

                for dy, dx in [(0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, 0)]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        img[ny, nx] += err

        return out

    @staticmethod
    def ordered(gray: np.ndarray, threshold: int) -> np.ndarray:
        """Ordered (Bayer matrix) dithering – 4×4 Bayer."""
        bayer_4x4 = np.array([
            [ 0, 8, 2,10],
            [12, 4,14, 6],
            [ 3,11, 1, 9],
            [15, 7,13, 5],
        ], dtype=np.float32) / 16.0 * 255.0 - 128.0   # spread ±128

        h, w = gray.shape
        pattern = np.tile(bayer_4x4, (h // 4 + 1, w // 4 + 1))[:h, :w]
        adjusted = gray.astype(np.float32) + pattern * (threshold / 128.0)
        return (adjusted >= threshold).astype(np.uint8) * 255

    @staticmethod
    def none(gray: np.ndarray, threshold: int) -> np.ndarray:
        """Simple fixed-threshold binarisation."""
        return ((gray >= threshold) * 255).astype(np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# Core converter
# ─────────────────────────────────────────────────────────────────────────────

class ESCPOSConverter:
    """
    End-to-end image → ESC/POS bitmap converter.
    All steps follow the spec precisely.
    """

    # ── Ordered dither dispatch ──────────────────────────────────────────────
    _DITHER_MAP = {
        DitherMode.NONE:           Ditherer.none,
        DitherMode.FLOYD_STEINBERG: Ditherer.floyd_steinberg,
        DitherMode.ATKINSON:       Ditherer.atkinson,
        DitherMode.ORDERED:        Ditherer.ordered,
    }

    def __init__(
        self,
        printer_width:    int = 384,
        dither_mode:      DitherMode = DitherMode.FLOYD_STEINBERG,
        threshold:        Optional[int] = None,
        invert:           bool = False,
        preserve_aspect:  bool = True,
        enhance_contrast: bool = True,
        sharpen:          bool = True,
        symbol_name:      str  = "logo",
    ):
        if printer_width % 8 != 0:
            printer_width = ((printer_width + 7) // 8) * 8
        self.printer_width   = printer_width
        self.dither_mode     = dither_mode
        self.threshold       = threshold          # None = auto
        self.invert          = invert
        self.preserve_aspect = preserve_aspect
        self.enhance_contrast = enhance_contrast
        self.sharpen         = sharpen
        self.symbol_name     = symbol_name.upper().replace("-", "_").replace(" ", "_")

    # ── Step 1: Load ──────────────────────────────────────────────────────────
    def _load_image(self, path: Path) -> tuple[Image.Image, str]:
        ext = path.suffix.lower()

        if ext == ".svg":
            try:
                import cairosvg
            except ImportError:
                raise RuntimeError(
                    "cairosvg is required for SVG files.\n"
                    "Install with: pip install cairosvg"
                )
            # Render at 4× target width for crisp quality
            hi_res = self.printer_width * 4
            png_bytes = cairosvg.svg2png(
                url=str(path),
                output_width=hi_res,
            )
            img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
            fmt = "SVG"

        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"):
            img = Image.open(path)
            fmt = ext.lstrip(".").upper()

        else:
            raise ValueError(f"Unsupported format: '{ext}'. Use SVG, PNG, JPG/JPEG.")

        return img, fmt

    # ── Step 2: Resize ────────────────────────────────────────────────────────
    def _resize(self, img: Image.Image) -> Image.Image:
        orig_w, orig_h = img.size

        target_w = self.printer_width
        if self.preserve_aspect:
            ratio    = target_w / orig_w
            target_h = max(1, int(orig_h * ratio))
        else:
            target_h = orig_h

        # Ensure width divisible by 8 (already guaranteed, but double-check)
        target_w = ((target_w + 7) // 8) * 8

        # High-quality downscale
        img = img.resize((target_w, target_h), Image.LANCZOS)
        return img

    # ── Step 3: Grayscale + Enhancement ─────────────────────────────────────
    def _to_gray(self, img: Image.Image) -> Image.Image:
        # Flatten alpha onto white background
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            if img.mode in ("RGBA", "LA"):
                bg.paste(img, mask=img.split()[-1])
            else:
                bg.paste(img)
            img = bg

        gray = img.convert("L")

        if self.enhance_contrast:
            gray = ImageOps.autocontrast(gray, cutoff=2)
            enhancer = ImageEnhance.Contrast(gray)
            gray = enhancer.enhance(1.4)

        if self.sharpen:
            gray = gray.filter(ImageFilter.SHARPEN)
            gray = gray.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

        return gray

    # ── Step 4: Monochrome Conversion ─────────────────────────────────────────
    def _to_mono(self, gray: Image.Image) -> np.ndarray:
        arr = np.array(gray, dtype=np.uint8)

        # Auto threshold: Otsu-like mean-based
        if self.threshold is None:
            mean  = float(arr.mean())
            std   = float(arr.std())
            thr   = int(np.clip(mean - std * 0.1, 64, 200))
        else:
            thr = int(np.clip(self.threshold, 0, 255))

        self._effective_threshold = thr

        fn = self._DITHER_MAP[self.dither_mode]
        mono = fn(arr, thr)            # 0 or 255

        if self.invert:
            mono = 255 - mono

        # Validate: only 0 and 255
        unique = set(mono.flatten().tolist())
        if not unique.issubset({0, 255}):
            raise RuntimeError("Monochrome validation failed: intermediate gray values remain.")

        return mono  # 255 = white, 0 = black

    # ── Step 5: Pack to bitmap bytes ─────────────────────────────────────────
    @staticmethod
    def _pack_bits(mono: np.ndarray) -> bytes:
        """
        Pack monochrome pixels MSB-first.
        white pixel (255) → bit 0
        black pixel (0)   → bit 1
        """
        h, w = mono.shape
        assert w % 8 == 0, "Width must be divisible by 8 before packing."

        # 255=white→0, 0=black→1  (invert for ESC/POS convention)
        bits = (mono == 0).astype(np.uint8)           # shape (h, w)

        # Reshape to (h, w//8, 8) and pack each group MSB-first
        bits_3d = bits.reshape(h, w // 8, 8)
        weights  = np.array([128, 64, 32, 16, 8, 4, 2, 1], dtype=np.uint8)
        packed   = (bits_3d * weights).sum(axis=2).astype(np.uint8)   # (h, w//8)

        return packed.tobytes()

    # ── Step 6a: ESC/POS raster stream ──────────────────────────────────────
    @staticmethod
    def _build_escpos(bitmap: bytes, width_px: int, height_px: int) -> bytes:
        """
        Build complete GS v 0 raster-image command.

        GS v 0 m xL xH yL yH d1 d2 … dk
        m  = 0 (normal density)
        xL,xH = bytes per row  (width_px/8)
        yL,yH = number of rows (height_px)
        """
        bytes_per_row = width_px // 8
        xL = bytes_per_row & 0xFF
        xH = (bytes_per_row >> 8) & 0xFF
        yL = height_px & 0xFF
        yH = (height_px >> 8) & 0xFF

        header = bytes([
            0x1D, 0x76, 0x30,   # GS v 0
            0x00,               # m = normal
            xL, xH,
            yL, yH,
        ])
        return header + bitmap

    # ── Step 6b: C/C++ header ───────────────────────────────────────────────
    def _build_cheader(self, bitmap: bytes, width: int, height: int) -> str:
        name = self.symbol_name
        bpr  = width // 8
        lines = [
            f"/* Auto-generated by ESC/POS Bitmap Tool */",
            f"/* Compatible with ESP32, STM32, AVR, RP2040 */",
            f"",
            f"#ifndef {name}_BITMAP_H",
            f"#define {name}_BITMAP_H",
            f"",
            f"#include <stdint.h>",
            f"",
            f"#define {name}_WIDTH       {width}",
            f"#define {name}_HEIGHT      {height}",
            f"#define {name}_BYTES_PER_ROW {bpr}",
            f"#define {name}_TOTAL_BYTES  {len(bitmap)}",
            f"",
            f"/* Pixel mapping: MSB-first, 1=black, 0=white */",
            f"const uint8_t {name.lower()}Bitmap[{len(bitmap)}] = {{",
        ]

        row_bytes = []
        for i, b in enumerate(bitmap):
            col = i % bpr
            if col == 0:
                row_bytes.append("    ")
            row_bytes.append(f"0x{b:02X}")
            if i < len(bitmap) - 1:
                row_bytes.append(", ")
            if col == bpr - 1:
                row_bytes.append("\n")

        lines.append("".join(row_bytes))
        lines.append("};")
        lines.append("")
        lines.append(f"#endif /* {name}_BITMAP_H */")
        lines.append("")
        return "\n".join(lines)

    # ── Step 6c: Hex text ─────────────────────────────────────────────────────
    @staticmethod
    def _build_hex(bitmap: bytes, bytes_per_row: int) -> str:
        lines = ["# ESC/POS Bitmap Hex Dump", "# Format: MSB-first, 1=black 0=white", ""]
        for i in range(0, len(bitmap), bytes_per_row):
            row = bitmap[i : i + bytes_per_row]
            lines.append(" ".join(f"{b:02X}" for b in row))
        return "\n".join(lines)

    # ── Validation ────────────────────────────────────────────────────────────
    @staticmethod
    def _validate(bitmap: bytes, width: int, height: int):
        bpr      = width // 8
        expected = bpr * height
        if width % 8 != 0:
            raise RuntimeError(f"Validation FAIL: width {width} not divisible by 8.")
        if len(bitmap) != expected:
            raise RuntimeError(
                f"Validation FAIL: expected {expected} bytes, got {len(bitmap)}."
            )

    # ── Public entry point ────────────────────────────────────────────────────
    def convert(self, input_path: str) -> ConversionResult:
        t0   = time.perf_counter()
        path = Path(input_path)

        if not path.exists():
            raise FileNotFoundError(f"Input file not found: '{input_path}'")

        result = ConversionResult()
        stats  = result.stats

        # Step 1 – Load
        img, fmt = self._load_image(path)
        stats.original_width, stats.original_height = img.size
        stats.input_format = fmt

        # Step 2 – Resize
        img = self._resize(img)

        # Step 3 – Grayscale + Enhancement
        gray = self._to_gray(img)
        final_w, final_h = gray.size
        stats.final_width  = final_w
        stats.final_height = final_h

        # Step 4 – Monochrome
        mono_arr = self._to_mono(gray)
        stats.threshold = self._effective_threshold

        # Step 5 – Pack bits
        bitmap = self._pack_bits(mono_arr)

        # Validate
        self._validate(bitmap, final_w, final_h)

        bpr = final_w // 8
        stats.bytes_per_row   = bpr
        stats.total_bytes     = len(bitmap)
        stats.dither_mode     = self.dither_mode.value

        original_size = stats.original_width * stats.original_height
        if original_size > 0:
            stats.compression_ratio = (1.0 - len(bitmap) / original_size) * 100

        # Step 6 – Outputs
        result.bitmap_bytes  = bitmap
        result.escpos_stream = self._build_escpos(bitmap, final_w, final_h)
        result.cheader_text  = self._build_cheader(bitmap, final_w, final_h)
        result.hex_text      = self._build_hex(bitmap, bpr)

        # Preview: white=255 (PIL L mode)
        preview_arr = (mono_arr).astype(np.uint8)   # 255=white, 0=black
        result.preview_image = Image.fromarray(preview_arr, mode="L")

        stats.processing_time_ms = (time.perf_counter() - t0) * 1000
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Batch processor
# ─────────────────────────────────────────────────────────────────────────────

def batch_convert(
    input_paths: list[str],
    output_dir:  str,
    **kwargs,
) -> list[dict]:
    """Convert multiple images, return list of stats dicts."""
    results = []
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for src in input_paths:
        stem = Path(src).stem
        try:
            converter = ESCPOSConverter(symbol_name=stem, **kwargs)
            res       = converter.convert(src)
            _write_outputs(res, out_dir, stem, OutputFormat.ALL)
            results.append({"file": src, "status": "OK", "stats": res.stats})
            print(f"  ✓  {src}  →  {res.stats.final_width}×{res.stats.final_height}  "
                  f"({res.stats.total_bytes} bytes)")
        except Exception as exc:
            results.append({"file": src, "status": "ERROR", "error": str(exc)})
            print(f"  ✗  {src}  →  {exc}", file=sys.stderr)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_outputs(
    result:     ConversionResult,
    out_dir:    Path,
    stem:       str,
    fmt:        OutputFormat,
):
    if fmt in (OutputFormat.ESCPOS, OutputFormat.ALL):
        p = out_dir / f"{stem}.bin"
        p.write_bytes(result.escpos_stream)
        print(f"    ESC/POS raster → {p}")

    if fmt in (OutputFormat.CHEADER, OutputFormat.ALL):
        p = out_dir / f"{stem}.h"
        p.write_text(result.cheader_text, encoding="utf-8")
        print(f"    C/C++ header   → {p}")

    if fmt in (OutputFormat.BINARY, OutputFormat.ALL):
        p = out_dir / f"{stem}_raw.bin"
        p.write_bytes(result.bitmap_bytes)
        print(f"    Raw bitmap     → {p}")

    if fmt in (OutputFormat.HEX, OutputFormat.ALL):
        p = out_dir / f"{stem}.hex"
        p.write_text(result.hex_text, encoding="utf-8")
        print(f"    Hex text       → {p}")

    if result.preview_image is not None:
        p = out_dir / f"{stem}_preview.png"
        result.preview_image.save(p)
        print(f"    Preview PNG    → {p}")


def _print_stats(stats: ConversionStats):
    print()
    print("┌─────────────────────────────────────────┐")
    print("│           Conversion Statistics          │")
    print("├─────────────────────────────────────────┤")
    print(f"│  Input format    : {stats.input_format:<22}│")
    print(f"│  Original size   : {stats.original_width}×{stats.original_height:<20}│")
    print(f"│  Final size      : {stats.final_width}×{stats.final_height:<20}│")
    print(f"│  Bytes per row   : {stats.bytes_per_row:<22}│")
    print(f"│  Total bytes     : {stats.total_bytes:<22}│")
    print(f"│  Dither mode     : {stats.dither_mode:<22}│")
    print(f"│  Threshold       : {stats.threshold:<22}│")
    print(f"│  Compression     : {stats.compression_ratio:.1f}%{'':<19}│")
    print(f"│  Processing time : {stats.processing_time_ms:.1f} ms{'':<17}│")
    print("└─────────────────────────────────────────┘")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="escpos_bitmap_tool",
        description="ESC/POS Thermal Printer Bitmap Conversion Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion (80mm printer, all outputs)
  python escpos_bitmap_tool.py logo.png --width 576

  # 58mm printer, Floyd-Steinberg dithering
  python escpos_bitmap_tool.py logo.svg --width 384 --dither floyd-steinberg

  # Custom threshold, inverted, C header only
  python escpos_bitmap_tool.py logo.jpg --width 384 --threshold 140 \\
      --invert --format cheader

  # Batch conversion
  python escpos_bitmap_tool.py *.png --width 576 --batch --output-dir ./out

  # Ordered dithering, no contrast enhancement
  python escpos_bitmap_tool.py logo.png --width 384 --dither ordered \\
      --no-enhance --no-sharpen
""",
    )

    # ── Positional ────────────────────────────────────────────────────────────
    p.add_argument(
        "input",
        nargs="+",
        metavar="IMAGE",
        help="Input image file(s). Supported: SVG, PNG, JPG/JPEG",
    )

    # ── Required ─────────────────────────────────────────────────────────────
    p.add_argument(
        "--width", "-w",
        type=int,
        default=384,
        metavar="PIXELS",
        help="Target printer width in pixels. Default: 384 (58mm). "
             "Common: 384=58mm, 576=80mm. Must be divisible by 8 (auto-adjusted).",
    )

    # ── Optional ─────────────────────────────────────────────────────────────
    p.add_argument(
        "--format", "-f",
        choices=[f.value for f in OutputFormat],
        default="all",
        metavar="FORMAT",
        help="Output format: escpos|cheader|binary|hex|all. Default: all",
    )

    p.add_argument(
        "--dither", "-d",
        choices=[m.value for m in DitherMode],
        default="floyd-steinberg",
        metavar="MODE",
        help="Dithering: none|floyd-steinberg|atkinson|ordered. Default: floyd-steinberg",
    )

    p.add_argument(
        "--threshold", "-t",
        type=int,
        default=None,
        metavar="0-255",
        help="Binarisation threshold 0-255. Default: auto (Otsu-like).",
    )

    p.add_argument(
        "--invert",
        action="store_true",
        help="Invert black/white output.",
    )

    p.add_argument(
        "--no-preserve-aspect",
        action="store_true",
        help="Do NOT preserve aspect ratio (stretch to width).",
    )

    p.add_argument(
        "--no-enhance",
        action="store_true",
        help="Disable contrast enhancement.",
    )

    p.add_argument(
        "--no-sharpen",
        action="store_true",
        help="Disable edge sharpening.",
    )

    p.add_argument(
        "--output-dir", "-o",
        default="./escpos_output",
        metavar="DIR",
        help="Output directory. Default: ./escpos_output",
    )

    p.add_argument(
        "--name", "-n",
        default=None,
        metavar="SYMBOL_NAME",
        help="C symbol name prefix. Default: derived from filename.",
    )

    p.add_argument(
        "--batch",
        action="store_true",
        help="Batch mode: process all input files, suppress individual prompts.",
    )

    p.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress all output except errors.",
    )

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    # Validate threshold
    if args.threshold is not None and not (0 <= args.threshold <= 255):
        parser.error("--threshold must be between 0 and 255.")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fmt = OutputFormat(args.format)

    common_kwargs = dict(
        printer_width    = args.width,
        dither_mode      = DitherMode(args.dither),
        threshold        = args.threshold,
        invert           = args.invert,
        preserve_aspect  = not args.no_preserve_aspect,
        enhance_contrast = not args.no_enhance,
        sharpen          = not args.no_sharpen,
    )

    # ── Batch mode ────────────────────────────────────────────────────────────
    if args.batch or len(args.input) > 1:
        if not args.quiet:
            print(f"\n=== ESC/POS Batch Conversion ({len(args.input)} files) ===\n")
        batch_convert(args.input, str(out_dir), **common_kwargs)
        if not args.quiet:
            print(f"\nAll outputs written to: {out_dir.resolve()}")
        return

    # ── Single file ───────────────────────────────────────────────────────────
    input_path = args.input[0]
    stem       = args.name or Path(input_path).stem

    if not args.quiet:
        print(f"\n=== ESC/POS Bitmap Converter ===")
        print(f"  Input  : {input_path}")
        print(f"  Width  : {args.width}px")
        print(f"  Dither : {args.dither}")
        print(f"  Output : {out_dir}/")
        print()

    converter = ESCPOSConverter(symbol_name=stem, **common_kwargs)

    try:
        result = converter.convert(input_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR during conversion: {exc}", file=sys.stderr)
        raise

    if not args.quiet:
        _write_outputs(result, out_dir, stem, fmt)
        _print_stats(result.stats)
        print(f"Output directory : {out_dir.resolve()}")
    else:
        _write_outputs(result, out_dir, stem, fmt)


if __name__ == "__main__":
    main()
