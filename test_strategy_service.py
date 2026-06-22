import unittest

from strategy_service import build_strategy_report


class StrategyServiceTest(unittest.TestCase):
    def test_strong_fund_gets_buy_action_and_weak_fund_gets_sell_action(self):
        funds = [
            {
                "code": "000001",
                "name": "强势基金",
                "success": True,
                "estimate_nav": "1.2000",
                "nav": "1.1800",
                "estimate_change": "0.80",
                "week_growth": "2.50",
                "month_growth": "6.00",
                "three_month_growth": "15.00",
                "six_month_growth": "22.00",
                "year_growth": "35.00",
            },
            {
                "code": "000002",
                "name": "弱势基金",
                "success": True,
                "estimate_nav": "0.8000",
                "nav": "0.8200",
                "estimate_change": "-1.20",
                "week_growth": "-3.00",
                "month_growth": "-8.00",
                "three_month_growth": "-12.00",
                "six_month_growth": "-20.00",
                "year_growth": "-25.00",
            },
        ]
        positions = {
            "000001": {"buy_price": 1.0, "amount": 100},
            "000002": {"buy_price": 1.0, "amount": 1900},
        }

        report = build_strategy_report(funds, positions)
        by_code = {item["code"]: item for item in report["items"]}

        self.assertEqual(by_code["000001"]["action"], "buy")
        self.assertEqual(by_code["000002"]["action"], "sell")
        self.assertGreater(by_code["000001"]["target_weight"], 90)
        self.assertEqual(by_code["000001"]["profit_amount"], 18)
        self.assertEqual(by_code["000002"]["profit_amount"], -342)
        self.assertGreater(by_code["000001"]["rebalance_amount"], 700)
        self.assertLess(by_code["000002"]["rebalance_amount"], -700)
        self.assertEqual(report["overview"]["total_invested"], 2000)
        self.assertEqual(report["overview"]["current_value"], 1676)
        self.assertEqual(report["overview"]["profit_amount"], -324)
        self.assertEqual(report["overview"]["action_counts"]["buy"], 1)
        self.assertEqual(report["overview"]["action_counts"]["sell"], 1)

    def test_missing_position_is_marked_as_input_without_blocking_score(self):
        funds = [
            {
                "code": "000001",
                "name": "强势基金",
                "success": True,
                "estimate_nav": "1.2000",
                "nav": "1.1800",
                "estimate_change": "0.80",
                "week_growth": "2.50",
                "month_growth": "6.00",
                "three_month_growth": "15.00",
                "six_month_growth": "22.00",
                "year_growth": "35.00",
            }
        ]

        report = build_strategy_report(funds, {})
        item = report["items"][0]

        self.assertEqual(item["action"], "input")
        self.assertTrue(item["needs_position"])
        self.assertEqual(item["position_status"], "watch")
        self.assertGreater(item["score"], 70)
        self.assertEqual(report["overview"]["missing_positions"], 0)
        self.assertEqual(report["overview"]["watch_count"], 1)
        self.assertIn("base", report["overview"]["scenario"])

    def test_strategy_uses_official_nav_before_estimated_nav(self):
        funds = [
            {
                "code": "014143",
                "name": "银河创新成长混合C",
                "success": True,
                "nav": "11.8958",
                "nav_date": "2026-05-21",
                "estimate_nav": "12.1618",
                "estimate_time": "2026-05-21 15:00",
                "estimate_change": "-2.30",
                "month_growth": "30.21",
                "three_month_growth": "24.65",
                "six_month_growth": "48.90",
                "year_growth": "87.78",
            }
        ]
        positions = {
            "014143": {
                "buy_price": 10,
                "amount": 1000,
            }
        }

        report = build_strategy_report(funds, positions)
        item = report["items"][0]

        self.assertEqual(item["current_price"], 11.8958)
        self.assertEqual(item["price_source"], "official")
        self.assertEqual(item["price_date"], "2026-05-21")
        self.assertEqual(item["estimated_price"], 12.1618)
        self.assertEqual(item["current_value"], 1189.58)
        self.assertEqual(item["profit_amount"], 189.58)

    def test_concentrated_strong_holding_is_reduce_action(self):
        funds = [
            {
                "code": "000001",
                "name": "已重仓强势基金",
                "success": True,
                "nav": "1.1000",
                "estimate_change": "0.50",
                "month_growth": "8.00",
                "three_month_growth": "18.00",
                "six_month_growth": "30.00",
                "year_growth": "45.00",
            },
            {
                "code": "000002",
                "name": "候选强势基金A",
                "success": True,
                "nav": "1.0000",
                "estimate_change": "0.20",
                "month_growth": "7.00",
                "three_month_growth": "16.00",
                "six_month_growth": "28.00",
                "year_growth": "42.00",
            },
            {
                "code": "000003",
                "name": "候选强势基金B",
                "success": True,
                "nav": "1.0000",
                "estimate_change": "0.10",
                "month_growth": "6.00",
                "three_month_growth": "15.00",
                "six_month_growth": "25.00",
                "year_growth": "40.00",
            },
            {
                "code": "000004",
                "name": "候选强势基金C",
                "success": True,
                "nav": "1.0000",
                "estimate_change": "0.10",
                "month_growth": "5.00",
                "three_month_growth": "14.00",
                "six_month_growth": "24.00",
                "year_growth": "35.00",
            },
        ]
        positions = {
            "000001": {
                "buy_price": 1.0,
                "amount": 10000,
            }
        }

        report = build_strategy_report(funds, positions)
        held = next(item for item in report["items"] if item["code"] == "000001")

        self.assertEqual(held["action"], "hold")
        self.assertEqual(held["decision"], "hold_with_risk")
        self.assertGreaterEqual(held["current_weight"], 99)
        self.assertEqual(held["target_weight"], 100)
        self.assertIn("集中", held["decision_reason"])
        self.assertEqual(report["overview"]["recommendation"]["stance"], "控制集中度")
        self.assertGreaterEqual(len(report["overview"]["next_actions"]), 3)
        self.assertEqual(report["overview"]["next_actions"][0]["type"], "hold_with_risk")

    def test_missing_strong_fund_is_ranked_as_candidate_opportunity(self):
        funds = [
            {
                "code": "000001",
                "name": "已持有基金",
                "success": True,
                "nav": "1.0000",
                "estimate_change": "0.10",
                "month_growth": "1.00",
                "three_month_growth": "2.00",
                "six_month_growth": "3.00",
                "year_growth": "5.00",
            },
            {
                "code": "000002",
                "name": "未持有强势基金",
                "success": True,
                "nav": "1.0000",
                "estimate_change": "0.30",
                "month_growth": "8.00",
                "three_month_growth": "18.00",
                "six_month_growth": "30.00",
                "year_growth": "50.00",
            },
        ]
        positions = {
            "000001": {
                "buy_price": 1.0,
                "amount": 5000,
            }
        }

        report = build_strategy_report(funds, positions)
        candidate = next(item for item in report["items"] if item["code"] == "000002")
        candidate_actions = [
            action for action in report["overview"]["next_actions"]
            if action["type"] == "watch_candidate"
        ]

        self.assertEqual(candidate["action"], "input")
        self.assertEqual(candidate["decision"], "watch_candidate")
        self.assertIn("候选", candidate["decision_text"])
        self.assertTrue(candidate_actions)
        self.assertEqual(candidate_actions[0]["code"], "000002")

    def test_unowned_watchlist_does_not_make_holding_unexecutable(self):
        funds = [
            {
                "code": "014143",
                "name": "已持有强势基金",
                "success": True,
                "nav": "11.8958",
                "estimate_nav": "12.1618",
                "estimate_change": "-2.30",
                "month_growth": "30.21",
                "three_month_growth": "24.65",
                "six_month_growth": "48.90",
                "year_growth": "87.78",
            },
            {
                "code": "018291",
                "name": "观察池强势基金",
                "success": True,
                "nav": "1.0000",
                "estimate_change": "0.30",
                "month_growth": "8.00",
                "three_month_growth": "18.00",
                "six_month_growth": "30.00",
                "year_growth": "50.00",
            },
        ]
        positions = {
            "014143": {
                "buy_price": 11.6693,
                "amount": 20000,
            }
        }

        report = build_strategy_report(funds, positions)
        held = next(item for item in report["items"] if item["code"] == "014143")
        watch = next(item for item in report["items"] if item["code"] == "018291")

        self.assertEqual(report["overview"]["held_count"], 1)
        self.assertEqual(report["overview"]["watch_count"], 1)
        self.assertEqual(report["overview"]["missing_positions"], 0)
        self.assertTrue(report["overview"]["recommendation"]["can_execute"])
        self.assertEqual(held["position_status"], "held")
        self.assertEqual(watch["position_status"], "watch")
        self.assertEqual(watch["decision"], "watch_candidate")
        self.assertNotIn("缺少买入价", " ".join(report["overview"]["recommendation"]["warnings"]))

    def test_weak_theme_prevents_blind_add_even_when_fund_trend_is_strong(self):
        funds = [
            {
                "code": "014143",
                "name": "趋势强但板块弱",
                "success": True,
                "nav": "1.1000",
                "estimate_change": "0.50",
                "month_growth": "10.00",
                "three_month_growth": "20.00",
                "six_month_growth": "35.00",
                "year_growth": "60.00",
            }
        ]
        positions = {
            "014143": {
                "buy_price": 1.0,
                "amount": 10000,
            }
        }
        theme_signals = {
            "014143": {
                "theme": "科技成长",
                "score": 32,
                "status": "弱",
                "matches": [
                    {"name": "半导体", "direction": "out", "period": "today", "flow": 50}
                ],
            }
        }

        report = build_strategy_report(funds, positions, theme_signals)
        item = report["items"][0]

        self.assertEqual(item["theme"]["status"], "弱")
        self.assertLess(item["score"], 100)
        self.assertIn(item["decision"], ["hold_with_risk", "reduce", "sell", "hold"])
        self.assertNotEqual(item["decision"], "add")
        self.assertIn("板块", item["decision_reason"])


if __name__ == "__main__":
    unittest.main()
