from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any

from .normalize.events import format_decimal

FEE_CONTRACT_VERSION = 'rh20_fee_extension_v1'
V2_FIXED_SCENARIO_ID = 'v2_fixed'
DEFAULT_V3_SCENARIO_ID = 'no_xsauce'
_RECIPIENT_KEYS = (
    'trader_fee_paid_usd',
    'protocol_fee_earned_usd',
    'active_lp_fee_earned_usd',
    'maker_rebate_earned_usd',
)


@dataclass
class FeeRollupStats:
    fee_basis_filled_notional_total: float = 0.0
    trader_fee_paid_total: float = 0.0
    protocol_fee_earned_total: float = 0.0
    active_lp_fee_earned_total: float = 0.0
    maker_rebate_earned_total: float = 0.0
    precise_fee_rows: int = 0
    v3_min_order_ineligible_rows: int = 0
    recipient_reconciliation_fail_rows: int = 0
    scenario_rollups: dict[str, dict[str, float]] = field(default_factory=dict)


def load_fee_policy(path: str | Path) -> dict[str, Any]:
    payload = _parse_mapping_yaml(Path(path).read_text(encoding='utf-8'))
    fees = payload.get('fees')
    if not isinstance(fees, dict):
        raise ValueError(f'{path} must define a top-level fees mapping')
    return fees


def v3_supported_scenarios(fee_policy: dict[str, Any]) -> list[str]:
    scenarios = fee_policy.get('v3_whbar_usdc', {}).get('scenarios', {})
    if not isinstance(scenarios, dict) or not scenarios:
        return [DEFAULT_V3_SCENARIO_ID]
    return [str(key) for key in scenarios.keys()]


def default_v3_scenario_id(fee_policy: dict[str, Any]) -> str:
    supported = v3_supported_scenarios(fee_policy)
    if DEFAULT_V3_SCENARIO_ID in supported:
        return DEFAULT_V3_SCENARIO_ID
    return supported[0]


def build_v2_fee_fields(
    fee_policy: dict[str, Any],
    *,
    filled_size: float,
    filled_notional: float,
    route_name: str = 'v2',
) -> dict[str, Any]:
    policy = _require_mapping(fee_policy, 'v2_whbar_usdc')
    trader_fee_bps = _require_float(policy, 'trader_fee_bps')
    protocol_fee_bps = _require_float(policy, 'protocol_fee_bps')
    active_lp_fee_bps = _require_float(policy, 'active_lp_fee_bps')

    recipient_allocations = {
        'trader_fee_paid_usd': amount_from_bps(filled_notional, trader_fee_bps),
        'protocol_fee_earned_usd': amount_from_bps(filled_notional, protocol_fee_bps),
        'active_lp_fee_earned_usd': amount_from_bps(filled_notional, active_lp_fee_bps),
        'maker_rebate_earned_usd': 0.0,
    }
    route_entry = {
        'route': route_name,
        'fee_model': 'v2_whbar_usdc',
        'filled_size': filled_size,
        'filled_notional_usd': filled_notional,
        'recipient_allocations': recipient_allocations,
    }
    return compose_fee_fields(
        route_entries={route_name: route_entry},
        default_scenario_id=V2_FIXED_SCENARIO_ID,
    )


def build_v3_fee_fields(
    fee_policy: dict[str, Any],
    *,
    requested_notional: float,
    filled_size: float,
    filled_notional: float,
    route_name: str = 'pure_book',
    default_scenario_id: str | None = None,
) -> dict[str, Any]:
    route_entry = build_v3_fee_route_entry(
        fee_policy,
        requested_notional=requested_notional,
        filled_size=filled_size,
        filled_notional=filled_notional,
        route_name=route_name,
    )
    return compose_fee_fields(
        route_entries={route_name: route_entry},
        default_scenario_id=default_scenario_id or default_v3_scenario_id(fee_policy),
    )


