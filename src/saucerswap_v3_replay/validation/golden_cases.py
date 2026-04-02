from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ..backstop.v2_residual import ResidualQuote
from ..fees import load_fee_policy
from ..metrics.core import slippage_bps
from ..normalize.events import format_decimal, parse_float, parse_int
from ..schema import ExecutionRecord, ReplayUnit
from ..sim.book_profile import BookProfile, load_book_profile
from ..sim.hybrid import simulate_hybrid
from ..sim.pure_book import simulate_pure_book
from .determinism import fingerprint_payload

PURE_BOOK_LANE = '3a_pure_book'
HYBRID_LANE = '3b_hybrid'


@dataclass(frozen=True)
class GoldenCase:
    name: str
    lane: str
    replay_unit: ReplayUnit
    v2_execution_price: float | None = None
    v2_available_size: float | None = None

    def residual_quote(self) -> ResidualQuote | None:
        if self.v2_execution_price is None or self.v2_available_size is None:
            return None
        return ResidualQuote(
            execution_price=self.v2_execution_price,
            available_size=self.v2_available_size,
            source='toy_fixture_v2_quote',
            replay_unit_id=self.replay_unit.replay_unit_id,
            trade_row_id=self.replay_unit.trade_row_id,
            swap_event_id=self.replay_unit.swap_event_id,
            trade_timestamp_seconds=self.replay_unit.trade_timestamp_seconds,
        )


@dataclass(frozen=True)
class GoldenCaseResult:
    name: str
    lane: str
    replay_unit_id: str
    actual: dict[str, Any]
    expected: dict[str, Any]
    checks: dict[str, bool]
    status: str


def evaluate_golden_cases(
    book_path: str | Path,
    flow_path: str | Path,
    expected_path: str | Path,
    fee_config_path: str | Path | None = None,
) -> dict[str, Any]:
    book_profile = load_book_profile(book_path)
    fee_policy = load_fee_policy(fee_config_path or Path('config/fees.yaml'))
    flow_cases = load_golden_case_flow(flow_path)
    expected_payload = json.loads(Path(expected_path).read_text(encoding='utf-8'))
    hybrid_rule = expected_payload.get('hybrid_rule', {})
    max_buy_slippage_bps = float(hybrid_rule.get('max_buy_slippage_bps', 50.0))
    max_sell_slippage_bps = float(hybrid_rule.get('max_sell_slippage_bps', 50.0))

    case_results: list[GoldenCaseResult] = []
    for case_spec in expected_payload.get('cases', []):
        case_name = str(case_spec['name'])
        case = flow_cases[case_name]
        actual = evaluate_case(
            case,
            book_profile=book_profile,
            fee_policy=fee_policy,
            max_buy_slippage_bps=max_buy_slippage_bps,
            max_sell_slippage_bps=max_sell_slippage_bps,
        )
        expected = normalize_expected_payload(case_spec['expected'])
        checks = compare_actual_to_expected(actual, expected)
        status = 'pass' if all(checks.values()) else 'fail'
        case_results.append(
            GoldenCaseResult(
                name=case_name,
                lane=case.lane,
                replay_unit_id=case.replay_unit.replay_unit_id,
                actual=actual,
                expected=expected,
                checks=checks,
                status=status,
            )
        )

    rendered_cases = [render_case_result(result) for result in case_results]
    pass_count = sum(1 for result in case_results if result.status == 'pass')
    fail_count = len(case_results) - pass_count
    fingerprint = fingerprint_payload(
        {
            'book': render_book_profile(book_profile),
            'hybrid_rule': {
                'max_buy_slippage_bps': max_buy_slippage_bps,
                'max_sell_slippage_bps': max_sell_slippage_bps,
            },
            'cases': rendered_cases,
        }
    )
    return {
        'notes': str(expected_payload.get('notes') or ''),
        'fixtures': {
            'toy_book_path': str(Path(book_path)),
            'toy_flow_path': str(Path(flow_path)),
            'toy_expected_outputs_path': str(Path(expected_path)),
        },
        'book': render_book_profile(book_profile),
        'hybrid_rule': {
            'max_buy_slippage_bps': format_decimal(max_buy_slippage_bps),
            'max_sell_slippage_bps': format_decimal(max_sell_slippage_bps),
        },
        'counts': {
            'case_count': len(rendered_cases),
            'pass_count': pass_count,
            'fail_count': fail_count,
        },
        'status': 'pass' if fail_count == 0 else 'fail',
        'fingerprint': fingerprint,
        'cases': rendered_cases,
    }


