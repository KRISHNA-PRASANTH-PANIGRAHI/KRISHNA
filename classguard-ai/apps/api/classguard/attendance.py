"""Connected-time calculation independent of camera, visibility or participation.

The caller supplies server-confirmed intervals and excluded teaching breaks.
Open or uncertain intervals contribute no inferred time and require review.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal


@dataclass(frozen=True)
class ConnectionInterval:
    joined_at: datetime
    left_at: datetime | None
    confirmed: bool = True


@dataclass(frozen=True)
class AttendanceSummary:
    connected_seconds: float
    eligible_seconds: float
    percentage: float | None
    review_status: Literal["complete", "requires_review"]


def _to_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("All timestamps must be timezone-aware datetimes")
    return value.astimezone(UTC)


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _seconds(intervals: list[tuple[datetime, datetime]]) -> float:
    return sum((end - start).total_seconds() for start, end in intervals)


def calculate_attendance(
    session_start: datetime,
    session_end: datetime,
    connections: list[ConnectionInterval],
    breaks: list[tuple[datetime, datetime]] | None = None,
) -> AttendanceSummary:
    """Union connections across devices, clamp to session and subtract break time.

    Reconnect gaps are not credited. This function accepts complete event intervals,
    not raw provider webhooks. Event deduplication and reconciliation are a future
    attendance-pipeline milestone. It intentionally produces no present/absent verdict.
    """
    session_start = _to_utc(session_start)
    session_end = _to_utc(session_end)
    if session_end < session_start:
        raise ValueError("Session end cannot precede session start")

    break_intervals: list[tuple[datetime, datetime]] = []
    for start, end in breaks or []:
        start, end = _to_utc(start), _to_utc(end)
        if end <= start:
            raise ValueError("Break end must be after break start")
        start, end = max(start, session_start), min(end, session_end)
        if end > start:
            break_intervals.append((start, end))
    merged_breaks = _merge_intervals(break_intervals)
    eligible_seconds = (session_end - session_start).total_seconds() - _seconds(merged_breaks)

    confirmed_intervals: list[tuple[datetime, datetime]] = []
    requires_review = False
    for connection in connections:
        joined_at = _to_utc(connection.joined_at)
        left_at = None
        if connection.left_at is not None:
            left_at = _to_utc(connection.left_at)
            if left_at < joined_at:
                raise ValueError("A connection cannot end before it begins")
        if not connection.confirmed or connection.left_at is None:
            requires_review = True
            continue
        start = max(joined_at, session_start)
        end = min(left_at, session_end)
        if end > start:
            confirmed_intervals.append((start, end))

    merged_connections = _merge_intervals(confirmed_intervals)
    excluded_connections = [
        (max(start, break_start), min(end, break_end))
        for start, end in merged_connections
        for break_start, break_end in merged_breaks
        if min(end, break_end) > max(start, break_start)
    ]
    connected_seconds = _seconds(merged_connections) - _seconds(excluded_connections)
    percentage = round(100 * connected_seconds / eligible_seconds, 2) if eligible_seconds else None
    return AttendanceSummary(
        connected_seconds=connected_seconds,
        eligible_seconds=eligible_seconds,
        percentage=percentage,
        review_status="requires_review" if requires_review or not eligible_seconds else "complete",
    )
