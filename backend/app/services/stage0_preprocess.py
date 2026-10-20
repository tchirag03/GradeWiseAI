"""
Stage 0: Preprocessing & Layout Segmentation Service.
Uses OpenCV for deskewing & contrast normalization, and Surya/heuristic layout
analysis to segment text and diagrams into crops to minimize token counts.
"""
import os
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None


class PreprocessingService:
    """Stage 0 Preprocessing & Layout detection."""

    def __init__(self) -> None:
        self._surya_model = None
        self._surya_processor = None
        self._surya_available = False
        self._init_layout_model()

    def _init_layout_model(self) -> None:
        """Attempt to load Surya layout detection model if installed."""
        try:
            from surya.layout import load_predictor
            print("[Stage 0] Loading Surya layout predictor...")
            self._surya_predictor = load_predictor()
            self._surya_available = True
            print("[Stage 0] Surya layout predictor ready.")
        except Exception as exc:
            print(f"[Stage 0] Surya layout not loaded ({exc}). Using OpenCV contour fallback.")
            self._surya_available = False

    # ------------------------------------------------------------------
    # 1. OpenCV Preprocessing: Deskew & Contrast
    # ------------------------------------------------------------------
    @staticmethod
    def deskew_and_normalize(image_path: str) -> np.ndarray:
        """
        Deskew image and apply contrast enhancement (CLAHE).
        Maintains grayscale — does NOT binarize, as VLMs prefer rich grayscale.
        """
        if cv2 is None:
            # Fallback if cv2 not available: open with PIL
            img_pil = Image.open(image_path).convert("L")
            return np.array(img_pil)

        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        # 1. Deskew using Hough lines / minimum area rectangle
        coords = np.column_stack(np.where(img < 240))
        if coords.size > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            if abs(angle) > 0.5 and abs(angle) < 45:
                (h, w) = img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img = cv2.warpAffine(
                    img, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )

        # 2. Contrast Enhancement with CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        normalized = clahe.apply(img)

        return normalized

    # ------------------------------------------------------------------
    # 2. Layout Segmentation & Cropping
    # ------------------------------------------------------------------
    def detect_and_crop(
        self,
        image_path: str,
        evaluation_id: str,
        sheet_id: str,
        base_upload_dir: str = "uploads",
    ) -> list[dict[str, Any]]:
        """
        Detects text regions vs diagram regions, crops them, and saves sub-images.
        Returns list of crop dictionaries:
          [{"crop_id": ..., "crop_type": "text"|"figure", "crop_path": ..., "bbox": [y1, x1, y2, x2]}]
        """
        processed_mat = self.deskew_and_normalize(image_path)
        h, w = processed_mat.shape[:2]

        # Directory to store crops for this sheet
        crop_dir = Path(base_upload_dir) / evaluation_id / "crops" / str(sheet_id)
        crop_dir.mkdir(parents=True, exist_ok=True)

        # Save the normalized full image as reference
        clean_full_path = crop_dir / "clean_full.png"
        if cv2 is not None:
            cv2.imwrite(str(clean_full_path), processed_mat)
        else:
            Image.fromarray(processed_mat).save(str(clean_full_path))

        crops_meta: list[dict[str, Any]] = []

        if self._surya_available:
            crops_meta = self._crop_with_surya(clean_full_path, crop_dir, processed_mat)
        else:
            crops_meta = self._crop_with_opencv_heuristics(crop_dir, processed_mat)

        # If no sub-regions found, fallback to the entire clean page as a text crop
        if not crops_meta:
            crops_meta.append({
                "crop_id": f"{sheet_id}_full",
                "crop_type": "text",
                "crop_path": str(clean_full_path),
                "bbox": [0, 0, h, w],
            })

        return crops_meta

    def _crop_with_surya(
        self,
        clean_img_path: Path,
        crop_dir: Path,
        processed_mat: np.ndarray
    ) -> list[dict[str, Any]]:
        """Use Surya layout analysis to identify text blocks vs diagram/figures."""
        pil_img = Image.open(clean_img_path)
        preds = self._surya_predictor([pil_img])
        layout_pred = preds[0]

        crops = []
        for i, box in enumerate(layout_pred.bboxes):
            # box format in surya: [x1, y1, x2, y2], label in box.label
            label = getattr(box, "label", "text").lower()
            x1, y1, x2, y2 = [int(v) for v in box.bbox]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(processed_mat.shape[1], x2), min(processed_mat.shape[0], y2)

            if (x2 - x1) < 20 or (y2 - y1) < 20:
                continue

            crop_type = "figure" if any(k in label for k in ["figure", "picture", "drawing"]) else "text"
            cropped_mat = processed_mat[y1:y2, x1:x2]

            crop_file = crop_dir / f"crop_{i}_{crop_type}.png"
            if cv2 is not None:
                cv2.imwrite(str(crop_file), cropped_mat)
            else:
                Image.fromarray(cropped_mat).save(str(crop_file))

            crops.append({
                "crop_id": f"crop_{i}_{crop_type}",
                "crop_type": crop_type,
                "crop_path": str(crop_file),
                "bbox": [y1, x1, y2, x2],
            })
        return crops

    def _crop_with_opencv_heuristics(
        self,
        crop_dir: Path,
        processed_mat: np.ndarray
    ) -> list[dict[str, Any]]:
        """
        Contour and density-based fallback segmentation.
        Distinguishes wide text bands from dense/isolated diagram regions.
        """
        if cv2 is None:
            return []

        h, w = processed_mat.shape[:2]
        # Otsu thresholding for contour detection
        _, thresh = cv2.threshold(processed_mat, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Dilate to connect nearby text lines into paragraphs/sections
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 9))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        crops = []
        # Sort contours top-to-bottom
        contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[1])

        for i, cnt in enumerate(contours):
            x, y, cw, ch = cv2.boundingRect(cnt)
            # Filter out tiny noise marks
            if cw < 60 or ch < 35:
                continue

            aspect_ratio = cw / float(ch)
            area = cw * ch
            total_area = float(h * w)

            # Heuristic: diagrams/trees typically have aspect ratio closer to square (0.6 - 1.8)
            # and occupy a significant area, whereas text lines are wide and flatter.
            crop_type = "figure" if (0.5 <= aspect_ratio <= 1.8 and area > 0.05 * total_area) else "text"

            cropped = processed_mat[y:y + ch, x:x + cw]
            crop_file = crop_dir / f"crop_{i}_{crop_type}.png"
            cv2.imwrite(str(crop_file), cropped)

            crops.append({
                "crop_id": f"crop_{i}_{crop_type}",
                "crop_type": crop_type,
                "crop_path": str(crop_file),
                "bbox": [y, x, y + ch, x + cw],
            })

        return crops


# Module-level singleton
_stage0_instance: PreprocessingService | None = None


def get_preprocessing_service() -> PreprocessingService:
    global _stage0_instance
    if _stage0_instance is None:
        _stage0_instance = PreprocessingService()
    return _stage0_instance
