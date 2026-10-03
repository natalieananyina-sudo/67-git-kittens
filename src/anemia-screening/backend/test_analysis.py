import unittest

from screening.analysis import analyze


class AnalysisTests(unittest.TestCase):
    def test_hemoglobin_threshold_and_missing_markers(self):
        result = analyze({"sex": "F", "age_years": 35, "hemoglobin": 119})
        self.assertTrue(result["anemia"])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["classCode"])
        self.assertFalse(analyze({"sex": "M", "age_years": 35, "hemoglobin": 130})["anemia"])

    def test_model_inference_with_sparse_features(self):
        result = analyze({"sex": "M", "age_years": "40", "hemoglobin": "140",
                          "ferritin": "30", "CRP": "2"})
        self.assertEqual(result["status"], "predicted")
        self.assertEqual(result["classCode"], "no_anemia_no_deficiency")
        self.assertEqual(result["measuredMarkers"], ["ferritin", "CRP"])

    def test_reject_invalid_number(self):
        with self.assertRaisesRegex(ValueError, "ferritin"):
            analyze({"sex": "M", "age_years": 40, "hemoglobin": 140,
                     "ferritin": "n/a", "CRP": 2})


if __name__ == "__main__":
    unittest.main()
