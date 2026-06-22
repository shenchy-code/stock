import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import app as app_module


class StrategyApiTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.data_file = os.path.join(self.tempdir.name, "funds_data.json")
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump({
                "funds": ["000001"],
                "stocks": [],
                "positions": {},
                "last_update": None,
            }, f)

        self.original_data_file = app_module.DATA_FILE
        self.original_fetch_fund_info = app_module.fetch_fund_info
        app_module.DATA_FILE = self.data_file

        def fake_fetch_fund_info(code):
            return {
                "code": code,
                "name": "测试基金",
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

        app_module.fetch_fund_info = fake_fetch_fund_info
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.DATA_FILE = self.original_data_file
        app_module.fetch_fund_info = self.original_fetch_fund_info
        self.tempdir.cleanup()

    def test_post_strategy_positions_saves_position_inputs(self):
        response = self.client.post("/api/strategy/positions", json={
            "positions": {
                "000001": {
                    "buy_price": "1.0000",
                    "amount": "1000",
                }
            }
        })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["positions"]["000001"]["buy_price"], 1.0)
        self.assertEqual(payload["positions"]["000001"]["amount"], 1000.0)

        with open(self.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["positions"]["000001"]["amount"], 1000.0)

    def test_get_strategy_returns_report_using_saved_positions(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump({
                "funds": ["000001"],
                "stocks": [],
                "positions": {"000001": {"buy_price": 1.0, "amount": 1000}},
                "last_update": None,
            }, f)

        response = self.client.get("/api/strategy")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["overview"]["total_invested"], 1000)
        self.assertEqual(payload["overview"]["current_value"], 1180)
        self.assertEqual(payload["items"][0]["code"], "000001")
        self.assertEqual(payload["items"][0]["profit_amount"], 180)
        self.assertEqual(payload["items"][0]["price_source"], "official")
        self.assertEqual(payload["positions"]["000001"]["buy_price"], 1.0)

    def test_latest_official_nav_overrides_stale_jsonp_nav(self):
        response = Mock()
        response.json.return_value = {
            "Data": {
                "LSJZList": [
                    {
                        "FSRQ": "2026-05-21",
                        "DWJZ": "11.8958",
                        "JZZZL": "-4.44",
                    }
                ]
            }
        }

        with patch.object(app_module.http, "get", return_value=response):
            latest = app_module.fetch_latest_official_nav("014143")

        self.assertEqual(latest["nav"], "11.8958")
        self.assertEqual(latest["nav_date"], "2026-05-21")
        self.assertEqual(latest["day_growth"], "-4.44")


if __name__ == "__main__":
    unittest.main()
