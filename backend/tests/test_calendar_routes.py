from datetime import datetime

from app.routes.calendar_routes import _parse_date_safe


def test_parse_date_safe_supports_utc_iso_timestamp():
    assert _parse_date_safe("2026-08-26T13:30:00Z") == datetime(2026, 8, 26, 13, 30)


def test_parse_date_safe_normalizes_timezone_offset_to_utc():
    assert _parse_date_safe("2026-08-26T18:30:00+05:00") == datetime(2026, 8, 26, 13, 30)
