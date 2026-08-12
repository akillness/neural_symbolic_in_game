import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from nesy_game import evaluate_trace


class MetricsTests(unittest.TestCase):
    def test_trace_metrics(self) -> None:
        metrics = evaluate_trace(
            committed=[True, True, False],
            hard_violations=[0, 1, 1],
            repair_successes=[True, False],
            target_tension=[0.0, 1.0],
            predicted_tension=[0.0, 0.5],
        )
        self.assertAlmostEqual(metrics["valid_commit_rate"], 0.5)
        self.assertAlmostEqual(metrics["hard_violations_per_candidate"], 2 / 3)
        self.assertAlmostEqual(metrics["repair_at_k"], 0.5)
        self.assertAlmostEqual(metrics["tension_mae"], 0.25)

    def test_mismatched_tension_curves_fail(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_trace([], [], [], [0.1], [])

    def test_mismatched_commit_vectors_fail(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_trace([True], [], [])

    def test_no_commits_is_not_perfect_validity(self) -> None:
        metrics = evaluate_trace([False], [1], [])
        self.assertEqual(metrics["valid_commit_rate"], 0.0)

    def test_negative_violations_fail(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_trace([True], [-1], [])


if __name__ == "__main__":
    unittest.main()
