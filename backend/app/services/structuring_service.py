"""
Text Structuring Service.

Parses raw OCR text into structured question-answer format using
regex + heuristic rules.  No ML model required.

Design principles:
  • Modular — independent service, can upgrade to ML-based parser later
  • Stateless — takes raw text in, returns structured dict out
"""
import re
from typing import Optional


# Common CS / programming keywords for keyword extraction
_CS_KEYWORDS = {
    "algorithm", "array", "binary", "boolean", "class", "complexity",
    "data structure", "database", "function", "graph", "hash", "heap",
    "inheritance", "iteration", "linked list", "loop", "matrix",
    "object", "pointer", "polymorphism", "queue", "recursion",
    "search", "sort", "stack", "string", "tree", "variable",
    "if", "else", "while", "for", "return", "print", "input",
    "def", "int", "float", "list", "dict", "set", "tuple",
    "try", "except", "import", "from", "break", "continue",
    "switch", "case", "struct", "void", "null", "true", "false",
    "O(1)", "O(n)", "O(n^2)", "O(log n)", "O(n log n)",
}

# Patterns that indicate code rather than prose
_CODE_INDICATORS = re.compile(
    r"(=\s*\d|[{}\[\];]|\b(def|class|if|else|elif|while|for|return|print|"
    r"int\s+\w|void\s+\w|public|private|#include)\b)",
    re.IGNORECASE,
)

# Question start patterns  — Q1 / Q.1 / 1. / 1) / Question 1 …
_QUESTION_SPLIT = re.compile(
    r"(?:^|\n)"                       # start of line
    r"(?:"
    r"Q\.?\s*(\d+)"                   # Q1, Q.1, Q 1
    r"|Question\s+(\d+)"             # Question 1
    r"|(\d+)\s*[.)]\s"               # 1. or 1)
    r")",
    re.IGNORECASE,
)

# Sub-step patterns — Step 1, a), b), i., ii.
_STEP_SPLIT = re.compile(
    r"(?:^|\n)\s*(?:Step\s+(\d+)|([a-z])\)|([ivx]+)\.)\s",
    re.IGNORECASE,
)

