#!/usr/bin/env python3
"""Test matching TMDB (normalizzazione e score, senza rete)."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tmdb_enrich import (
    jaccard,
    normalize_film_title,
    recency_score,
    score_candidate,
    title_similarity,
)


class TestTitleNormalize(unittest.TestCase):
    def test_strips_articles_and_punct(self):
        self.assertEqual(normalize_film_title("Il Diavolo Veste Prada 2"), "diavolo veste prada 2")
        self.assertEqual(normalize_film_title("The Devil Wears Prada 2"), "devil wears prada 2")

    def test_spider_man_colon(self):
        a = normalize_film_title("Spider-Man: Brand New Day")
        b = normalize_film_title("Spider Man Brand New Day")
        self.assertEqual(a, b)


class TestSimilarity(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(title_similarity("Odissea", "Odissea", "The Odyssey"), 1.0)

    def test_original_title_match(self):
        self.assertGreater(
            title_similarity("The Odyssey", "Odissea", "The Odyssey"),
            0.9,
        )

    def test_jaccard_partial(self):
        self.assertGreater(jaccard("Robin Hood Il Prezzo del Sangue", "Robin Hood"), 0.3)


class TestRecency(unittest.TestCase):
    def test_current_release_high(self):
        now = datetime(2026, 8, 17, tzinfo=timezone.utc)
        self.assertEqual(recency_score("2026-07-15", now), 1.0)

    def test_old_film_low(self):
        now = datetime(2026, 8, 17, tzinfo=timezone.utc)
        self.assertLess(recency_score("1976-01-01", now), 0.2)

    def test_prefers_new_over_old_same_title(self):
        now = datetime(2026, 8, 17, tzinfo=timezone.utc)
        query = "Obsession"
        new = {"title": "Obsession", "original_title": "Obsession", "release_date": "2026-03-01", "popularity": 20}
        old = {"title": "Obsession", "original_title": "Obsession", "release_date": "1976-01-01", "popularity": 8}
        self.assertGreater(score_candidate(query, new, now), score_candidate(query, old, now))


if __name__ == "__main__":
    unittest.main()
