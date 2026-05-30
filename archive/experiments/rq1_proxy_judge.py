"""Thin CLI helper for merging offline Cursor-proxy plain-LLM adjudication payloads."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.rq1_llm_judge import (
    DEFAULT_PLAIN_LLM_LIVE_PROXY,
    DEFAULT_SUMMARY,
    DEFAULT_TEMPLATE,
    merge_plain_llm_live_scores,
    summarize_from_template,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="RQ1 plain-LLM proxy judge hydration (offline JSON)")
    parser.add_argument("--scores", type=Path, default=DEFAULT_PLAIN_LLM_LIVE_PROXY)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--no-write-template", action="store_true")
    args = parser.parse_args(argv)

    template_path = Path(args.template)
    tpl = json.loads(template_path.read_text(encoding="utf-8"))
    score_path = Path(args.scores).expanduser().resolve()

    merged = merge_plain_llm_live_scores(tpl, score_path)
    summary = summarize_from_template(tpl)

    if not args.no_write_template:
        template_path.write_text(json.dumps(tpl, indent=2) + "\n", encoding="utf-8")

    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    merged["summary_path"] = str(summary_path)
    print(json.dumps(merged, indent=2))


if __name__ == "__main__":
    main()
