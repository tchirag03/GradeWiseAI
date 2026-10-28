"""
Structured Run Logging System.
Stores execution logs for each evaluation run in a dedicated folder:
  logs/{evaluation_id}/{run_id}/run.log
  logs/{evaluation_id}/{run_id}/summary.json
"""
import os
import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.core.config import settings

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configure standard root logger
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)

_run_loggers: dict[str, logging.Logger] = {}


def _sanitize_path_component(val: str, default: str = "unknown") -> str:
    """Sanitize directory names to prevent path traversal."""
    cleaned = re.sub(r"[^\w-]", "", str(val)).strip()
    return cleaned if cleaned else default


def get_run_dir(evaluation_id: str, run_id: Optional[str] = None) -> Path:
    """Computes and creates the dedicated directory for an evaluation run."""
    base_dir = Path(settings.log_dir).resolve()
    safe_eval_id = _sanitize_path_component(evaluation_id, "eval")
    if not run_id:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{timestamp}"

    safe_run_id = _sanitize_path_component(run_id, "run_default")
    run_dir = base_dir / safe_eval_id / safe_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def get_run_logger(evaluation_id: str, run_id: Optional[str] = None) -> logging.Logger:
    """
    Returns a logger configured to write to the dedicated folder for this run:
    logs/{evaluation_id}/{run_id}/run.log
    """
    safe_eval_id = _sanitize_path_component(evaluation_id, "eval")
    if not run_id:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{timestamp}"
    safe_run_id = _sanitize_path_component(run_id, "run_default")

    key = f"{safe_eval_id}_{safe_run_id}"
    if key in _run_loggers:
        return _run_loggers[key]

    run_dir = get_run_dir(safe_eval_id, safe_run_id)
    log_file = run_dir / "run.log"

    logger = logging.getLogger(f"eval_{safe_eval_id}_{safe_run_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid adding duplicate handlers if logger was previously instantiated
    if not logger.handlers:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(sh)

    setattr(logger, "run_id", safe_run_id)
    setattr(logger, "run_dir", str(run_dir))
    setattr(logger, "log_file", str(log_file))

    _run_loggers[key] = logger
    return logger


def write_run_summary(run_dir: str | Path, summary_data: Dict[str, Any]) -> None:
    """Writes machine-readable summary.json into the run folder."""
    path = Path(run_dir) / "summary.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, default=str)


def list_evaluation_runs(evaluation_id: str) -> List[Dict[str, Any]]:
    """Lists all stored run folders and metadata for an evaluation."""
    safe_eval_id = _sanitize_path_component(evaluation_id, "eval")
    eval_dir = Path(settings.log_dir).resolve() / safe_eval_id
    if not eval_dir.exists():
        return []

    runs = []
    for d in sorted(eval_dir.iterdir(), reverse=True):
        if d.is_dir():
            log_file = d / "run.log"
            summary_file = d / "summary.json"
            summary = {}
            if summary_file.exists():
                try:
                    with open(summary_file, "r", encoding="utf-8") as f:
                        summary = json.load(f)
                except Exception:
                    pass

            runs.append({
                "run_id": d.name,
                "folder_path": str(d),
                "has_log": log_file.exists(),
                "log_size_bytes": log_file.stat().st_size if log_file.exists() else 0,
                "created_at": datetime.fromtimestamp(d.stat().st_mtime, tz=timezone.utc).isoformat(),
                "summary": summary,
            })
    return runs


def read_run_log(evaluation_id: str, run_id: str, max_lines: int = 500) -> str:
    """Reads the content of run.log for a specific run."""
    safe_eval_id = _sanitize_path_component(evaluation_id, "eval")
    safe_run_id = _sanitize_path_component(run_id, "run_default")
    log_file = Path(settings.log_dir).resolve() / safe_eval_id / safe_run_id / "run.log"
    if not log_file.exists():
        return f"No log file found at {log_file}"

    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        return "".join(lines[-max_lines:])