def build_hybrid_fee_fields(
    fee_policy: dict[str, Any],
    *,
    requested_notional: float,
    pure_book_filled_size: float,
    pure_book_filled_notional: float,
    v2_backstop_filled_size: float,
    v2_backstop_execution_price: float | None,
    default_scenario_id: str | None = None,
) -> dict[str, Any]:
    route_entries: dict[str, dict[str, Any]] = {}
    if pure_book_filled_size > 0 or pure_book_filled_notional > 0:
        route_entries['pure_book'] = build_v3_fee_route_entry(
            fee_policy,
            requested_notional=requested_notional,
            filled_size=pure_book_filled_size,
            filled_notional=pure_book_filled_notional,
            route_name='pure_book',
        )
    if v2_backstop_filled_size > 0 and v2_backstop_execution_price is not None:
        route_entries['v2_backstop'] = build_v2_fee_route_entry(
            fee_policy,
            filled_size=v2_backstop_filled_size,
            filled_notional=v2_backstop_filled_size * v2_backstop_execution_price,
            route_name='v2_backstop',
        )
    return compose_fee_fields(
        route_entries=route_entries,
        default_scenario_id=default_scenario_id or default_v3_scenario_id(fee_policy),
    )


def build_v2_fee_route_entry(
    fee_policy: dict[str, Any],
    *,
    filled_size: float,
    filled_notional: float,
    route_name: str,
) -> dict[str, Any]:
    fields = build_v2_fee_fields(
        fee_policy,
        filled_size=filled_size,
        filled_notional=filled_notional,
        route_name=route_name,
    )
    return _require_mapping(fields['fee_route_breakdown'], route_name)


def build_v3_fee_route_entry(
    fee_policy: dict[str, Any],
    *,
    requested_notional: float,
    filled_size: float,
    filled_notional: float,
    route_name: str,
) -> dict[str, Any]:
    policy = _require_mapping(fee_policy, 'v3_whbar_usdc')
    min_order_size_usdc = _require_float(policy, 'min_order_size_usdc')
    scenarios = _require_mapping(policy, 'scenarios')
    scenario_allocations: dict[str, dict[str, float]] = {}
    ordered_scenarios: list[str] = []
    for scenario_id, scenario_payload in scenarios.items():
        ordered_scenarios.append(str(scenario_id))
        if not isinstance(scenario_payload, dict):
            raise ValueError(f'Expected mapping at scenario {scenario_id!r}')
        scenario = scenario_payload
        scenario_allocations[str(scenario_id)] = {
            'trader_fee_paid_usd': amount_from_bps(
                filled_notional,
                _require_float(scenario, 'effective_taker_fee_bps'),
            ),
            'protocol_fee_earned_usd': amount_from_bps(
                filled_notional,
                _require_float(scenario, 'protocol_net_fee_bps'),
            ),
            'active_lp_fee_earned_usd': 0.0,
            'maker_rebate_earned_usd': amount_from_bps(
                filled_notional,
                _require_float(scenario, 'maker_rebate_bps'),
            ),
        }
    return {
        'route': route_name,
        'fee_model': 'v3_whbar_usdc',
        'filled_size': filled_size,
        'filled_notional_usd': filled_notional,
        'v3_min_order_ineligible': requested_notional < min_order_size_usdc,
        'ordered_scenarios': ordered_scenarios,
        'scenario_allocations': scenario_allocations,
    }


