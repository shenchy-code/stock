FUND_THEME_MAP = {
    "014143": {
        "theme": "科技成长",
        "sectors": ["半导体", "电子", "元件", "软件开发", "计算机"],
    },
    "014881": {
        "theme": "机器人",
        "sectors": ["机器人", "通用设备", "自动化设备", "机械设备"],
    },
    "002207": {
        "theme": "黄金贵金属",
        "sectors": ["贵金属", "黄金", "小金属", "工业金属"],
    },
    "013384": {
        "theme": "高端制造",
        "sectors": ["高端制造", "通用设备", "工业母机", "机械设备", "电子"],
    },
    "011120": {
        "theme": "创新科技",
        "sectors": ["软件开发", "计算机", "电子", "通信设备", "半导体"],
    },
    "018291": {
        "theme": "新兴成长",
        "sectors": ["电子", "通信设备", "半导体", "计算机", "元件"],
    },
    "010416": {
        "theme": "质量成长",
        "sectors": ["电子", "通信设备", "计算机", "电力设备", "机械设备"],
    },
    "021277": {
        "theme": "全球成长",
        "sectors": ["电子", "计算机", "通信设备", "软件开发"],
    },
    "020900": {
        "theme": "通信设备",
        "sectors": ["通信设备", "通信", "通信网络设备及器件", "电子", "元件"],
    },
    "002112": {
        "theme": "价值成长",
        "sectors": ["电子", "通信设备", "计算机", "电力设备", "基础化工"],
    },
    "018957": {
        "theme": "成长机会",
        "sectors": ["电子", "半导体", "通信设备", "计算机", "元件"],
    },
    "013841": {
        "theme": "集成电路",
        "sectors": ["半导体", "集成电路封测", "半导体设备", "半导体材料", "数字芯片设计"],
    },
    "016371": {
        "theme": "业绩驱动成长",
        "sectors": ["电子", "通信设备", "计算机", "电力设备", "机械设备"],
    },
    "006503": {
        "theme": "集成电路",
        "sectors": ["半导体", "集成电路封测", "半导体设备", "半导体材料", "数字芯片设计"],
    },
    "019830": {
        "theme": "数字产业",
        "sectors": ["软件开发", "计算机", "互联网服务", "电子", "通信设备"],
    },
}

PERIOD_WEIGHTS = {
    "today": 0.5,
    "5d": 0.3,
    "10d": 0.2,
}


def _norm(value):
    return str(value or "").strip().lower()


def _matches_sector(theme_sector, flow_name):
    theme_sector = _norm(theme_sector)
    flow_name = _norm(flow_name)
    return theme_sector and flow_name and (theme_sector in flow_name or flow_name in theme_sector)


def score_theme_from_flows(sectors, flow_data):
    matched = []
    score = 50

    for period, weight in PERIOD_WEIGHTS.items():
        period_data = flow_data.get(period, {})
        for direction, direction_score in (("in", 1), ("out", -1)):
            for rank, sector in enumerate(period_data.get(direction, []), 1):
                name = sector.get("name", "")
                if not any(_matches_sector(theme_sector, name) for theme_sector in sectors):
                    continue

                flow = abs(float(sector.get("flow") or 0))
                change = float(sector.get("change") or 0)
                rank_power = max(0.25, (21 - rank) / 20)
                flow_power = min(flow / 30, 2)
                impact = direction_score * weight * rank_power * (6 + flow_power * 4)
                if direction == "in" and change > 3:
                    impact += weight * 2
                elif direction == "out" and change < -2:
                    impact -= weight * 2

                score += impact
                matched.append({
                    "period": period,
                    "direction": direction,
                    "name": name,
                    "flow": sector.get("flow"),
                    "change": sector.get("change"),
                    "impact": round(impact, 2),
                })

    score = round(max(0, min(100, score)), 1)
    if score >= 65:
        status = "强"
    elif score >= 55:
        status = "偏强"
    elif score >= 45:
        status = "中性"
    elif score >= 35:
        status = "偏弱"
    else:
        status = "弱"

    return {
        "score": score,
        "status": status,
        "matches": matched[:8],
    }


def build_theme_signals(fund_codes, flow_data):
    signals = {}
    for code in fund_codes:
        config = FUND_THEME_MAP.get(code, {
            "theme": "未分类",
            "sectors": [],
        })
        signal = score_theme_from_flows(config["sectors"], flow_data)
        signals[code] = {
            "theme": config["theme"],
            "sectors": config["sectors"],
            **signal,
        }
    return signals
