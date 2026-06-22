import unittest

from theme_service import build_theme_signals, score_theme_from_flows


class ThemeServiceTest(unittest.TestCase):
    def test_theme_score_rewards_sustained_inflows_and_penalizes_outflows(self):
        sectors = ["半导体", "电子"]
        flow_data = {
            "today": {
                "in": [{"name": "电子", "flow": 20, "change": 2}],
                "out": [{"name": "半导体", "flow": 50, "change": -1}],
            },
            "5d": {
                "in": [{"name": "半导体设备", "flow": 30, "change": 4}],
                "out": [],
            },
            "10d": {
                "in": [{"name": "电子", "flow": 15, "change": 3}],
                "out": [],
            },
        }

        signal = score_theme_from_flows(sectors, flow_data)

        self.assertGreater(signal["score"], 45)
        self.assertLess(signal["score"], 65)
        self.assertIn(signal["status"], ["中性", "偏强"])
        self.assertTrue(any(match["direction"] == "out" for match in signal["matches"]))
        self.assertTrue(any(match["direction"] == "in" for match in signal["matches"]))

    def test_build_theme_signals_maps_known_fund_to_theme(self):
        signals = build_theme_signals(["014143"], {
            "today": {
                "in": [{"name": "电子", "flow": 30, "change": 2}],
                "out": [],
            },
            "5d": {"in": [], "out": []},
            "10d": {"in": [], "out": []},
        })

        self.assertEqual(signals["014143"]["theme"], "科技成长")
        self.assertGreater(signals["014143"]["score"], 50)
        self.assertEqual(signals["014143"]["status"], "偏强")


if __name__ == "__main__":
    unittest.main()
