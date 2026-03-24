from __future__ import annotations


def render_markdown_summary(summary: dict[str, dict[str, float]]) -> str:
    lines = [
        '| Lane | Count | Avg completion | Avg execution price |',
        '|---|---:|---:|---:|',
    ]
    for lane, row in summary.items():
        lines.append(
            f"| {lane} | {int(row['count'])} | {row['avg_completion_ratio']:.4f} | {row['avg_execution_price']:.6f} |"
        )
    return '\n'.join(lines)
