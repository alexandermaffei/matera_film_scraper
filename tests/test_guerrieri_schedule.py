#!/usr/bin/env python3
"""Date Inizio/Fine Guerrieri: niente spettacoli dopo Fine, anche se Webtic li elenca."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guerrieri import (
    build_programmazione,
    parse_excluded_dates,
    parse_guerrieri_listing_html,
    parse_it_day_month,
    parse_showtimes,
    parse_unique_show_overrides,
    scrape_guerrieri_official,
)

FIXTURE = r"""
<script>
outputContainer.innerHTML = "    \n    <div class=\"lista-elementi-grid\">\n    <article id=\"post-2107\" class=\"movie-preview-container-elemento\"><h1 class=\"movie-main-title-elemento\">Sheep in the Box<\/h1><div class=\"available-dates-boxes\"><div class=\"date-box\"><div class=\"date-box-label-elemento\">Inizio<\/div><div class=\"date-box-value\">27 Ago<\/div><\/div><div class=\"date-box\"><div class=\"date-box-label-elemento\">Fine<\/div><div class=\"date-box-value\">01 Set<\/div><\/div><\/div><div class=\"orari\"><div class=\"info-label\">Info:<\/div><div class=\"info-value\">MARTEDI&#039; 1 SETTEMBRE UNICO SPETTACOLO ORE: 18.30<\/div></div><div class=\"orari\"><div class=\"info-label\">Orario:<\/div><div class=\"info-value\">18.30 - 21.00<\/div></div></article></div>\n    <div class=\"lista-elementi-grid\">\n    <article class=\"movie-preview-container-elemento\"><h1 class=\"movie-main-title-elemento\">Coutures<\/h1><div class=\"available-dates-boxes\"><div class=\"date-box\"><div class=\"date-box-label-elemento\">Inizio<\/div><div class=\"date-box-value\">04 Set<\/div><\/div><div class=\"date-box\"><div class=\"date-box-label-elemento\">Fine<\/div><div class=\"date-box-value\">08 Set<\/div><\/div></div><div class=\"available-dates-boxes\"><div class=\"date-box full-width\"><div class=\"date-box-label-elemento\">Date Escluse<\/div><div class=\"date-box-value non-available\">07 09<\/div></div></div><div class=\"orari\"><div class=\"info-label\">Orario:<\/div><div class=\"info-value\">17.30 - 19.15<\/div></div></article></div>\n    <article class=\"movie-preview-container-elemento\"><h1 class=\"movie-main-title-elemento\">The Echo Chamber<\/h1><div class=\"available-dates-boxes\"><div class=\"date-box full-width\"><div class=\"date-box-label-elemento\">Prossimamente in sala<\/div><div class=\"date-box-value\">Data da definire<\/div></div></div></article>";
contentRendered = true;
</script>
"""


class GuerrieriScheduleTests(unittest.TestCase):
    def test_parse_day_month(self):
        today = date(2026, 9, 1)
        self.assertEqual(parse_it_day_month("01 Set", today), date(2026, 9, 1))
        self.assertEqual(parse_it_day_month("27 Ago", today), date(2026, 8, 27))
        self.assertEqual(parse_it_day_month("07 09", today), date(2026, 9, 7))

    def test_showtimes_and_unique(self):
        self.assertEqual(parse_showtimes("18.30 - 21.00"), ["18:30", "21:00"])
        ov = parse_unique_show_overrides(
            "MARTEDI' 1 SETTEMBRE UNICO SPETTACOLO ORE: 18.30",
            today=date(2026, 9, 1),
        )
        self.assertEqual(ov, {"2026-09-01": ["18:30"]})

    def test_excluded(self):
        self.assertEqual(
            parse_excluded_dates("07 09", today=date(2026, 9, 1)),
            [date(2026, 9, 7)],
        )

    def test_listing_ignores_comingsoon_ghost_dates(self):
        today = date(2026, 9, 1)
        listings = parse_guerrieri_listing_html(FIXTURE, today=today)
        titles = [f["titolo"] for f in listings]
        self.assertEqual(titles, ["Sheep in the Box", "Coutures"])
        sheep = listings[0]
        self.assertEqual(sheep["end"], "2026-09-01")
        self.assertNotIn("2026-09-04", sheep["days"])
        self.assertIn("2026-09-01", sheep["days"])

        coutures = listings[1]
        self.assertIn("2026-09-04", coutures["days"])
        self.assertIn("2026-09-06", coutures["days"])
        self.assertNotIn("2026-09-07", coutures["days"])
        self.assertIn("2026-09-08", coutures["days"])

    def test_webtic_ghost_times_are_dropped(self):
        today = date(2026, 9, 1)
        allowed = [f"2026-09-0{d}" for d in range(1, 8)]
        webtic = [
            {
                "titolo": "Sheep In The Box",
                "programmazione": [
                    {"data": "2026-09-01", "orari": ["18:30"]},
                    {"data": "2026-09-04", "orari": ["21:00"]},
                    {"data": "2026-09-05", "orari": ["21:00"]},
                    {"data": "2026-09-06", "orari": ["21:00"]},
                ],
            }
        ]
        films = scrape_guerrieri_official(
            allowed,
            page_html=FIXTURE,
            webtic_films=webtic,
            today=today,
        )
        by_title = {f["titolo"]: f for f in films}
        sheep_days = {p["data"]: p["orari"] for p in by_title["Sheep in the Box"]["programmazione"]}
        self.assertEqual(sheep_days, {"2026-09-01": ["18:30"]})
        coutures_days = {p["data"] for p in by_title["Coutures"]["programmazione"]}
        self.assertEqual(coutures_days, {"2026-09-04", "2026-09-05", "2026-09-06"})


if __name__ == "__main__":
    unittest.main()
