#!/usr/bin/env python3
"""Select the best generated image candidate from QA reports.

This supports a best-of-N workflow: generate 3-6 candidates with the same
shared brief, run sprite QA + vision critique on each, then keep only the
highest-scoring candidate. This prevents the common AI-art failure where the
first acceptable-looking sample becomes canon.

Input schema:
{
  "candidates": [
    {"id": "rock_v01", "image": "rock_v01.png", "sprite_qa": "rock_v01.sprite-qa.json", "critique": "rock_v01.critique.json"}
  ]
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get(d: Any, path: str, default=None):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def score_candidate(c: dict) -> dict:
    sprite = load(c.get("sprite_qa")) if c.get("sprite_qa") else None
    critique = load(c.get("critique")) if c.get("critique") else None

    sprite_failures = get(sprite, "summary.failures", 0) if sprite else 0
    sprite_warnings = get(sprite, "summary.warnings", 0) if sprite else 0
    sprite_pass = (sprite is None) or (get(sprite, "result") == "pass" and sprite_failures == 0)

    verdict = get(critique, "critique.verdict", get(critique, "verdict")) if critique else "pass"
    overall = get(critique, "critique.overall", get(critique, "overall", 2.0)) if critique else 2.0
    scores = get(critique, "critique.scores", {}) if critique else {}
    subject_score = scores.get("subject_correct", 3)
    critique_pass = verdict == "pass" and subject_score > 1

    axis_avg = (sum(v for v in scores.values() if isinstance(v, (int, float))) / len(scores)) if scores else 2.0
    hard_fail = not sprite_pass or not critique_pass
    score = 0.0
    score += float(overall) * 10.0
    score += axis_avg * 5.0
    score -= sprite_failures * 100.0
    score -= sprite_warnings * 2.0
    if hard_fail:
        score -= 1000.0

    return {
        "id": c.get("id"),
        "image": c.get("image"),
        "score": score,
        "eligible": not hard_fail,
        "sprite_failures": sprite_failures,
        "sprite_warnings": sprite_warnings,
        "critique_verdict": verdict,
        "critique_overall": overall,
        "subject_correct": subject_score,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Select best image candidate from sprite QA + critique reports.")
    p.add_argument("--candidates", required=True, help="JSON file with candidates[]")
    p.add_argument("--json-report", help="Write selection report")
    args = p.parse_args()

    data = load(args.candidates)
    candidates = data.get("candidates", [])
    scored = [score_candidate(c) for c in candidates]
    scored.sort(key=lambda x: x["score"], reverse=True)
    eligible = [s for s in scored if s["eligible"]]
    winner = eligible[0] if eligible else (scored[0] if scored else None)
    report = {
        "schema": "unity-game-skills.best-candidate.v1",
        "result": "pass" if winner and winner["eligible"] else "fail",
        "winner": winner,
        "candidates": scored,
    }
    text = json.dumps(report, indent=2)
    if args.json_report:
        Path(args.json_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_report).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
