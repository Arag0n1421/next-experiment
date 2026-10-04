import datetime as dt
import unittest

import numpy as np

from science.screen import guide_enrichments, normalize_counts, resolve_gene, summarize_condition, summarize_context, run_tool


class ScientificInvariants(unittest.TestCase):
    def test_depth_normalization_removes_pure_library_scaling(self):
        guide_abundances = np.array([10., 20., 50., 100.])
        counts = guide_abundances[:, None] * np.array([1., 2., 5., 3., 8., 4.])
        norm, _, _ = normalize_counts(counts)
        effects, _ = guide_enrichments(norm, np.array([True, True, False, False]))
        np.testing.assert_allclose(effects, 0, atol=1e-12)

    def test_zero_library_and_invalid_counts_fail(self):
        for a in (np.zeros((3, 6)), np.full((3, 6), -1.), np.full((3, 6), np.nan)):
            with self.assertRaises(ValueError):
                normalize_counts(a)

    def test_non_target_controls_are_exact_labels(self):
        for gene in ("CTRL", "KNTC1", "NONO"):
            label, _ = resolve_gene(gene + "_+_123", gene)
            self.assertNotEqual(label, "non-targeting")
        self.assertEqual(resolve_gene("non-targeting_00001", "non-targeting")[0], "non-targeting")
        with self.assertRaises(ValueError):
            resolve_gene("CTRL_+_123", "non-targeting")

    def test_excel_date_symbol_recovery_has_source_bound_ledger(self):
        label, note = resolve_gene("MARCH1_+_123", dt.datetime(2024, 3, 1))
        self.assertEqual(label, "MARCH1")
        self.assertIn("Excel date", note["reason"])
        self.assertEqual(note["guide"], "MARCH1_+_123")
        self.assertEqual(resolve_gene("C4B_2_-_123", "C4B")[0], "C4B")

    def test_loo_identifies_real_estimator_reversal_and_no_single_guide_certainty(self):
        # Three guide means yield a positive median; omitting one can reverse it.
        result = summarize_condition(np.array([[-2., -2.], [1., 1.], [3., 3.]]), ["a", "b", "c"])
        self.assertTrue(result["leave_one_out"]["sign_reversal"])
        self.assertFalse(result["fixed_checklist_pass"])
        single = summarize_condition(np.array([[4., 4.]]), ["a"])
        self.assertEqual(single["leave_one_out"]["status"], "insufficient_guides")
        self.assertIsNone(single["leave_one_out"]["score_min"])
        self.assertFalse(single["fixed_checklist_pass"])

    def test_repeat_disagreement_prevents_checklist_pass(self):
        result = summarize_condition(np.array([[3., -1.], [4., -2.], [2., 0.]]), ["a", "b", "c"])
        self.assertFalse(result["repeat_sign_agreement"])
        self.assertFalse(result["fixed_checklist_pass"])

    def test_context_cancels_shared_baseline_before_gene_aggregation(self):
        effects = np.array([[2., 3., 5., 8.], [8., 9., 10., 10.], [-2., -1., 3., 4.]])
        shifted = effects + np.array([[30., 40., 30., 40.]])
        original = summarize_context(effects, ["a", "b", "c"])
        alternate = summarize_context(shifted, ["a", "b", "c"])
        self.assertAlmostEqual(original["score"], alternate["score"])
        np.testing.assert_allclose(original["repeat_scores"], alternate["repeat_scores"])

    def test_operation_allowlist_blocks_arbitrary_code(self):
        self.assertEqual(run_tool("exec rm -rf anything")["status"], "failed")


if __name__ == "__main__":
    unittest.main()
