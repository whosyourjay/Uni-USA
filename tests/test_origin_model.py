#!/usr/bin/env python3
"""Fuzz checks for predicting origin ability from national institution features."""

import random
import unittest

from uniusa import origin_model, pathways


LEVELS = (1, 2, 3)


def random_features(rng):
    return {
        "completion_rate": rng.random(),
        "transfer_out_rate": rng.random(),
        "full_time_share": rng.random(),
        "log_undergraduates": rng.uniform(0, 12),
        "open_admission": float(rng.random() < 0.5),
        "is_public": float(rng.random() < 0.5),
        "level": rng.choice(LEVELS),
    }


def random_origins(rng, count=None):
    """Origins with a score on roughly two thirds of them, and their features."""
    rows, table = [], {}
    for origin_id in range(count or rng.randint(30, 200)):
        table[origin_id] = random_features(rng)
        scored = rng.random() < 0.66
        rows.append({
            "origin_id": origin_id,
            "origin_type": (
                origin_model.FOUR_YEAR
                if table[origin_id]["level"] == origin_model.FOUR_YEAR_LEVEL
                else "two-year"
            ),
            "freshman_score": round(rng.uniform(5, 99), 3) if scored else "",
            "transfer_out_domestic": float(rng.randint(1, 4000)),
        })
    return rows, table


def four_year_rows(rows, table):
    return [
        row for row in rows
        if table[row["origin_id"]]["level"] == origin_model.FOUR_YEAR_LEVEL
    ]


class OriginModelTests(unittest.TestCase):
    def test_predictions_stay_on_the_percentile_scale(self):
        """A percentile cannot leave 0-100 however extreme the features are."""
        rng = random.Random(20260822)
        for _ in range(200):
            rows, table = random_origins(rng)
            if len(four_year_rows(rows, table)) < len(origin_model.FEATURE_COLUMNS) + 2:
                continue
            predictions, _ = origin_model.predicted_scores(rows, table)
            low, high = origin_model.SCORE_RANGE
            for score in predictions.values():
                self.assertGreaterEqual(score, low)
                self.assertLessEqual(score, high)

    def test_every_featured_origin_gets_a_prediction(self):
        """Nothing with features falls back to the institution-type median."""
        rng = random.Random(7)
        for _ in range(200):
            rows, table = random_origins(rng)
            if len(four_year_rows(rows, table)) < len(origin_model.FEATURE_COLUMNS) + 2:
                continue
            predictions, _ = origin_model.predicted_scores(rows, table)
            self.assertEqual(set(predictions), set(table))

    def test_the_anchored_level_lands_on_its_scored_median(self):
        """Borrowing only the ordering means the scored peers set the level."""
        rng = random.Random(11)
        for _ in range(200):
            rows, table = random_origins(rng, count=rng.randint(80, 200))
            for row in rows:
                if table[row["origin_id"]]["level"] == 3:
                    table[row["origin_id"]]["level"] = 2
            scored = [
                row for row in rows
                if row["freshman_score"] != "" and table[row["origin_id"]]["level"] == 2
            ]
            if (len(four_year_rows(rows, table)) < len(origin_model.FEATURE_COLUMNS) + 2
                    or len(scored) < origin_model.MINIMUM_ANCHOR_ORIGINS):
                continue
            predictions, _ = origin_model.predicted_scores(rows, table)
            weight = lambda row: row["transfer_out_domestic"]
            observed = pathways.weighted_median(
                scored, weight, lambda row: row["freshman_score"]
            )
            predicted = pathways.weighted_median(
                scored, weight, lambda row: predictions[row["origin_id"]]
            )
            low, high = origin_model.SCORE_RANGE
            if low < predicted < high:
                self.assertAlmostEqual(observed, predicted, 3)


if __name__ == "__main__":
    unittest.main()
