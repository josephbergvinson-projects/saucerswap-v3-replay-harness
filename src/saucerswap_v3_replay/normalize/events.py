from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any

from ..schema import ReplayUnit

HBAR_DECIMALS = 8
USDC_DECIMALS = 6


@dataclass(frozen=True)
class NormalizedEvent:
    trade_row_id: int
    swap_event_id: str
    trade_timestamp_seconds: int
    timestamp: str
    side: str
    requested_size: float
    requested_notional: float
    observed_execution_price: float
    reference_price: float
    reference_price_source: str
    reference_price_fallback: bool
    swap_metadata_covered: bool
    fee_covered: bool
    base_id: str
    target_id: str
    base_volume_raw: int
    target_volume_raw: int
    source_ordering_key: str
    amount_a: str = ''
    amount_b: str = ''
    sqrt_ratio_x96: str = ''
    liquidity: str = ''

    @property
    def replay_unit_id(self) -> str:
        return f'swap:{self.swap_event_id}:trade:{self.trade_row_id}'

    def to_replay_unit(self) -> ReplayUnit:
        return ReplayUnit(
            replay_unit_id=self.replay_unit_id,
            timestamp=self.timestamp,
            tx_id=self.swap_event_id,
            event_index=self.trade_row_id,
            side=self.side,
            requested_size=self.requested_size,
            requested_notional=self.requested_notional,
            reference_price=self.reference_price,
            metadata={
                'source_ordering_key': self.source_ordering_key,
                'observed_execution_price': self.observed_execution_price,
                'base_id': self.base_id,
                'target_id': self.target_id,
                'base_volume_raw': self.base_volume_raw,
                'target_volume_raw': self.target_volume_raw,
            },
            trade_row_id=self.trade_row_id,
            swap_event_id=self.swap_event_id,
            trade_timestamp_seconds=self.trade_timestamp_seconds,
            reference_price_source=self.reference_price_source,
            reference_price_fallback=self.reference_price_fallback,
            swap_metadata_covered=self.swap_metadata_covered,
            fee_covered=self.fee_covered,
        )

    def as_normalized_row(self) -> dict[str, str]:
        return {
            'replay_unit_id': self.replay_unit_id,
            'timestamp': self.timestamp,
            'source_ordering_key': self.source_ordering_key,
            'tradeRowId': str(self.trade_row_id),
            'swapEventId': self.swap_event_id,
            'tradeTimestampSeconds': str(self.trade_timestamp_seconds),
            'side': self.side,
            'baseId': self.base_id,
            'targetId': self.target_id,
            'baseVolumeRaw': str(self.base_volume_raw),
            'targetVolumeRaw': str(self.target_volume_raw),
            'amountA': self.amount_a,
            'amountB': self.amount_b,
            'sqrtRatioX96': self.sqrt_ratio_x96,
            'liquidity': self.liquidity,
            'requested_size': format_scaled_int(self.target_volume_raw, HBAR_DECIMALS),
            'requested_notional': format_scaled_int(self.base_volume_raw, USDC_DECIMALS),
            'observed_execution_price': format_decimal(self.observed_execution_price),
            'reference_price': format_decimal(self.reference_price),
            'reference_price_source': self.reference_price_source,
            'reference_price_fallback': format_bool(self.reference_price_fallback),
            'swap_metadata_covered': format_bool(self.swap_metadata_covered),
            'fee_covered': format_bool(self.fee_covered),
        }

    def as_replay_row(self) -> dict[str, str]:
        return {
            'replay_unit_id': self.replay_unit_id,
            'timestamp': self.timestamp,
            'tx_id': self.swap_event_id,
            'event_index': str(self.trade_row_id),
            'side': self.side,
            'requested_size': format_scaled_int(self.target_volume_raw, HBAR_DECIMALS),
            'requested_notional': format_scaled_int(self.base_volume_raw, USDC_DECIMALS),
            'reference_price': format_decimal(self.reference_price),
            'tradeRowId': str(self.trade_row_id),
            'swapEventId': self.swap_event_id,
            'tradeTimestampSeconds': str(self.trade_timestamp_seconds),
            'reference_price_source': self.reference_price_source,
            'reference_price_fallback': format_bool(self.reference_price_fallback),
            'swap_metadata_covered': format_bool(self.swap_metadata_covered),
            'fee_covered': format_bool(self.fee_covered),
        }


NORMALIZED_EVENT_FIELDNAMES = [
    'replay_unit_id',
    'timestamp',
    'source_ordering_key',
    'tradeRowId',
    'swapEventId',
    'tradeTimestampSeconds',
    'side',
    'baseId',
    'targetId',
    'baseVolumeRaw',
    'targetVolumeRaw',
    'amountA',
    'amountB',
    'sqrtRatioX96',
    'liquidity',
    'requested_size',
    'requested_notional',
    'observed_execution_price',
    'reference_price',
    'reference_price_source',
    'reference_price_fallback',
    'swap_metadata_covered',
    'fee_covered',
]

REPLAY_UNIT_FIELDNAMES = [
    'replay_unit_id',
    'timestamp',
    'tx_id',
    'event_index',
    'side',
    'requested_size',
    'requested_notional',
    'reference_price',
    'tradeRowId',
    'swapEventId',
    'tradeTimestampSeconds',
    'reference_price_source',
    'reference_price_fallback',
    'swap_metadata_covered',
    'fee_covered',
]


