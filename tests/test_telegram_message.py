#!/usr/bin/env python3
"""Test formattazione messaggio Telegram/WhatsApp."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper import (
    TELEGRAM_MAX_MESSAGE_LENGTH,
    format_telegram_message,
    format_rating_stars,
    group_consecutive_dates,
    film_merge_key,
    rating_to_stars,
)


def sample_multi_cinema_data():
    days_pic = {
        "2026-05-21": ["17:30", "21:30"],
        "2026-05-22": ["17:30", "19:30", "21:30"],
        "2026-05-23": ["17:30"],
        "2026-05-24": ["21:30"],
        "2026-05-25": ["17:30", "19:30"],
        "2026-05-26": ["17:30", "19:30"],
        "2026-05-27": ["17:30"],
    }
    days_rc = {
        "2026-05-24": ["16:30", "21:30"],
        "2026-05-25": ["17:30", "19:30"],
        "2026-05-26": ["17:30", "19:30"],
        "2026-05-27": ["16:30", "21:30"],
    }
    many_rc = {f"2026-05-{d:02d}": ["16:10", "16:30", "17:00", "18:00", "19:00", "20:00", "21:00", "21:40"] for d in range(21, 28)}

    def film(title, imdb, schedule, vo=False, cs_rating=None, tmdb_rating=None):
        progs = [{"data": d, "orari": t} for d, t in schedule.items()]
        f = {
            "titolo": title,
            "imdb_url": f"https://www.imdb.com/title/{imdb}/",
            "programmazione": progs,
        }
        if cs_rating is not None:
            f["voto_comingsoon"] = cs_rating
        if tmdb_rating is not None:
            f["voto_tmdb"] = tmdb_rating
        if vo:
            f["lingua_originale"] = True
            f["programmazione_vo"] = [{"data": "2026-05-21", "orari": ["18:20"]}]
            f["programmazione_non_vo"] = progs
        return f

    return {
        "timestamp": "2026-05-21T07:01:00",
        "cinema": [
            {
                "cinema": "Il Piccolo",
                "film": [film("Amarga Navidad", "tt28088049", days_pic)],
            },
            {
                "cinema": "UCI Cinemas Red Carpet",
                "film": [
                    film("Amarga Navidad", "tt28088049", days_rc),
                    film("The Mandalorian & Grogu", "tt30825738", many_rc, vo=True),
                    film("The Mandalorian and Grogu", "tt30825738", many_rc),
                ],
            },
        ],
    }


class TestRatingStars(unittest.TestCase):
    def test_rating_to_stars(self):
        self.assertEqual(rating_to_stars(4), "★★★★☆")
        self.assertEqual(rating_to_stars(3.5), "★★★½☆")
        self.assertEqual(rating_to_stars(5), "★★★★★")

    def test_format_rating_stars_both_sources(self):
        self.assertEqual(format_rating_stars(4.0, 7.2), "★★★★☆ ★★★½☆")


class TestTelegramHelpers(unittest.TestCase):
    def test_film_merge_key_imdb_unifies_title_variants(self):
        k1 = film_merge_key("The Mandalorian & Grogu", "https://www.imdb.com/title/tt30825738/")
        k2 = film_merge_key("The Mandalorian and Grogu", "https://www.imdb.com/title/tt30825738/")
        self.assertEqual(k1, k2)
        self.assertEqual(k1, "tt30825738")

    def test_group_consecutive_dates(self):
        date_times = {
            "2026-05-21": {"17:30", "21:30"},
            "2026-05-22": {"17:30", "21:30"},
            "2026-05-24": {"17:30"},
        }
        groups = group_consecutive_dates(date_times)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0][0], "2026-05-21")
        self.assertEqual(groups[0][1], "2026-05-22")
        self.assertEqual(groups[1][0], "2026-05-24")


class TestTelegramMessageFormat(unittest.TestCase):
    def setUp(self):
        self.data = sample_multi_cinema_data()
        self.msg = format_telegram_message(self.data)

    def test_message_within_telegram_limit(self):
        self.assertLessEqual(len(self.msg), TELEGRAM_MAX_MESSAGE_LENGTH)

    def test_full_cinema_names(self):
        self.assertIn("🎪 Cinema Piccolo", self.msg)
        self.assertIn("🎪 Red Carpet", self.msg)
        self.assertNotIn("🎪 RC\n", self.msg)
        self.assertNotIn("🎪 Pic\n", self.msg)

    def test_multi_cinema_layout(self):
        amarga = self.msg.index("Amarga Navidad")
        piccolo = self.msg.index("🎪 Cinema Piccolo", amarga)
        red = self.msg.index("🎪 Red Carpet", piccolo)
        self.assertLess(amarga, piccolo)
        self.assertLess(piccolo, red)

    def test_time_format_two_and_three_showings(self):
        self.assertIn("21 mag 17:30 21:30", self.msg)
        self.assertIn("22 mag 17:30-19:30-21:30", self.msg)

    def test_compact_format_from_four_showings(self):
        self.assertRegex(self.msg, r"\d+ spett\. \d{2}:\d{2}-\d{2}:\d{2}")

    def test_mandalorian_not_duplicated_three_times(self):
        self.assertEqual(self.msg.lower().count("mandalorian"), 2)  # VO + altri

    def test_short_imdb_links(self):
        self.assertIn("imdb.com/title/tt28088049", self.msg)
        self.assertNotIn("https://www.imdb.com", self.msg)

    def test_vo_section_present(self):
        self.assertIn("🌐 PROIEZIONI IN VERSIONE ORIGINALE:", self.msg)
        self.assertIn("🎞️ PROIEZIONI IN ITALIANO:", self.msg)
        self.assertIn("📽️🌐", self.msg)

    def test_message_headers(self):
        self.assertIn("🎬 MATERA - PROIEZIONI DEI PROSSIMI 7 GIORNI", self.msg)

    def test_ratings_in_message(self):
        data = sample_multi_cinema_data()
        data["cinema"][1]["film"][0]["voto_comingsoon"] = 4.0
        data["cinema"][1]["film"][0]["voto_tmdb"] = 8.0
        msg = format_telegram_message(data)
        self.assertIn("★★★★☆ ★★★★☆", msg)


class TestTelegramMessageFromCache(unittest.TestCase):
    def test_cached_json_if_present(self):
        cache = Path(__file__).resolve().parents[1] / "programmazione_cinema_matera.json"
        if not cache.exists():
            self.skipTest("programmazione_cinema_matera.json non presente")
        data = json.loads(cache.read_text(encoding="utf-8"))
        msg = format_telegram_message(data)
        self.assertLessEqual(len(msg), TELEGRAM_MAX_MESSAGE_LENGTH)
        self.assertTrue(
            msg.startswith("🎬 MATERA - PROIEZIONI DEI PROSSIMI 7 GIORNI")
            or msg.startswith("🎬 MATERA")
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