# Complexity patterns
_COMPLEXITY_RE = re.compile(r"O\([^)]+\)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# OCR cleaning patterns  (from ocr_pipeline_prompt.md — Step 1)
# ---------------------------------------------------------------------------

# Broken words: a space inserted inside a word (e.g. "al go rithm" → not fixable
# generically, but we can catch single-char fragments glued to neighbours)
_BROKEN_SINGLE_CHAR = re.compile(r"(?<=[a-zA-Z])\s([a-zA-Z])\s(?=[a-zA-Z])")

# Excessive whitespace (tabs, multiple spaces → single space)
_MULTI_SPACE = re.compile(r"[^\S\n]{2,}")

# Garbled / non-printable characters (everything outside basic printable ASCII
# + common Unicode letters, but keep newlines)
_GARBLED = re.compile(r"[^\x20-\x7E\n\u00C0-\u024F]+")

# Lines that are entirely noise (fewer than 2 alphanumeric chars)
_NOISE_LINE = re.compile(r"^[^a-zA-Z0-9]*[a-zA-Z0-9]?[^a-zA-Z0-9]*$")


class StructuringService:
    """Parse raw OCR text into structured Q&A data."""

    # ------------------------------------------------------------------
    # OCR text cleaning  (prompt Step 1)
    # ------------------------------------------------------------------
    def clean_ocr_text(self, raw_text: str) -> str:
        """Apply rule-based cleaning to raw OCR output.

        Implements the OCR Cleaning step from ocr_pipeline_prompt.md:
          • Fix common spacing issues and broken words
          • Mark illegible / garbled sequences as [OCR_UNCLEAR]
          • Preserve code syntax, variable names, and math expressions
          • Do NOT alter meaning

        Args:
            raw_text: Raw text straight from the Vision API.

        Returns:
            Cleaned text ready for question splitting.
        """
        if not raw_text or not raw_text.strip():
            return ""

        lines = raw_text.split("\n")
        cleaned_lines: list[str] = []

        for line in lines:
            # Skip entirely noisy lines
            if _NOISE_LINE.match(line) and len(line.strip()) > 0:
                # Only skip if the line has almost no real content
                alnum_count = sum(1 for c in line if c.isalnum())
                if alnum_count < 2 and len(line.strip()) > 3:
                    continue

            # Replace garbled character sequences with [OCR_UNCLEAR]
            # but only if the sequence is 2+ chars (avoid marking single
            # Unicode accent characters)
            cleaned = _GARBLED.sub(lambda m: "[OCR_UNCLEAR]" if len(m.group()) >= 2 else m.group(), line)

            # Convert LaTeX formulas to human-readable text
            cleaned = self._convert_latex_to_text(cleaned)

            # Collapse excessive whitespace
            cleaned = _MULTI_SPACE.sub(" ", cleaned)

            # Re-join single-character fragments that OCR split apart
            # e.g. "a l g o r i t h m" — only when surrounded by letters
            cleaned = _BROKEN_SINGLE_CHAR.sub(r"\1", cleaned)

            # Strip leading/trailing whitespace per line
            cleaned = cleaned.strip()

            if cleaned:
                cleaned_lines.append(cleaned)

        return "\n".join(cleaned_lines)

    def _convert_latex_to_text(self, text: str) -> str:
        """Convert LaTeX math/formulas to human-readable Markdown/plain text.
        
        Examples:
          \text{Mid} -> Mid
          \frac{a}{b} -> (a) / (b)
          \rightarrow -> ->
        """
        # 1. Basic formatting commands
        text = re.sub(r"\\text\{([^}]+)\}", r"\1", text)
        text = re.sub(r"\\boxed\{([^}]+)\}", r"[\1]", text)
        
        # 2. Fractions: \frac{num}{den} -> (num) / (den)
        # Handle nested braces with a simple loop if needed, but basic regex first
        while "\\frac{" in text:
            new_text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1) / (\2)", text)
            if new_text == text: break
            text = new_text

        # 3. Square roots
        text = re.sub(r"\\sqrt\{([^}]+)\}", r"sqrt(\1)", text)

        # 4. Arrows
        text = text.replace("\\rightarrow", "->")
        text = text.replace("\\Rightarrow", "=>")
        text = text.replace("\\leftarrow", "<-")
        text = text.replace("\\Leftarrow", "<=")
        text = text.replace("\\leftrightarrow", "<->")

        # 5. Symbols & Operators
        text = text.replace("\\times", "*")
        text = text.replace("\\div", "/")
        text = text.replace("\\pm", "+/-")
        text = text.replace("\\le", "<=")
        text = text.replace("\\ge", ">=")
        text = text.replace("\\neq", "!=")
        text = text.replace("\\infty", "infinity")
        text = text.replace("\\dots", "...")

        # 6. Arrays / Tables (Simple flattening)
        text = re.sub(r"\\begin\{array\}\{[^}]+\}", "", text)
        text = text.replace("\\end{array}", "")
        text = text.replace("\\\\", "\n")  # Newline in arrays
        text = text.replace("&", " | ")    # Column separator

        # 7. Remove math delimiters
        text = text.replace("$$", "")
        text = text.replace("$", "")

        return text

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def structure_text(self, raw_text: str) -> dict:
        """Main entry point.

        Args:
            raw_text: Plain text from OCR extraction.

        Returns:
            dict matching the StructuredText schema.
        """
        if not raw_text or not raw_text.strip():
            return {
                "questions": [],
                "metadata": {
                    "total_questions": 0,
                    "total_steps": 0,
                    "average_complexity": "N/A",
                },
            }

        # Step 1: Clean OCR artefacts before parsing
        cleaned_text = self.clean_ocr_text(raw_text)

        question_blocks = self._split_questions(cleaned_text)

        questions = []
        total_steps = 0

        for q_num, q_block in question_blocks:
            structured_q = self._parse_question(q_num, q_block)
            questions.append(structured_q)
            total_steps += len(structured_q["answer"]["structured_steps"])

        return {
            "questions": questions,
            "metadata": {
                "total_questions": len(questions),
                "total_steps": total_steps,
                "average_complexity": self._average_complexity(questions),
            },
        }

    # ------------------------------------------------------------------
    # Question splitting
    # ------------------------------------------------------------------
    def _split_questions(self, text: str) -> list[tuple[int, str]]:
        """Split text into (question_number, block_text) pairs."""
        matches = list(_QUESTION_SPLIT.finditer(text))

        if not matches:
            # No question markers found → treat entire text as one question
            return [(1, text.strip())]

        blocks: list[tuple[int, str]] = []
        for i, m in enumerate(matches):
            q_num = int(m.group(1) or m.group(2) or m.group(3))
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            if block:
                blocks.append((q_num, block))

        return blocks if blocks else [(1, text.strip())]

    # ------------------------------------------------------------------
    # Single question parsing
    # ------------------------------------------------------------------
    def _parse_question(self, q_num: int, block: str) -> dict:
        """Parse a single question block into structured form."""
        lines = block.split("\n")

        # First line is usually the question text; rest is the answer
        question_text = lines[0].strip() if lines else ""
        answer_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else block.strip()

        # If the first line looks like code or is very short, treat all as answer
        if len(question_text) < 5 or _CODE_INDICATORS.search(question_text):
            question_text = f"Question {q_num}"
            answer_text = block.strip()

        steps = self._extract_steps(answer_text)
        code_blocks = self._extract_code_blocks(answer_text)
        keywords = self._extract_keywords(answer_text)
        complexity = self._detect_complexity(answer_text)

        return {
            "question_number": q_num,
            "question_text": question_text,
            "answer": {
                "raw_text": answer_text,
                "structured_steps": steps,
                "identified_algorithm": None,
                "complexity": complexity,
                "keywords": keywords,
                "code_blocks": code_blocks,
            },
        }

    # ------------------------------------------------------------------
    # Step extraction
    # ------------------------------------------------------------------
    def _extract_steps(self, text: str) -> list[dict]:
        """Detect answer steps (Step 1, a), i., numbered sub-items)."""
        matches = list(_STEP_SPLIT.finditer(text))

        if not matches:
            # No sub-steps → single step from the whole text
            step_type = "code" if _CODE_INDICATORS.search(text) else "explanation"
            return [
                {
                    "step_number": 1,
                    "description": "Answer",
                    "type": step_type,
                    "content": text.strip(),
                }
            ]

        steps: list[dict] = []
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            step_type = "code" if _CODE_INDICATORS.search(content) else "explanation"

            steps.append(
                {
                    "step_number": i + 1,
                    "description": content[:60].rstrip() + ("…" if len(content) > 60 else ""),
                    "type": step_type,
                    "content": content,
                }
            )

        return steps

    # ------------------------------------------------------------------
    # Code block detection
    # ------------------------------------------------------------------
    def _extract_code_blocks(self, text: str) -> list[dict]:
        """Identify code-like regions in the answer text."""
        blocks: list[dict] = []
        lines = text.split("\n")
        code_lines: list[str] = []
        code_start = -1

        for idx, line in enumerate(lines):
            if _CODE_INDICATORS.search(line):
                if not code_lines:
                    code_start = idx + 1
                code_lines.append(line)
            else:
                if code_lines:
                    blocks.append(
                        {
                            "language": "python",  # default assumption
                            "code": "\n".join(code_lines),
                            "line_numbers": {
                                "start": code_start,
                                "end": code_start + len(code_lines) - 1,
                            },
                        }
                    )
                    code_lines = []

        # Flush remaining
        if code_lines:
            blocks.append(
                {
                    "language": "python",
                    "code": "\n".join(code_lines),
                    "line_numbers": {
                        "start": code_start,
                        "end": code_start + len(code_lines) - 1,
                    },
                }
            )

        return blocks

    # ------------------------------------------------------------------
    # Keyword extraction
    # ------------------------------------------------------------------
    def _extract_keywords(self, text: str) -> list[str]:
        """Find CS-related keywords in the text."""
        text_lower = text.lower()
        found = [kw for kw in _CS_KEYWORDS if kw in text_lower]
        return sorted(set(found))

    # ------------------------------------------------------------------
    # Complexity detection
    # ------------------------------------------------------------------
    def _detect_complexity(self, text: str) -> Optional[str]:
        """Look for Big-O notation in the text."""
        m = _COMPLEXITY_RE.search(text)
        return m.group(0) if m else None

    def _average_complexity(self, questions: list[dict]) -> str:
        """Aggregate complexity across questions."""
        complexities = [
            q["answer"]["complexity"]
            for q in questions
            if q["answer"]["complexity"]
        ]
        if not complexities:
            return "N/A"
        return ", ".join(sorted(set(complexities)))


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_instance: StructuringService | None = None


def get_structuring_service() -> StructuringService:
    global _instance
    if _instance is None:
        _instance = StructuringService()
    return _instance


def init_structuring_service() -> StructuringService:
    global _instance
    if _instance is None:
        _instance = StructuringService()
        print("[Structuring] Service ready.")
    return _instance