def compose_fee_fields(
    *,
    route_entries: dict[str, dict[str, Any]],
    default_scenario_id: str,
) -> dict[str, Any]:
    total_fee_basis = 0.0
    v3_min_order_ineligible = False
    for route_entry in route_entries.values():
        total_fee_basis += float(route_entry.get('filled_notional_usd', 0.0))
        v3_min_order_ineligible = v3_min_order_ineligible or bool(route_entry.get('v3_min_order_ineligible', False))

    scenario_totals = scenario_totals_from_breakdown(route_entries)
    selected_scenario_id = default_scenario_id
    if selected_scenario_id not in scenario_totals:
        selected_scenario_id = next(iter(scenario_totals.keys()), V2_FIXED_SCENARIO_ID)
    selected = scenario_totals.get(selected_scenario_id, zero_recipient_allocations())

    return {
        'fee_contract_version': FEE_CONTRACT_VERSION,
        'fee_scenario_id': selected_scenario_id,
        'v3_min_order_ineligible': v3_min_order_ineligible,
        'fee_basis_filled_notional_usd': total_fee_basis,
        'trader_fee_paid_usd': float(selected['trader_fee_paid_usd']),
        'protocol_fee_earned_usd': float(selected['protocol_fee_earned_usd']),
        'active_lp_fee_earned_usd': float(selected['active_lp_fee_earned_usd']),
        'maker_rebate_earned_usd': float(selected['maker_rebate_earned_usd']),
        'fees_paid': float(selected['trader_fee_paid_usd']),
        'fee_route_breakdown': route_entries,
    }


def scenario_totals_from_breakdown(route_entries: dict[str, Any]) -> dict[str, dict[str, float]]:
    fixed_routes: list[dict[str, float]] = []
    ordered_scenario_ids: list[str] = []
    scenario_routes: list[dict[str, Any]] = []

    for route_entry in route_entries.values():
        if not isinstance(route_entry, dict):
            continue
        scenario_allocations = route_entry.get('scenario_allocations')
        if isinstance(scenario_allocations, dict):
            scenario_routes.append(route_entry)
            for scenario_id in route_entry.get('ordered_scenarios') or scenario_allocations.keys():
                text = str(scenario_id)
                if text not in ordered_scenario_ids:
                    ordered_scenario_ids.append(text)
            continue
        recipient_allocations = route_entry.get('recipient_allocations')
        if isinstance(recipient_allocations, dict):
            fixed_routes.append(recipient_allocations)

    if not ordered_scenario_ids:
        total = zero_recipient_allocations()
        for fixed in fixed_routes:
            add_allocations(total, fixed)
        return {V2_FIXED_SCENARIO_ID: total}

    scenario_totals: dict[str, dict[str, float]] = {}
    for scenario_id in ordered_scenario_ids:
        total = zero_recipient_allocations()
        for fixed in fixed_routes:
            add_allocations(total, fixed)
        for route_entry in scenario_routes:
            scenario_allocations = route_entry.get('scenario_allocations', {})
            add_allocations(total, scenario_allocations.get(scenario_id, {}))
        scenario_totals[scenario_id] = total
    return scenario_totals


def add_record_fee_rollups(fee_rollups: FeeRollupStats, record: Any) -> None:
    fee_rollups.precise_fee_rows += 1
    fee_rollups.fee_basis_filled_notional_total += float(getattr(record, 'fee_basis_filled_notional_usd', 0.0))
    fee_rollups.trader_fee_paid_total += float(getattr(record, 'trader_fee_paid_usd', 0.0))
    fee_rollups.protocol_fee_earned_total += float(getattr(record, 'protocol_fee_earned_usd', 0.0))
    fee_rollups.active_lp_fee_earned_total += float(getattr(record, 'active_lp_fee_earned_usd', 0.0))
    fee_rollups.maker_rebate_earned_total += float(getattr(record, 'maker_rebate_earned_usd', 0.0))
    if bool(getattr(record, 'v3_min_order_ineligible', False)):
        fee_rollups.v3_min_order_ineligible_rows += 1
    if not reconciliation_holds(
        trader_fee_paid_usd=float(getattr(record, 'trader_fee_paid_usd', 0.0)),
        protocol_fee_earned_usd=float(getattr(record, 'protocol_fee_earned_usd', 0.0)),
        active_lp_fee_earned_usd=float(getattr(record, 'active_lp_fee_earned_usd', 0.0)),
        maker_rebate_earned_usd=float(getattr(record, 'maker_rebate_earned_usd', 0.0)),
    ):
        fee_rollups.recipient_reconciliation_fail_rows += 1

    scenario_totals = scenario_totals_from_breakdown(getattr(record, 'fee_route_breakdown', {}) or {})
    for scenario_id, allocations in scenario_totals.items():
        rollup = fee_rollups.scenario_rollups.setdefault(
            scenario_id,
            {
                'fee_basis_filled_notional_total': 0.0,
                'trader_fee_paid_total': 0.0,
                'protocol_fee_earned_total': 0.0,
                'active_lp_fee_earned_total': 0.0,
                'maker_rebate_earned_total': 0.0,
            },
        )
        rollup['fee_basis_filled_notional_total'] += float(getattr(record, 'fee_basis_filled_notional_usd', 0.0))
        rollup['trader_fee_paid_total'] += float(allocations.get('trader_fee_paid_usd', 0.0))
        rollup['protocol_fee_earned_total'] += float(allocations.get('protocol_fee_earned_usd', 0.0))
        rollup['active_lp_fee_earned_total'] += float(allocations.get('active_lp_fee_earned_usd', 0.0))
        rollup['maker_rebate_earned_total'] += float(allocations.get('maker_rebate_earned_usd', 0.0))


