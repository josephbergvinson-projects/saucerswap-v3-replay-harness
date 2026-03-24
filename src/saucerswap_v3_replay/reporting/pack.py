from __future__ import annotations

from ..metrics.summaries import aggregate_by_lane
from ..reporting.tables import render_markdown_summary
from ..schema import ExecutionRecord


def build_review_pack(records: list[ExecutionRecord]) -> str:
    summary = aggregate_by_lane(records)
    return render_markdown_summary(summary)
