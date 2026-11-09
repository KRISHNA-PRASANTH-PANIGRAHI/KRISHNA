from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from classguard.attendance import ConnectionInterval, calculate_attendance

START = datetime(2026, 11, 3, 10, tzinfo=UTC)
END = START + timedelta(hours=1)


def minute(value: int) -> datetime:
    return START + timedelta(minutes=value)


def connection(start: int, end: int | None, confirmed: bool = True) -> ConnectionInterval:
    return ConnectionInterval(minute(start), minute(end) if end is not None else None, confirmed)


def test_overlapping_devices_and_duplicate_events_do_not_inflate_attendance():
    result = calculate_attendance(START, END, [
        connection(-5, 20), connection(10, 40), connection(10, 40), connection(40, 70),
    ])
    assert result.connected_seconds == 3600
    assert result.percentage == 100
    assert result.review_status == "complete"


def test_reconnect_gap_remains_disconnected_and_breaks_are_excluded_once():
    result = calculate_attendance(
        START,
        END,
        [connection(0, 20), connection(25, 60)],
        [(minute(30), minute(40)), (minute(35), minute(45))],
    )
    assert result.eligible_seconds == 45 * 60
    assert result.connected_seconds == 40 * 60
    assert result.percentage == 88.89


def test_open_and_uncertain_connections_require_review_without_inventing_time():
    result = calculate_attendance(START, END, [
        connection(0, 10), connection(10, 40, confirmed=False), connection(40, None),
    ])
    assert result.connected_seconds == 600
    assert result.review_status == "requires_review"


def test_all_break_session_has_no_percentage_and_needs_review():
    result = calculate_attendance(START, END, [connection(0, 60)], [(START, END)])
    assert result.connected_seconds == 0
    assert result.eligible_seconds == 0
    assert result.percentage is None
    assert result.review_status == "requires_review"


def test_outside_connections_do_not_contribute_time():
    result = calculate_attendance(START, END, [connection(-30, -10), connection(65, 70)])
    assert result.connected_seconds == 0
    assert result.percentage == 0


@pytest.mark.parametrize("connections", [[connection(20, 10)], [ConnectionInterval(START.replace(tzinfo=None), END)]])
def test_invalid_connection_input_is_rejected(connections):
    with pytest.raises(ValueError):
        calculate_attendance(START, END, connections)


def test_zero_length_session_is_not_applicable_and_needs_review():
    result = calculate_attendance(START, START, [])
    assert result.eligible_seconds == 0
    assert result.percentage is None
    assert result.review_status == "requires_review"


def test_negative_session_is_rejected():
    with pytest.raises(ValueError):
        calculate_attendance(END, START, [])


def test_dst_transition_uses_elapsed_seconds_not_wall_clock_difference():
    timezone = ZoneInfo("America/New_York")
    start = datetime(2026, 11, 1, 1, 30, tzinfo=timezone, fold=0)
    end = datetime(2026, 11, 1, 1, 30, tzinfo=timezone, fold=1)
    result = calculate_attendance(start, end, [ConnectionInterval(start, end)])
    assert result.eligible_seconds == 3600
    assert result.connected_seconds == 3600
    assert result.percentage == 100
