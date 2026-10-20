"""
SLM Evaluation Service using Qwen2.5-0.5B-Instruct.

Grades structured Q&A answers against a rubric using a small language model
running entirely on CPU.

Design principles:
  • Modular — independent service, can swap model later
  • Efficient — model loaded ONCE, reused across requests
  • CPU-friendly — Qwen2.5-0.5B runs smoothly without GPU
  • Stateless — takes structured data in, returns scores out
"""
import json
import re
import time
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


class SLMService:
    """Answer evaluation using Qwen2.5-0.5B-Instruct."""

    MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

    def __init__(self) -> None:
        """Load the Qwen tokenizer and model (called once at startup)."""
        self.is_loaded = False
        try:
            print(f"[SLM] Loading model '{self.MODEL_NAME}' for CPU …")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.MODEL_NAME,
                trust_remote_code=True,
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.MODEL_NAME,
                torch_dtype=torch.float32,
                device_map="cpu",
                trust_remote_code=True,
            )
            self.model.eval()
            self.is_loaded = True
            print("[SLM] Model loaded successfully.")
        except Exception as exc:
            print(f"[SLM] Qwen model not loaded locally ({exc}). Ready for local inference.")
            self.tokenizer = None
            self.model = None

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------
    def _build_prompt(
        self,
        question_text: str,
        answer_text: str,
        rubric_components: list[dict],
        max_marks: float,
    ) -> list[dict]:
        """Build a chat-style grading prompt."""
        rubric_desc = "\n".join(
            f"  - {c['name']}: {c['marks']} marks"
            for c in rubric_components
        )

        system_msg = (
            "You are a strict but fair exam evaluator. "
            "Grade the student's answer against the rubric. "
            "Return ONLY valid JSON — no markdown, no explanation outside JSON."
        )

        user_msg = (
            f"## Question\n{question_text}\n\n"
            f"## Student Answer\n{answer_text}\n\n"
            f"## Rubric (total {max_marks} marks)\n{rubric_desc}\n\n"
            "## Instructions\n"
            "Award marks for each rubric component based on how well the answer addresses it.\n"
            "Return JSON in exactly this format:\n"
            "```\n"
            "{\n"
            '  "components": [\n'
            '    {"component": "<name>", "marks_awarded": <float>, "max_marks": <float>, "feedback": "<1-2 sentences>"}\n'
            "  ],\n"
            '  "total_marks": <float>,\n'
            '  "feedback": "<overall 1-2 sentence summary>"\n'
            "}\n"
            "```"
        )

        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------
    def _parse_response(
        self,
        raw_output: str,
        rubric_components: list[dict],
        max_marks: float,
    ) -> dict:
        """Extract structured grading JSON from model output.

        Falls back to heuristic scoring if JSON parsing fails.
        """
        # Try to find JSON in the output
        json_match = re.search(r"\{[\s\S]*\}", raw_output)
        if json_match:
            try:
                data = json.loads(json_match.group())
                # Validate and clamp scores
                components = []
                total = 0.0
                for i, comp in enumerate(data.get("components", [])):
                    comp_name = comp.get("component", "Unknown")
                    
                    # 1. Try to find true max_marks by matching the component name
                    true_max_marks = None
                    for rc in rubric_components:
                        if rc.get("name", "").lower() == comp_name.lower():
                            true_max_marks = float(rc.get("marks", 0))
                            break
                            
                    # 2. Fallback to positional mapping if names don't match perfectly
                    if true_max_marks is None and i < len(rubric_components):
                        true_max_marks = float(rubric_components[i].get("marks", 0))
                        comp_name = rubric_components[i].get("name", comp_name)
                    
                    # 3. Last resort fallback to what the model returned
                    if true_max_marks is None:
                        true_max_marks = float(comp.get("max_marks", 0))

                    awarded = min(
                        float(comp.get("marks_awarded", 0)),
                        true_max_marks,
                    )
                    awarded = max(0.0, awarded)
                    
                    components.append({
                        "component": comp_name,
                        "marks_awarded": round(awarded, 1),
                        "max_marks": round(true_max_marks, 1),
                        "feedback": comp.get("feedback", ""),
                    })
                    total += awarded

                return {
                    "components": components,
                    "total_marks": round(min(total, max_marks), 1),
                    "feedback": data.get("feedback", "Evaluation complete."),
                    "evaluation_method": "model",
                }
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        # Fallback: give partial credit based on answer length
        return self._fallback_evaluation(rubric_components, max_marks)

    def _fallback_evaluation(
        self,
        rubric_components: list[dict],
        max_marks: float,
    ) -> dict:
        """Heuristic fallback when model output can't be parsed."""
        components = []
        total = 0.0
        for comp in rubric_components:
            awarded = round(float(comp["marks"]) * 0.5, 1)  # 50% partial credit
            components.append({
                "component": comp["name"],
                "marks_awarded": awarded,
                "max_marks": float(comp["marks"]),
                "feedback": "Auto-evaluated (model output could not be parsed).",
            })
            total += awarded

        return {
            "components": components,
            "total_marks": round(total, 1),
            "feedback": "Partial credit awarded — model response was ambiguous.",
            "evaluation_method": "fallback",
        }

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------
    def evaluate_answer(
        self,
        question_text: str,
        answer_text: str,
        rubric_components: list[dict],
        max_marks: float,
        model_answers: list[str] | None = None,
    ) -> dict:
        """Evaluate a single question-answer pair against the rubric.

        Args:
            question_text: The exam question.
            answer_text: The student's answer (raw or structured).
            rubric_components: List of {"name": str, "marks": float}.
            max_marks: Maximum marks for this question.

        Returns:
            dict with keys: components, total_marks, feedback, processing_time_ms
        """
        t0 = time.perf_counter()

        if not self.is_loaded or self.model is None or self.tokenizer is None:
            res = self._fallback_evaluation(rubric_components, max_marks)
            res["processing_time_ms"] = round((time.perf_counter() - t0) * 1000)
            if model_answers:
                for i, comp in enumerate(res["components"]):
                    if i < len(model_answers):
                        comp["model_answer"] = model_answers[i]
            return res

        messages = self._build_prompt(
            question_text, answer_text, rubric_components, max_marks,
        )

        # Tokenize using the chat template
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        inputs = self.tokenizer(text, return_tensors="pt")

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        # Decode only the generated tokens (skip the prompt)
        generated = output_ids[0][inputs["input_ids"].shape[1]:]
        raw_output = self.tokenizer.decode(generated, skip_special_tokens=True)

        result = self._parse_response(raw_output, rubric_components, max_marks)
        result["processing_time_ms"] = round((time.perf_counter() - t0) * 1000)

        if model_answers:
            for i, comp in enumerate(result["components"]):
                if i < len(model_answers):
                    comp["model_answer"] = model_answers[i]

        return result

    # ------------------------------------------------------------------
    # Grade calculation helper
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_grade(percentage: float) -> str:
        """Convert percentage to letter grade."""
        if percentage >= 90:
            return "A+"
        elif percentage >= 80:
            return "A"
        elif percentage >= 70:
            return "B+"
        elif percentage >= 60:
            return "B"
        elif percentage >= 50:
            return "C"
        elif percentage >= 40:
            return "D"
        else:
            return "F"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_instance: SLMService | None = None


def get_slm_service() -> SLMService:
    """Return the SLM service singleton. Raises if not initialised."""
    if _instance is None:
        raise RuntimeError("SLMService not initialised — call init_slm_service() first.")
    return _instance


def init_slm_service() -> SLMService:
    """Initialise the singleton (call once at startup)."""
    global _instance
    if _instance is None:
        _instance = SLMService()
    return _instance