def load_golden_case_flow(path: str | Path) -> dict[str, GoldenCase]:
    flow_path = Path(path)
    cases: dict[str, GoldenCase] = {}
    with flow_path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            case_name = row['case_name']
            if case_name in cases:
                raise ValueError(f'Duplicate golden-case row for {case_name!r}')
            replay_unit = ReplayUnit(
                replay_unit_id=row['replay_unit_id'],
                timestamp=row['timestamp'],
                tx_id=row['tx_id'],
                event_index=parse_int(row['event_index']),
                side=row['side'],
                requested_size=parse_float(row['requested_size']),
                requested_notional=parse_float(row['requested_notional']),
                reference_price=parse_float(row['reference_price']),
            )
            v2_execution_price = parse_optional_float(row.get('v2_execution_price'))
            v2_available_size = parse_optional_float(row.get('v2_available_size'))
            cases[case_name] = GoldenCase(
                name=case_name,
                lane=row['lane'],
                replay_unit=replay_unit,
                v2_execution_price=v2_execution_price,
                v2_available_size=v2_available_size,
            )
    return cases


def evaluate_case(
    case: GoldenCase,
    *,
    book_profile: BookProfile,
    fee_policy: dict[str, Any],
    max_buy_slippage_bps: float,
    max_sell_slippage_bps: float,
) -> dict[str, Any]:
    replay_unit = case.replay_unit
    if case.lane == PURE_BOOK_LANE:
        record = simulate_pure_book(replay_unit, list(book_profile.levels), fee_policy)
    elif case.lane == HYBRID_LANE:
        record = simulate_hybrid(
            replay_unit,
            list(book_profile.levels),
            case.residual_quote(),
            max_slippage_bps=(
                max_buy_slippage_bps if replay_unit.side == 'buy' else max_sell_slippage_bps
            ),
            fee_policy=fee_policy,
        )
    else:
        raise ValueError(f'Unsupported golden-case lane: {case.lane}')

    execution_slippage_bps = 0.0
    if record.filled_size > 0:
        execution_slippage_bps = slippage_bps(
            replay_unit.reference_price,
            record.avg_execution_price,
            replay_unit.side,
        )
    return render_execution_record(record, execution_slippage_bps=execution_slippage_bps)


def render_execution_record(record: ExecutionRecord, *, execution_slippage_bps: float) -> dict[str, Any]:
    return {
        'lane': record.lane,
        'replay_unit_id': record.replay_unit_id,
        'side': record.side,
        'requested_size': format_decimal(record.requested_size),
        'requested_notional': format_decimal(record.requested_notional),
        'filled_size': format_decimal(record.filled_size),
        'filled_notional': format_decimal(record.filled_notional),
        'completion_ratio': format_decimal(record.completion_ratio),
        'reference_price': format_decimal(record.reference_price),
        'avg_execution_price': format_decimal(record.avg_execution_price),
        'execution_slippage_bps': format_decimal(execution_slippage_bps),
        'remainder_size': format_decimal(record.remainder_size),
        'route_breakdown': {
            key: format_decimal(value) for key, value in sorted(record.route_breakdown.items())
        },
        'admissibility_passed': record.admissibility_passed,
    }


def normalize_expected_payload(expected: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(expected)
    route_breakdown = normalized.get('route_breakdown')
    if isinstance(route_breakdown, dict):
        normalized['route_breakdown'] = {
            str(key): str(value) for key, value in sorted(route_breakdown.items())
        }
    return normalized


def compare_actual_to_expected(actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for key, expected_value in expected.items():
        checks[key] = actual.get(key) == expected_value
    return checks


def render_book_profile(book_profile: BookProfile) -> dict[str, Any]:
    return {
        'total_depth_usd': format_decimal(book_profile.total_depth_usd),
        'replenish_per_replay_unit': book_profile.replenish_per_replay_unit,
        'levels': [
            {
                'spread_bps': format_decimal(level.spread_bps),
                'size_usd': format_decimal(level.size_usd),
            }
            for level in book_profile.levels
        ],
        'fingerprint': book_profile.fingerprint,
    }


def render_case_result(result: GoldenCaseResult) -> dict[str, Any]:
    checked_fields = list(result.checks.keys())
    return {
        'name': result.name,
        'lane': result.lane,
        'replay_unit_id': result.replay_unit_id,
        'checked_fields': checked_fields,
        'check_summary': f'{sum(1 for value in result.checks.values() if value)}/{len(result.checks)}',
        'checks': result.checks,
        'status': result.status,
        'actual': result.actual,
        'expected': result.expected,
    }


def parse_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return parse_float(text)