def build_fee_summary_payload(
    *,
    fee_rollups: FeeRollupStats,
    requested_notional_total: float,
    default_scenario_id: str,
    supported_scenarios: list[str],
) -> dict[str, Any]:
    default_totals = {
        'fee_basis_filled_notional_total': fee_rollups.fee_basis_filled_notional_total,
        'trader_fee_paid_total': fee_rollups.trader_fee_paid_total,
        'protocol_fee_earned_total': fee_rollups.protocol_fee_earned_total,
        'active_lp_fee_earned_total': fee_rollups.active_lp_fee_earned_total,
        'maker_rebate_earned_total': fee_rollups.maker_rebate_earned_total,
    }
    scenario_ids = supported_scenarios or list(fee_rollups.scenario_rollups.keys()) or [default_scenario_id]
    scenario_rollups = {
        scenario_id: serialize_fee_rollup(
            fee_basis_total=float(
                fee_rollups.scenario_rollups.get(scenario_id, {}).get(
                    'fee_basis_filled_notional_total',
                    default_totals['fee_basis_filled_notional_total'],
                )
            ),
            requested_notional_total=requested_notional_total,
            trader_fee_paid_total=float(
                fee_rollups.scenario_rollups.get(scenario_id, {}).get(
                    'trader_fee_paid_total',
                    default_totals['trader_fee_paid_total'],
                )
            ),
            protocol_fee_earned_total=float(
                fee_rollups.scenario_rollups.get(scenario_id, {}).get(
                    'protocol_fee_earned_total',
                    default_totals['protocol_fee_earned_total'],
                )
            ),
            active_lp_fee_earned_total=float(
                fee_rollups.scenario_rollups.get(scenario_id, {}).get(
                    'active_lp_fee_earned_total',
                    default_totals['active_lp_fee_earned_total'],
                )
            ),
            maker_rebate_earned_total=float(
                fee_rollups.scenario_rollups.get(scenario_id, {}).get(
                    'maker_rebate_earned_total',
                    default_totals['maker_rebate_earned_total'],
                )
            ),
        )
        for scenario_id in scenario_ids
    }
    return {
        'fee_contract_version': FEE_CONTRACT_VERSION,
        'default_scenario_id': default_scenario_id,
        'supported_scenarios': scenario_ids,
        'v3_min_order_ineligible_rows': fee_rollups.v3_min_order_ineligible_rows,
        'recipient_reconciliation_fail_rows': fee_rollups.recipient_reconciliation_fail_rows,
        'recipient_reconciliation_pass': fee_rollups.recipient_reconciliation_fail_rows == 0,
        'default_rollup': serialize_fee_rollup(
            fee_basis_total=default_totals['fee_basis_filled_notional_total'],
            requested_notional_total=requested_notional_total,
            trader_fee_paid_total=default_totals['trader_fee_paid_total'],
            protocol_fee_earned_total=default_totals['protocol_fee_earned_total'],
            active_lp_fee_earned_total=default_totals['active_lp_fee_earned_total'],
            maker_rebate_earned_total=default_totals['maker_rebate_earned_total'],
        ),
        'scenario_rollups': scenario_rollups,
    }


