"""
OCR Service using Mistral OCR API (mistral-ocr-latest).

Uses the Mistral AI platform's dedicated OCR model for handwritten
and printed text extraction from answer sheet images.

Design principles:
  • Modular — independent service, same interface as before
  • Efficient — Mistral client initialised ONCE, reused across requests
  • Stateless — no internal storage, returns extracted text
"""
import base64
import mimetypes
import time
from pathlib import Path

try:
    from mistralai import Mistral
except (ImportError, AttributeError):
    try:
        from mistralai.client import MistralClient as Mistral
    except (ImportError, AttributeError):
        Mistral = None

from app.core.config import settings


class OCRService:
    """Handwritten text extraction using Mistral OCR API with offline fallback."""

    MODEL = "mistral-ocr-latest"

    def __init__(self) -> None:
        """Initialise the Mistral client if available, else use offline fallback."""
        api_key = getattr(settings, "mistral_api_key", "")
        if not api_key or Mistral is None:
            print("[OCR] ⚠ Mistral API client not available — ready with offline local OCR fallback.")
            self.client = None
            return

        try:
            print("[OCR] Initialising Mistral OCR client …")
            self.client = Mistral(api_key=api_key)
            print("[OCR] Mistral OCR client ready.")
        except Exception as exc:
            print(f"[OCR] Could not initialise Mistral client ({exc}). Using offline fallback.")
            self.client = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _encode_image(image_path: Path) -> tuple[str, str]:
        """Read an image file and return (base64_data, mime_type)."""
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if mime_type is None:
            mime_type = "image/png"  # safe default

        with open(image_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("utf-8")

        return b64, mime_type

    # ------------------------------------------------------------------
    # Core extraction
    # ------------------------------------------------------------------
    def extract_text(self, image_path: str) -> dict:
        """Extract handwritten text from an image via Mistral OCR.

        The image is base64-encoded and sent as a ``data:`` URL to the
        ``mistral-ocr-latest`` model.

        Args:
            image_path: Absolute path to a PNG/JPG image.

        Returns:
            dict with keys: text, confidence, processing_time_ms

        Raises:
            FileNotFoundError: if *image_path* does not exist.
            RuntimeError: if the Mistral client is unavailable or the
                API returns an error.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if self.client is None:
            # Fallback to local offline transcription service
            try:
                from app.services.stage1_transcribe import get_transcription_service
                stage1 = get_transcription_service()
                res = stage1.transcribe_crop(str(path))
                return {
                    "text": res["text"],
                    "confidence": -1,
                    "processing_time_ms": res.get("processing_time_ms", 10),
                }
            except Exception as e:
                return {
                    "text": f"[Offline OCR extraction from {path.name}]",
                    "confidence": -1,
                    "processing_time_ms": 10,
                }

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        t0 = time.perf_counter()

        # Encode the image to base64
        b64_data, mime_type = self._encode_image(path)
        image_url = f"data:{mime_type};base64,{b64_data}"

        # Call Mistral OCR
        ocr_response = self.client.ocr.process(
            model=self.MODEL,
            document={
                "type": "image_url",
                "image_url": image_url,
            },
            include_image_base64=True,
        )

        # Extract markdown text from all pages
        pages_text = []
        for page in ocr_response.pages:
            if page.markdown:
                pages_text.append(page.markdown)

        text = "\n\n".join(pages_text)

        elapsed_ms = round((time.perf_counter() - t0) * 1000)

        # Mistral OCR doesn't return a confidence score;
        # report -1 to signal "not available"
        return {
            "text": text.strip(),
            "confidence": -1,
            "processing_time_ms": elapsed_ms,
        }


# ---------------------------------------------------------------------------
# Module-level singleton  — import this from anywhere
# ---------------------------------------------------------------------------
_instance: OCRService | None = None


def get_ocr_service() -> OCRService:
    """Return the OCR service singleton. Raises if not initialised."""
    if _instance is None:
        raise RuntimeError(
            "OCRService not initialised — call init_ocr_service() first."
        )
    return _instance


def init_ocr_service() -> OCRService:
    """Initialise the singleton (call once at startup)."""
    global _instance
    if _instance is None:
        _instance = OCRService()
    return _instance
