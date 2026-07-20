from __future__ import annotations

import unittest

from app.evaluate_archive import evaluate_all
from app.evaluation_gold import MODERATION_GOLD_CASES, PRIVACY_GOLD_CASES, RETRIEVAL_GOLD_CASES


class EvaluationHarnessTests(unittest.TestCase):
    def test_gold_dataset_size_is_regression_scale(self) -> None:
        total_rows = len(MODERATION_GOLD_CASES) + len(PRIVACY_GOLD_CASES) + len(RETRIEVAL_GOLD_CASES)
        self.assertGreaterEqual(total_rows, 100)
        self.assertLessEqual(total_rows, 300)

    def test_evaluation_report_meets_guardrail_thresholds(self) -> None:
        report = evaluate_all()

        self.assertGreaterEqual(report.moderation.global_metrics.f1, 0.8)

        for pii_type, metrics in report.privacy.by_type.items():
            with self.subTest(pii_type=pii_type):
                self.assertLessEqual(metrics.false_negative_rate, 0.35)
                self.assertLessEqual(metrics.false_positive_rate, 0.35)
                self.assertGreaterEqual(metrics.span_boundary_accuracy, 0.65)

        self.assertGreaterEqual(report.retrieval.candidate.recall_at_5, 0.65)
        self.assertGreaterEqual(report.retrieval.candidate.recall_at_10, 0.75)
        self.assertGreaterEqual(report.retrieval.candidate.mrr, 0.7)
        self.assertGreaterEqual(report.retrieval.candidate.ndcg, 0.65)


if __name__ == "__main__":
    unittest.main()