def serialize_fee_rollup(
    *,
    fee_basis_total: float,
    requested_notional_total: float,
    trader_fee_paid_total: float,
    protocol_fee_earned_total: float,
    active_lp_fee_earned_total: float,
    maker_rebate_earned_total: float,
) -> dict[str, Any]:
    return {
        'fee_basis_filled_notional_usd': format_decimal(fee_basis_total),
        'requested_notional_usdc': format_decimal(requested_notional_total),
        'trader_fee_paid_usd': format_decimal(trader_fee_paid_total),
        'protocol_fee_earned_usd': format_decimal(protocol_fee_earned_total),
        'active_lp_fee_earned_usd': format_decimal(active_lp_fee_earned_total),
        'maker_rebate_earned_usd': format_decimal(maker_rebate_earned_total),
        'trader_fee_paid_bps_on_filled_notional': bps(trader_fee_paid_total, fee_basis_total),
        'protocol_fee_earned_bps_on_filled_notional': bps(protocol_fee_earned_total, fee_basis_total),
        'active_lp_fee_earned_bps_on_filled_notional': bps(active_lp_fee_earned_total, fee_basis_total),
        'maker_rebate_earned_bps_on_filled_notional': bps(maker_rebate_earned_total, fee_basis_total),
        'trader_fee_paid_bps_on_requested_notional': bps(trader_fee_paid_total, requested_notional_total),
        'protocol_fee_earned_bps_on_requested_notional': bps(protocol_fee_earned_total, requested_notional_total),
        'active_lp_fee_earned_bps_on_requested_notional': bps(
            active_lp_fee_earned_total,
            requested_notional_total,
        ),
        'maker_rebate_earned_bps_on_requested_notional': bps(
            maker_rebate_earned_total,
            requested_notional_total,
        ),
    }


def reconciliation_holds(
    *,
    trader_fee_paid_usd: float,
    protocol_fee_earned_usd: float,
    active_lp_fee_earned_usd: float,
    maker_rebate_earned_usd: float,
    tolerance: float = 1e-9,
) -> bool:
    return math.isclose(
        trader_fee_paid_usd,
        protocol_fee_earned_usd + active_lp_fee_earned_usd + maker_rebate_earned_usd,
        rel_tol=0.0,
        abs_tol=tolerance,
    )


def amount_from_bps(notional: float, bps_value: float) -> float:
    return float(notional) * float(bps_value) / 10_000.0


def bps(amount: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((amount / denominator) * 10_000.0, 12)


def zero_recipient_allocations() -> dict[str, float]:
    return {key: 0.0 for key in _RECIPIENT_KEYS}


def add_allocations(target: dict[str, float], source: dict[str, Any]) -> None:
    for key in _RECIPIENT_KEYS:
        target[key] = float(target.get(key, 0.0)) + float(source.get(key, 0.0))


def _parse_mapping_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith('- '):
            raise ValueError('fees.yaml fallback parser does not support list items')
        indent = len(line) - len(line.lstrip(' '))
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        key, sep, value = stripped.partition(':')
        if not sep:
            raise ValueError(f'Unsupported YAML line: {raw_line!r}')
        key = key.strip()
        value = value.strip()
        if not value:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
            continue
        parent[key] = _coerce_scalar(value)
    return root


def _coerce_scalar(value: str) -> Any:
    text = value.strip()
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    lowered = text.lower()
    if lowered == 'true':
        return True
    if lowered == 'false':
        return False
    if lowered == 'null':
        return None
    try:
        if any(ch in text for ch in ('.', 'e', 'E')):
            return float(text)
        return int(text)
    except ValueError:
        return text


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f'Expected mapping at {key!r}')
    return value


def _require_float(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if value is None:
        raise ValueError(f'Missing required fee scalar {key!r}')
    return float(value)