def clean_numeric_string(value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError('Numeric value is blank')
    return text.replace(',', '')


def parse_int(value: Any) -> int:
    text = clean_numeric_string(value)
    if '.' in text:
        return int(float(text))
    return int(text)


def parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return parse_int(text)


def parse_float(value: Any) -> float:
    return float(clean_numeric_string(value))


def parse_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == 'null':
        return None
    return parse_float(text)


def parse_timestamp_seconds(value: Any) -> int:
    text = clean_numeric_string(value)
    return math.floor(float(text))


def scale_int(value: int, decimals: int) -> float:
    return value / (10 ** decimals)


def format_scaled_int(value: int, decimals: int) -> str:
    negative = value < 0
    value = abs(value)
    whole = value // (10 ** decimals)
    fraction = value % (10 ** decimals)
    if fraction == 0:
        text = str(whole)
    else:
        text = f'{whole}.{fraction:0{decimals}d}'.rstrip('0')
    if negative and text != '0':
        return f'-{text}'
    return text


def iso_utc(timestamp_seconds: int) -> str:
    return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def format_decimal(value: float, places: int = 12) -> str:
    text = f'{value:.{places}f}'
    text = text.rstrip('0').rstrip('.')
    return text or '0'


def format_bool(value: bool) -> str:
    return 'true' if value else 'false'


def clean_optional_numeric_string(value: Any) -> str:
    if value is None:
        return ''
    text = str(value).strip()
    if not text or text.lower() == 'null':
        return ''
    return clean_numeric_string(text)


def infer_side(
    amount_base_in: float | int | None = None,
    amount_base_out: float | int | None = None,
    *,
    amount_b: int | None = None,
) -> str:
    if amount_b is not None:
        if amount_b < 0:
            return 'buy'
        if amount_b > 0:
            return 'sell'
        raise ValueError('Could not infer side from amountB sign')
    if amount_base_in is None or amount_base_out is None:
        raise ValueError('Could not infer side from event amounts')
    if amount_base_in > 0 and amount_base_out == 0:
        return 'sell'
    if amount_base_out > 0 and amount_base_in == 0:
        return 'buy'
    raise ValueError('Could not infer side from event amounts')


def has_explicit_side(explicit_type: str | None) -> bool:
    if not explicit_type:
        return False
    return explicit_type.strip().lower() in {'buy', 'sell'}


def normalize_side(explicit_type: str | None, amount_b: int | None = None) -> str:
    if has_explicit_side(explicit_type):
        return str(explicit_type).strip().lower()
    return infer_side(amount_b=amount_b)


def build_source_ordering_key(trade_timestamp_seconds: int, swap_event_id: str, trade_row_id: int) -> str:
    return f'{trade_timestamp_seconds:010d}:{int(swap_event_id):020d}:{trade_row_id:020d}'


def normalize_trade_row(
    row: dict[str, Any],
    *,
    reference_price: float,
    reference_price_source: str,
    reference_price_fallback: bool,
    swap_metadata_covered: bool,
    fee_covered: bool,
) -> NormalizedEvent:
    trade_row_id = parse_int(row['tradeRowId'])
    swap_event_id = str(parse_int(row['swapEventId']))
    trade_timestamp_seconds = parse_timestamp_seconds(row['tradeTimestampSeconds'])
    amount_b = parse_optional_int(row.get('amountB'))
    side = normalize_side(row.get('type'), amount_b=amount_b)
    base_volume_raw = parse_int(row['baseVolume'])
    target_volume_raw = parse_int(row['targetVolume'])
    requested_notional = scale_int(base_volume_raw, USDC_DECIMALS)
    requested_size = scale_int(target_volume_raw, HBAR_DECIMALS)
    observed_execution_price = (
        requested_notional / requested_size if requested_size > 0 else reference_price
    )
    return NormalizedEvent(
        trade_row_id=trade_row_id,
        swap_event_id=swap_event_id,
        trade_timestamp_seconds=trade_timestamp_seconds,
        timestamp=iso_utc(trade_timestamp_seconds),
        side=side,
        requested_size=requested_size,
        requested_notional=requested_notional,
        observed_execution_price=observed_execution_price,
        reference_price=reference_price,
        reference_price_source=reference_price_source,
        reference_price_fallback=reference_price_fallback,
        swap_metadata_covered=swap_metadata_covered,
        fee_covered=fee_covered,
        base_id=str(row.get('baseId', '')).strip(),
        target_id=str(row.get('targetId', '')).strip(),
        base_volume_raw=base_volume_raw,
        target_volume_raw=target_volume_raw,
        amount_a=clean_optional_numeric_string(row.get('amountA')),
        amount_b=clean_optional_numeric_string(row.get('amountB')),
        sqrt_ratio_x96=clean_optional_numeric_string(row.get('sqrtRatioX96')),
        liquidity=clean_optional_numeric_string(row.get('liquidity')),
        source_ordering_key=build_source_ordering_key(
            trade_timestamp_seconds=trade_timestamp_seconds,
            swap_event_id=swap_event_id,
            trade_row_id=trade_row_id,
        ),
    )
