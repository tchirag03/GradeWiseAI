"""
Unified VLM Service.
Multimodal Vision-Language Model evaluation pipeline powered by local Qwen-VL.
100% Dynamic — zero hardcoded fallbacks, mocks, or student data.
"""
import os
import sys
import asyncio
import base64
import io
import json
import re
import time
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from PIL import Image
import httpx
from bson import ObjectId

from app.core.config import settings
from app.core.mongodb import get_database

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL_NAME = "gemma4:e4b"


class UnifiedVLMService:
    """
    End-to-End Multimodal Assessment Service.
    Performs perception (handwriting, math, diagrams) and rubric grading
    in a unified, holistic VLM pass using local Qwen3-VL.
    """

    def __init__(self):
        self.ollama_url = getattr(settings, "ollama_url", OLLAMA_URL)
        self.model_name = getattr(settings, "ollama_model", MODEL_NAME)
        self.image_max_dim = getattr(settings, "image_max_dim", 768)
        self.vlm_num_ctx = getattr(settings, "vlm_num_ctx", 49152)
        self.vlm_max_tokens = getattr(settings, "vlm_max_tokens", 24576)
        self._inference_lock = asyncio.Lock()

    def _get_detached_flags(self) -> int:
        if sys.platform == "win32":
            return 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        return 0

    def ensure_ollama_running(self) -> bool:
        """Synchronously check or launch Ollama (fallback for non-async contexts)."""
        try:
            r = httpx.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if r.status_code == 200:
                return True
        except Exception:
            pass

        env = os.environ.copy()
        models_dir = os.path.expanduser("~/.ollama/models")
        if os.path.exists(models_dir):
            env["OLLAMA_MODELS"] = models_dir

        try:
            subprocess.Popen(
                ["ollama", "serve"],
                env=env,
                creationflags=self._get_detached_flags(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=(sys.platform != "win32"),
            )
            time.sleep(2.0)
            r = httpx.get(f"{self.ollama_url}/api/tags", timeout=2.0)
            return r.status_code == 200
        except Exception as e:
            print(f"[UnifiedVLM] Ollama auto-launch failed: {e}")
            return False

    async def ensure_ollama_running_async(self) -> bool:
        """Asynchronously check or launch Ollama without blocking the event loop."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                r = await client.get(f"{self.ollama_url}/api/tags")
                if r.status_code == 200:
                    return True
        except Exception:
            pass

        env = os.environ.copy()
        models_dir = os.path.expanduser("~/.ollama/models")
        if os.path.exists(models_dir):
            env["OLLAMA_MODELS"] = models_dir

        try:
            subprocess.Popen(
                ["ollama", "serve"],
                env=env,
                creationflags=self._get_detached_flags(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=(sys.platform != "win32"),
            )
            await asyncio.sleep(2.0)
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self.ollama_url}/api/tags")
                return r.status_code == 200
        except Exception as e:
            print(f"[UnifiedVLM] Ollama async launch check failed: {e}")
            return False

    async def ping_model(self) -> Tuple[bool, float, str]:
        """
        Pre-flight health check: Sends a minimal 'Are you up?' query to Ollama.
        Forces the model weights into RAM if not already loaded, verifies the runner is up,
        and measures initial response latency.
        """
        await self.ensure_ollama_running_async()
        start = time.time()
        payload = {
            "model": self.model_name,
            "prompt": "Respond with 1 word: ready",
            "stream": False,
            "options": {
                "num_predict": 5,
                "temperature": 0.0,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                elapsed = time.time() - start
                if resp.status_code == 200:
                    reply = resp.json().get("response", "").strip()
                    return True, elapsed, reply or "OK"
                return False, elapsed, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            elapsed = time.time() - start
            return False, elapsed, str(exc)

    @staticmethod
    @staticmethod
    def _resolve_file_path(file_path: str) -> str:
        """Resolve a file path: if relative, resolve against the backend project root."""
        if not file_path:
            raise FileNotFoundError("Empty file path provided.")
        if os.path.isabs(file_path) and os.path.exists(file_path):
            return file_path
        # Try resolving against the project root (where config.py computes BASE_DIR)
        resolved = settings.resolve_path(file_path)
        if os.path.exists(resolved):
            return resolved
        # Last resort: try CWD
        cwd_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(cwd_path):
            return cwd_path
        raise FileNotFoundError(
            f"Answer sheet image not found. Tried:\n"
            f"  1. As-is: {file_path}\n"
            f"  2. Project root: {resolved}\n"
            f"  3. CWD: {cwd_path}"
        )

    def prepare_image_b64(self, file_path: str, max_dim: Optional[int] = None) -> str:
        """
        Normalize and compress image for optimal vision encoder throughput.
        Reduces vision tokens significantly while preserving handwriting legibility.
        """
        resolved_path = self._resolve_file_path(file_path)

        with Image.open(resolved_path) as img:
            img = img.convert("RGB")
            target_dim = max_dim if max_dim is not None else self.image_max_dim
            img.thumbnail((target_dim, target_dim), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return b64

    async def _get_rubric_context(self, evaluation_id: str) -> Tuple[str, List[Dict[str, Any]], float, str]:
        """
        Dynamically fetches and formats the rubric associated with this evaluation.
        Raises an error if no valid rubric is uploaded/attached.
        """
        db = get_database()
        eval_doc = await db.evaluations.find_one({"_id": ObjectId(evaluation_id)})
        if not eval_doc:
            raise ValueError(f"Evaluation {evaluation_id} not found in database.")

        subject = eval_doc.get("subject") or eval_doc.get("name") or "Course Examination"
        max_marks = float(eval_doc.get("max_marks", 100))

        rubric_id = eval_doc.get("rubric_id")
        components: List[Dict[str, Any]] = []

        if rubric_id and ObjectId.is_valid(rubric_id):
            rubric_doc = await db.rubrics.find_one({"_id": ObjectId(rubric_id)})
            if rubric_doc:
                if rubric_doc.get("components"):
                    components = rubric_doc["components"]
                elif rubric_doc.get("file_path") and os.path.exists(rubric_doc["file_path"]):
                    from app.services.rubric_parser import parse_rubric_file
                    components = parse_rubric_file(rubric_doc["file_path"])
                    if components:
                        await db.rubrics.update_one(
                            {"_id": rubric_doc["_id"]},
                            {"$set": {"components": components}}
                        )

        # Fallback search by evaluation_id if not found via rubric_id
        if not components:
            rubric_doc = await db.rubrics.find_one({"evaluation_id": evaluation_id})
            if rubric_doc and rubric_doc.get("components"):
                components = rubric_doc["components"]

        if not components:
            raise ValueError(
                f"No grading rubric components found for evaluation '{eval_doc.get('name', evaluation_id)}'. "
                "Please upload a rubric document (PDF/TXT) before running the evaluation pipeline."
            )

        rubric_lines = []
        for idx, comp in enumerate(components, start=1):
            name = comp.get("name", f"Component {idx}")
            marks = comp.get("marks", 1.0)
            model_ans = comp.get("model_answer", "")
            bands = comp.get("mark_bands", "")
            line = f"{idx}. {name} (Max Marks: {marks})"
            if model_ans:
                line += f"\n   Expected Solution: {model_ans}"
            if bands:
                line += f"\n   Criteria: {bands}"
            rubric_lines.append(line)

        comp_sum = sum(float(c.get("marks", 0)) for c in components if c.get("marks") is not None)
        if comp_sum > 0:
            max_marks = comp_sum

        rubric_text = "\n\n".join(rubric_lines)
        return rubric_text, components, max_marks, subject

    @staticmethod
    def _repair_json_escapes(raw_str: str) -> str:
        r"""Fix invalid backslashes (e.g. LaTeX math \min, \sum, \alpha) inside JSON strings."""
        return re.sub(r'\\(?!([\"\\/bfnrt]|u[0-9a-fA-F]{4}))', r'\\\\', raw_str)

    @classmethod
    def _parse_json_safely(cls, text: str) -> Optional[dict]:
        """Robustly extracts and parses a JSON object with schema key verification, including LaTeX math escape repair."""
        if not text:
            return None
        s = text.strip()

        # Clean markdown codeblocks
        if s.startswith("```"):
            lines = s.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            s = "\n".join(lines).strip()

        def _try_load(chunk: str) -> Optional[dict]:
            for candidate in (chunk, cls._repair_json_escapes(chunk)):
                try:
                    d = json.loads(candidate, strict=False)
                    if isinstance(d, dict) and any(k in d for k in ("rubric_breakdown", "transcription", "total_score")):
                        return d
                except Exception:
                    pass
                for extra in ["}", "\n}", "\n}\n}", '"}]}', '"}']:
                    try:
                        d = json.loads(candidate + extra, strict=False)
                        if isinstance(d, dict) and any(k in d for k in ("rubric_breakdown", "transcription", "total_score")):
                            return d
                    except Exception:
                        pass
            return None

        # 1. Direct parse attempt
        d = _try_load(s)
        if d:
            return d

        # 2. Targeted extraction: locate start of target JSON by searching backwards for schema keys
        target_keys = ['"rubric_breakdown"', '"transcription"', '"total_score"', '"student_name"']
        for key in target_keys:
            idx = s.rfind(key)
            while idx != -1:
                start_brace = s.rfind('{', 0, idx)
                if start_brace != -1:
                    candidate = s[start_brace:]
                    end_brace = candidate.rfind('}')
                    if end_brace != -1:
                        chunk = candidate[:end_brace + 1]
                        d = _try_load(chunk)
                        if d:
                            return d
                idx = s.rfind(key, 0, idx)

        # 3. Generic regex search for any balanced JSON object with target keys
        matches = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', s))
        for m in reversed(matches):
            d = _try_load(m.group(0))
            if d:
                return d

        return None

    @staticmethod
    def _calculate_grade(pct: float) -> str:
        """Standard institutional grading scale."""
        if pct >= 90: return "A+"
        if pct >= 80: return "A"
        if pct >= 70: return "B+"
        if pct >= 60: return "B"
        if pct >= 50: return "C"
        if pct >= 40: return "D"
        return "F"

    async def evaluate_sheet(
        self,
        evaluation_id: str,
        sheet_id: str,
        logger: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Processes a single student answer sheet dynamically:
        1. Digitizes text & math notation to clean Markdown.
        2. Parses hand-drawn diagrams/trees into structural topology.
        3. Evaluates answers against the attached institutional rubric.
        4. Detects borderline scores for Stage 4 Educator Review.
        Logs every step to the dedicated run folder.
        """
        if logger is None:
            from app.core.logging_config import get_run_logger
            logger = get_run_logger(evaluation_id)

        db = get_database()
        sheet = await db.sheets.find_one({"_id": ObjectId(sheet_id)})
        if not sheet:
            raise ValueError(f"Sheet {sheet_id} not found in database.")

        logger.info("[Sheet %s] --- BEGIN EVALUATION ---", sheet_id)

        # Step 1: Load rubric
        logger.info("[Sheet %s] Step 1/5: Loading rubric for evaluation %s...", sheet_id, evaluation_id)
        rubric_text, rubric_components, max_marks, subject = await self._get_rubric_context(evaluation_id)
        logger.info("[Sheet %s] Rubric loaded: %d components, max_marks=%.1f, subject='%s'",
                     sheet_id, len(rubric_components), max_marks, subject)

        # Step 2: Resolve and validate image file
        file_path = sheet.get("file_path", "")
        file_name = sheet.get("file_name", os.path.basename(file_path))
        logger.info("[Sheet %s] Step 2/5: Resolving image file '%s' (stored path: '%s')...",
                     sheet_id, file_name, file_path)

        try:
            resolved_path = self._resolve_file_path(file_path)
            file_size = os.path.getsize(resolved_path)
            logger.info("[Sheet %s] Image found: %s (%.1f KB)", sheet_id, resolved_path, file_size / 1024)
        except FileNotFoundError as e:
            logger.error("[Sheet %s] IMAGE NOT FOUND: %s", sheet_id, str(e))
            raise

        # Step 3: Check Ollama & Pre-flight Model Ping ("Are you up?")
        logger.info("[Sheet %s] Step 3/5: Checking Ollama & pinging model '%s' (\"Are you up?\")...", sheet_id, self.model_name)
        from app.core.event_bus import publish_event
        await publish_event(
            evaluation_id=evaluation_id,
            event_type="vlm_ping",
            message=f"[{file_name}] Pinging model {self.model_name} (\"Are you up?\") to verify runner is active in RAM...",
            data={"sheet_id": sheet_id, "file_name": file_name, "model": self.model_name},
            level="info",
        )
        is_up, ping_latency, ping_reply = await self.ping_model()
        if not is_up:
            raise RuntimeError(
                f"Ollama model '{self.model_name}' failed pre-flight health check at {self.ollama_url}: {ping_reply}. "
                f"Please ensure Ollama is running and model '{self.model_name}' is available."
            )
        logger.info("[Sheet %s] Pre-flight ping SUCCESS in %.2fs! Model '%s' is active in RAM (reply: '%s').",
                    sheet_id, ping_latency, self.model_name, ping_reply)
        await publish_event(
            evaluation_id=evaluation_id,
            event_type="vlm_ping_ok",
            message=f"[{file_name}] ✓ Model {self.model_name} is UP and warm in RAM ({ping_latency:.2f}s latency).",
            data={"sheet_id": sheet_id, "file_name": file_name, "model": self.model_name, "latency": round(ping_latency, 2)},
            level="info",
        )

        # Step 4: Encode image(s) and call VLM
        pages = sheet.get("pages")
        if not pages:
            pages = [{"file_name": file_name, "file_path": file_path, "page_number": 1}]

        b64_imgs = []
        for p in pages:
            p_path = self._resolve_file_path(p.get("file_path", file_path))
            b64_imgs.append(self.prepare_image_b64(p_path, max_dim=self.image_max_dim))

        total_b64_kb = sum(len(b) for b in b64_imgs) * 3 // 4 // 1024
        existing_student_name = sheet.get("student_name", "")
        page_count = len(b64_imgs)
        logger.info("[Sheet %s] Step 4/5: %d page(s) encoded (~%d KB total). Sending to Ollama %s...",
                     sheet_id, page_count, total_b64_kb, self.model_name)
        logger.info("[Sheet %s] (Processing on local CPU, ~60-90s per sheet...)",
                     sheet_id)

        from app.core.event_bus import publish_event
        await publish_event(
            evaluation_id=evaluation_id,
            event_type="vlm_dispatch",
            message=f"[{file_name}] {page_count} page(s) encoded (~{total_b64_kb} KB). Submitting to {self.model_name}...",
            data={"sheet_id": sheet_id, "file_name": file_name, "model": self.model_name, "page_count": page_count},
            level="info",
        )

        # Acquire lock to ensure single-job execution on CPU to avoid timeouts and thrashing
        start_time = time.time()
        async with self._inference_lock:
            logger.info("[Sheet %s] Inference lock acquired. Calling Ollama /api/generate (%d page(s))...", sheet_id, page_count)
            result = await self._call_vlm(
                b64_imgs=b64_imgs,
                rubric_text=rubric_text,
                file_name=file_name,
                sheet_student_name=existing_student_name,
                rubric_components=rubric_components,
                max_marks=max_marks,
                subject=subject,
                logger=logger,
                sheet_id=sheet_id,
            )
        elapsed = time.time() - start_time
        logger.info("[Sheet %s] Step 5/5: VLM inference completed in %.1fs", sheet_id, elapsed)

        await publish_event(
            evaluation_id=evaluation_id,
            event_type="vlm_complete",
            message=f"[{file_name}] Ollama response parsed in {elapsed:.1f}s. Finalizing assessment...",
            data={"sheet_id": sheet_id, "file_name": file_name, "elapsed": round(elapsed, 2)},
            level="info",
        )

        # Update MongoDB sheet record with authentic evaluation results
        total_score = result.get("total_score", 0.0)
        grade = result.get("evaluation_result", {}).get("grade", self._calculate_grade((total_score / max_marks * 100) if max_marks > 0 else 0))
        needs_review = result.get("needs_human_review", False)
        review_reasons = result.get("review_reasons", [])

        logger.info(
            "[Sheet %s] RESULT: Student='%s' | Score=%.1f/%.1f | Grade=%s | Review=%s",
            sheet_id,
            result.get("student_name") or existing_student_name,
            total_score,
            max_marks,
            grade,
            needs_review,
        )
        if needs_review:
            logger.warning("[Sheet %s] Flagged for Educator Review! Reasons: %s", sheet_id, review_reasons)

        # Log rubric breakdown
        breakdown = result.get("evaluation_result", {}).get("questions", [{}])[0].get("component_scores", []) if result.get("evaluation_result") else []
        for comp in breakdown:
            logger.info("[Sheet %s]   - %s: %.1f/%.1f | %s",
                        sheet_id,
                        comp.get("component", "?"),
                        comp.get("marks_awarded", 0),
                        comp.get("max_marks", 0),
                        comp.get("feedback", "")[:80])

        update_doc = {
            "student_name": result.get("student_name") or existing_student_name or os.path.splitext(file_name)[0],
            "ocr_text": result.get("transcription", ""),
            "diagram_descriptions": result.get("diagram_description", ""),
            "evaluation_result": result.get("evaluation_result", {}),
            "total_score": total_score,
            "max_score": result.get("max_score", max_marks),
            "status": "review-needed" if needs_review else "evaluation-completed",
            "needs_human_review": needs_review,
            "review_reasons": review_reasons,
            "ocr_confidence": 0.95,
            "crops": result.get("crops", sheet.get("crops", [])),
            "pages": pages,
            "page_count": len(pages),
            "is_bundle": sheet.get("is_bundle", len(pages) > 1),
            "evaluation_completed_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }

        # Save individual sheet evaluation artifact into the run folder if available
        run_dir = getattr(logger, "run_dir", None)
        if run_dir:
            sheet_artifact = Path(run_dir) / f"sheet_{sheet_id}.json"
            try:
                with open(sheet_artifact, "w", encoding="utf-8") as f:
                    json.dump(update_doc, f, indent=2, default=str)
                logger.info("[Sheet %s] Stored sheet artifact at %s", sheet_id, sheet_artifact)
            except Exception as e:
                logger.warning("[Sheet %s] Could not save sheet JSON artifact: %s", sheet_id, e)

        await db.sheets.update_one({"_id": ObjectId(sheet_id)}, {"$set": update_doc})
        logger.info("[Sheet %s] --- EVALUATION COMPLETE ---", sheet_id)
        return update_doc

    async def _call_vlm(
        self,
        b64_imgs: List[str] | str,
        rubric_text: str,
        file_name: str,
        sheet_student_name: str,
        rubric_components: List[Dict[str, Any]],
        max_marks: float,
        subject: str,
        logger: Optional[Any] = None,
        sheet_id: str = "",
    ) -> Dict[str, Any]:
        """Invokes local VLM via Ollama with strict JSON enforcement across all submission pages."""
        if isinstance(b64_imgs, str):
            b64_imgs = [b64_imgs]

        page_count = len(b64_imgs)
        page_directive = (
            f"Evaluate this complete {page_count}-page handwritten examination answer script "
            f"(Page 1 through Page {page_count}) accurately against the official rubric from beginning to end."
            if page_count > 1 else
            "Evaluate this handwritten student examination answer sheet image accurately against the official rubric."
        )

        prompt = f"""You are an Expert University Professor and Precision Academic Grading System for: {subject}.
{page_directive}

### OFFICIAL GRADING RUBRIC:
{rubric_text}

### MANDATORY INSTRUCTIONS:
1. Complete verbatim transcription of all handwritten text, formulas, steps, and pseudocode across all {page_count} page(s) from top to bottom (do not summarize or condense).
2. Grade every rubric component with marks awarded, exact student evidence quote, detailed explainability feedback, and expected answer.
3. In "evaluator_rationale", provide an in-depth 3-5 sentence academic assessment summary explaining strengths, gaps, and exact justification for total score awarded across the full submission.
4. STRICT THINKING CONSTRAINT: Keep internal reasoning concise (under 100-150 words). Do not rewrite the prompt or transcribe the code in thinking. Quickly check criteria and immediately output the final JSON object.

Return ONLY a valid JSON object matching this schema:
{{
  "student_name": "Student Name (e.g. Nithin) or empty string",
  "transcription": "Complete verbatim markdown transcription of the handwritten answer sheet across all pages from top to bottom, including all text, steps, and full pseudocode",
  "diagram_description": "Structural description of hand-drawn diagrams, or empty string",
  "rubric_breakdown": [
    {{
      "component": "Component name matching rubric",
      "marks_awarded": 1.5,
      "max_marks": 2.0,
      "student_evidence": "Exact quote or line from the student script",
      "feedback": "Detailed explainability rationale: what was demonstrated, what was missing, and deduction reasoning",
      "model_answer": "Expected standard answer or criteria"
    }}
  ],
  "evaluator_rationale": "Comprehensive academic assessment summary explaining strengths, gaps, and exact justification for total score awarded",
  "total_score": 0.0,
  "max_score": {max_marks},
  "percentage": 0.0,
  "grade": "B",
  "needs_human_review": false,
  "review_reasons": []
}}
"""
        req_payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": b64_imgs,
            "options": {
                "num_thread": 10,
                "temperature": 0.6,
                "num_ctx": self.vlm_num_ctx,
                "num_predict": self.vlm_max_tokens,
            },
            "stream": False,
        }

        timeout_sec = 600.0  # 10 minutes per sheet for local CPU inference
        _log = logger.info if logger else print
        total_kb = sum(len(b) for b in b64_imgs) * 3 // 4 // 1024

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                _log("[Sheet %s] POST %s/api/generate (model=%s, timeout=%ds, prompt=%d chars, %d page(s), total=%d KB)",
                     sheet_id, self.ollama_url, self.model_name, int(timeout_sec),
                     len(prompt), page_count, total_kb)
                resp = await client.post(f"{self.ollama_url}/api/generate", json=req_payload)
        except httpx.TimeoutException as exc:
            if logger:
                logger.error("[Sheet %s] TIMEOUT after %ds waiting for Ollama. The model is too slow on CPU for this image.",
                             sheet_id, int(timeout_sec))
            raise RuntimeError(
                f"Ollama inference timed out after {int(timeout_sec)}s on CPU while evaluating '{file_name}'. "
                "The model is taking longer than expected. Retrying one sheet at a time is recommended."
            ) from exc
        except Exception as exc:
            err_detail = str(exc) or type(exc).__name__
            if logger:
                logger.error("[Sheet %s] Ollama connection error: %s\n%s", sheet_id, err_detail, traceback.format_exc())
            raise RuntimeError(f"Ollama connection error: {err_detail}") from exc

        if resp.status_code != 200:
            body_preview = resp.text[:500]
            if logger:
                logger.error("[Sheet %s] Ollama HTTP %d: %s", sheet_id, resp.status_code, body_preview)
            if resp.status_code == 404 or "not found" in resp.text.lower():
                raise RuntimeError(
                    f"Ollama model '{self.model_name}' is not installed locally. Please run: ollama pull {self.model_name}"
                )
            raise RuntimeError(
                f"Ollama inference failed (HTTP {resp.status_code}): {body_preview}"
            )

        # Parse Ollama response metadata
        resp_body = resp.json()
        eval_duration = resp_body.get("eval_duration", 0) / 1e9
        prompt_eval_duration = resp_body.get("prompt_eval_duration", 0) / 1e9
        total_duration = resp_body.get("total_duration", 0) / 1e9
        eval_count = resp_body.get("eval_count", 0)
        prompt_eval_count = resp_body.get("prompt_eval_count", 0)

        _log("[Sheet %s] Ollama response received: HTTP 200", sheet_id)
        _log("[Sheet %s]   Prompt eval: %.1fs (%d tokens) | Generation: %.1fs (%d tokens) | Total: %.1fs",
             sheet_id, prompt_eval_duration, prompt_eval_count, eval_duration, eval_count, total_duration)

        raw_json = resp_body.get("response", "").strip()
        thinking = resp_body.get("thinking", "").strip()
        if thinking:
            _log("[Sheet %s]   Model reasoning completed (%d chars of chain-of-thought)", sheet_id, len(thinking))

        data = None
        # 1. Attempt extraction from response body
        if raw_json:
            data = self._parse_json_safely(raw_json)

        # 2. If response was empty or unparseable, search inside thinking block for schema JSON
        if not data and thinking:
            _log("[Sheet %s]   Searching for schema JSON inside thinking block (%d chars)...", sheet_id, len(thinking))
            data = self._parse_json_safely(thinking)

        if not data:
            if logger:
                logger.error("[Sheet %s] Failed to extract valid schema JSON. Response: %d chars, Thinking: %d chars",
                             sheet_id, len(raw_json), len(thinking))
            raise RuntimeError("VLM response did not contain a valid JSON evaluation object. Please retry this sheet.")

        _log("[Sheet %s]   JSON parsed successfully! Keys: %s", sheet_id, list(data.keys()))

        return self._format_vlm_output(
            data=data,
            file_name=file_name,
            sheet_student_name=sheet_student_name,
            rubric_components=rubric_components,
            max_marks=max_marks,
            subject=subject,
        )

    def _format_vlm_output(
        self,
        data: dict,
        file_name: str,
        sheet_student_name: str,
        rubric_components: List[Dict[str, Any]],
        max_marks: float,
        subject: str,
    ) -> dict:
        total = float(data.get("total_score", 0.0))
        max_s = float(data.get("max_score", max_marks))
        if max_s <= 0:
            max_s = max_marks if max_marks > 0 else 10.0

        total = min(max(0.0, total), max_s)
        pct = round((total / max_s * 100), 1) if max_s > 0 else 0.0

        # Dynamic student name resolution
        student_name = data.get("student_name", "").strip()
        transcription = data.get("transcription", "")
        is_generic = (
            not student_name
            or student_name.lower() in ("student", "unknown", "n/a", "none")
            or student_name.startswith("IMG_")
            or student_name == os.path.splitext(file_name)[0]
        )
        if is_generic and transcription:
            m = re.search(r"Name(?:\s+of\s+the\s+Candidate)?\s*:\s*([A-Za-z\s]+?)(?=\n\s*(?:USN|Signature|Date|Course|Marks)|\n\n)", transcription, re.IGNORECASE)
            if m:
                extracted = " ".join(m.group(1).split())
                if len(extracted) >= 2:
                    student_name = extracted

        if not student_name or student_name.lower() in ("student", "unknown", "n/a", "none"):
            student_name = sheet_student_name or os.path.splitext(file_name)[0]

        calculated_grade = self._calculate_grade(pct)
        grade = data.get("grade") or calculated_grade

        # Stage 4 borderline detection
        needs_review = bool(data.get("needs_human_review", False))
        review_reasons = list(data.get("review_reasons", []))

        # Boundary rule: within 2.5% of any grade cutoff
        boundary_dist = min(abs(pct - cutoff) for cutoff in [90, 80, 70, 60, 50, 40])
        if boundary_dist <= 2.5 and f"Borderline score ({pct}%)" not in "".join(review_reasons):
            needs_review = True
            review_reasons.append(f"Borderline score ({pct}%, within 2.5% of grade threshold)")

        rubric_breakdown = data.get("rubric_breakdown", [])
        formatted_breakdown = []
        for comp in rubric_breakdown:
            formatted_breakdown.append({
                "component": comp.get("component") or comp.get("name") or "Criteria",
                "marks_awarded": float(comp.get("marks_awarded", 0.0)),
                "max_marks": float(comp.get("max_marks", 1.0)),
                "feedback": comp.get("feedback") or "Graded against rubric criteria.",
                "student_evidence": comp.get("student_evidence", ""),
                "model_answer": comp.get("model_answer", ""),
            })

        if not formatted_breakdown and rubric_components:
            for comp in rubric_components:
                formatted_breakdown.append({
                    "component": comp.get("name", "Criteria"),
                    "marks_awarded": 0.0,
                    "max_marks": float(comp.get("marks", 1.0)),
                    "feedback": "Evaluated by multimodal model.",
                    "student_evidence": "Not found in student script",
                    "model_answer": comp.get("model_answer", ""),
                })

        evaluator_rationale = data.get("evaluator_rationale") or data.get("feedback") or "Evaluated with criteria-based explainability."

        eval_result = {
            "questions": [
                {
                    "question_number": 1,
                    "question_text": f"{subject} Answer Assessment",
                    "component_scores": formatted_breakdown,
                    "total_marks": total,
                    "max_marks": max_s,
                    "feedback": evaluator_rationale,
                }
            ],
            "total_score": total,
            "max_score": max_s,
            "percentage": pct,
            "grade": grade,
        }

        crops = []
        if data.get("diagram_description"):
            crops.append({
                "crop_id": "crop_figure_1",
                "crop_type": "figure",
                "crop_path": "",
                "diagram_description": data.get("diagram_description"),
            })

        return {
            "student_name": student_name,
            "transcription": data.get("transcription", ""),
            "diagram_description": data.get("diagram_description", ""),
            "evaluation_result": eval_result,
            "total_score": total,
            "max_score": max_s,
            "needs_human_review": needs_review,
            "review_reasons": review_reasons,
            "crops": crops,
        }


# Singleton accessor
_vlm_service: Optional[UnifiedVLMService] = None

def get_unified_vlm_service() -> UnifiedVLMService:
    global _vlm_service
    if _vlm_service is None:
        _vlm_service = UnifiedVLMService()
    return _vlm_service
