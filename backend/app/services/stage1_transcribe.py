"""
Stage 1: Transcribe Service (Local Document OCR).
Transcribes handwritten text and mathematical expressions into Markdown with LaTeX.
Uses local EasyOCR / local document models for fast CPU throughput with zero cloud dependencies.
"""
import time
from pathlib import Path
from typing import Any
from PIL import Image


class TranscriptionService:
    """Stage 1: High-accuracy handwriting and math transcription on CPU."""

    MODEL_ID = "THUDM/glm-ocr"

    def __init__(self) -> None:
        self.model = None
        self.processor = None
        self.is_loaded = False
        self.easyocr_reader = None
        self._init_easyocr()
        self._try_load_model()

    def _init_easyocr(self) -> None:
        """Initialize EasyOCR CPU reader for offline handwritten text extraction."""
        try:
            import easyocr
            print("[Stage 1] Initializing local EasyOCR engine for CPU...")
            self.easyocr_reader = easyocr.Reader(["en"], gpu=False)
            print("[Stage 1] Local EasyOCR engine ready.")
        except Exception as exc:
            print(f"[Stage 1] EasyOCR not loaded ({exc}).")
            self.easyocr_reader = None

    def _try_load_model(self) -> None:
        """Attempt to load custom document model weights if provisioned."""
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
            import torch

            print(f"[Stage 1] Checking local model '{self.MODEL_ID}' (0.9B)...")
            self.processor = AutoProcessor.from_pretrained(
                self.MODEL_ID,
                trust_remote_code=True,
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_ID,
                torch_dtype=torch.float32,
                device_map="cpu",
                trust_remote_code=True,
            )
            self.model.eval()
            self.is_loaded = True
            print("[Stage 1] Dedicated 0.9B model loaded successfully on CPU.")
        except Exception as exc:
            self.is_loaded = False

    def transcribe_crop(self, crop_path: str) -> dict[str, Any]:
        """
        Transcribe a single text crop to text / Markdown.
        """
        path = Path(crop_path)
        if not path.exists():
            raise FileNotFoundError(f"Crop not found: {crop_path}")

        t0 = time.perf_counter()

        if self.is_loaded and self.model and self.processor:
            import torch
            image = Image.open(path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=False,
                )
            generated_text = self.processor.decode(output_ids[0], skip_special_tokens=True)
        elif self.easyocr_reader is not None:
            try:
                lines = self.easyocr_reader.readtext(str(path), detail=0)
                generated_text = "\n".join(lines).strip()
            except Exception as e:
                generated_text = ""
        else:
            generated_text = ""

        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        unclear_count = generated_text.count("[UNCLEAR]") + generated_text.count("?")

        return {
            "text": generated_text.strip(),
            "unclear_tokens": unclear_count,
            "processing_time_ms": elapsed_ms,
        }

    def transcribe_sheet_crops(self, crops: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Transcribes all text crops for a sheet and aggregates the complete document text.
        """
        if not crops:
            return {"transcript": "", "total_unclear": 0, "processing_time_ms": 0, "crops": []}

        t0 = time.perf_counter()
        total_unclear = 0

        # Check if full clean page is available for complete reading order
        first_crop_path = Path(crops[0]["crop_path"])
        clean_full_file = first_crop_path.parent / "clean_full.png"

        full_page_lines: list[str] = []
        if clean_full_file.exists() and self.easyocr_reader is not None:
            try:
                full_page_lines = self.easyocr_reader.readtext(str(clean_full_file), detail=0)
            except Exception as e:
                print(f"[Stage 1] Full page OCR error: {e}")

        # Also transcribe individual crops for region metadata
        text_crops = [c for c in crops if c.get("crop_type") in ("text", "table", "math")]
        crop_texts = []
        for crop in text_crops:
            res = self.transcribe_crop(crop["crop_path"])
            crop["transcription"] = res["text"]
            if res["text"]:
                crop_texts.append(res["text"])
            total_unclear += res["unclear_tokens"]

        # Prefer full page transcription if rich, else combine crops
        if len(full_page_lines) >= len(crop_texts):
            full_transcript = "\n".join(full_page_lines)
        else:
            full_transcript = "\n\n".join(crop_texts)

        elapsed_ms = round((time.perf_counter() - t0) * 1000)

        return {
            "transcript": full_transcript,
            "total_unclear": total_unclear,
            "processing_time_ms": elapsed_ms,
            "crops": crops,
        }


# Module-level singleton
_stage1_instance: TranscriptionService | None = None


def get_transcription_service() -> TranscriptionService:
    global _stage1_instance
    if _stage1_instance is None:
        _stage1_instance = TranscriptionService()
    return _stage1_instance
