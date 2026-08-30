import random
import unittest

from uniusa import export_joint_scores


class JointScoreExportFuzzTest(unittest.TestCase):
    def test_rounded_percentiles_form_a_distribution(self):
        rng = random.Random(314159)
        for _ in range(40):
            middle = sorted(rng.sample(range(1, 100), rng.randint(2, 15)))
            labels = ["1-", *(str(value) for value in middle), "99+"]
            scores = range(200, 200 + 10 * len(labels), 10)
            distribution = export_joint_scores.counts_from_labels(
                dict(zip(scores, labels)))
            self.assertAlmostEqual(sum(count for _, count in distribution), 100)
            self.assertTrue(all(count >= 0 for _, count in distribution))
