from datetime import date
from unittest.mock import MagicMock

import pytest

from bandsintown_scraper import scraper
from bandsintown_scraper.scraper import (
    ScrapingError,
    _scrap_days,
    list_page_files,
    scrap_multiple_pages,
    scrap_one_page,
)

DAY = date(2026, 10, 31)


@pytest.fixture(autouse=True)
def sleep_mock(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(scraper.time, "sleep", mock)
    return mock


def fake_pages(monkeypatch, pages):
    """Remplace l'API : renvoie les pages données dans l'ordre, puis des pages vides."""
    def fake_scrap_one_page(page_idx, day, session):
        return [{"id": event_id} for event_id in pages[page_idx - 1]] if page_idx <= len(pages) else []

    monkeypatch.setattr(scraper, "scrap_one_page", fake_scrap_one_page)


def test_scrap_one_page_asks_for_the_whole_day():
    session = MagicMock()
    session.get.return_value = MagicMock(status_code=200, json=lambda: [{"id": 1}])

    assert scrap_one_page(1, DAY, session) == [{"id": 1}]
    assert session.get.call_args.kwargs["params"]["date"] == "2026-10-31T00:00:00,2026-10-31T23:59:59"


def test_scrap_one_page_raises_when_site_refuses():
    session = MagicMock()
    session.get.return_value = MagicMock(status_code=403, text="blocked")

    with pytest.raises(ScrapingError):
        scrap_one_page(1, DAY, session)


def test_empty_page_ends_the_day(monkeypatch, tmp_path, sleep_mock):
    fake_pages(monkeypatch, [[1, 2]])

    new_events, page_limit_reached, nb_pages = scrap_multiple_pages(DAY, 30, set(), tmp_path, None)

    assert [event["id"] for event in new_events] == [1, 2]
    assert not page_limit_reached
    assert nb_pages == 2
    assert sleep_mock.call_count == 2


def test_repeated_page_means_api_limit(monkeypatch, tmp_path):
    fake_pages(monkeypatch, [[1, 2], [3, 4], [1, 2]])

    new_events, page_limit_reached, nb_pages = scrap_multiple_pages(DAY, 30, set(), tmp_path, None)

    assert len(new_events) == 4
    assert page_limit_reached
    assert nb_pages == 3


def test_events_seen_on_previous_day_do_not_stop_the_day(monkeypatch, tmp_path):
    fake_pages(monkeypatch, [[1, 2], [3]])

    new_events, page_limit_reached, _ = scrap_multiple_pages(DAY, 30, {1, 2}, tmp_path, None)

    assert [event["id"] for event in new_events] == [3]
    assert not page_limit_reached


def test_max_page_means_api_limit(monkeypatch, tmp_path):
    fake_pages(monkeypatch, [[1], [2], [3]])

    new_events, page_limit_reached, nb_pages = scrap_multiple_pages(DAY, 2, set(), tmp_path, None)

    assert len(new_events) == 2
    assert page_limit_reached
    assert nb_pages == 2


def test_every_day_is_collected_even_after_an_empty_one(monkeypatch, tmp_path):
    events_by_day = {date(2026, 11, 1): [{"id": 1}], date(2026, 11, 3): [{"id": 2}]}
    requested_days = []

    def fake_scrap_one_page(page_idx, day, session):
        requested_days.append(day)
        return events_by_day.get(day, []) if page_idx == 1 else []

    monkeypatch.setattr(scraper, "scrap_one_page", fake_scrap_one_page)

    _scrap_days(date(2026, 11, 1), date(2026, 11, 3), tmp_path, None)

    assert sorted(set(requested_days)) == [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3)]
    assert len(list_page_files(tmp_path)) == 2
