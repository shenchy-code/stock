from collections import Counter


ACTION_LABELS = {
    "buy": "买入/加仓",
    "hold": "持有",
    "reduce": "减仓",
    "sell": "卖出",
    "input": "补充持仓",
}

DECISION_LABELS = {
    "add": "建议加仓",
    "hold": "继续持有",
    "hold_with_risk": "持有控仓",
    "reduce": "建议减仓",
    "sell": "建议卖出",
    "reduce_concentration": "降低集中度",
    "candidate_buy": "候选买入",
    "watch_candidate": "观察候选",
    "candidate_watch": "观察等待",
    "avoid": "暂不参与",
    "input_required": "补充持仓",
}

MAX_SINGLE_WEIGHT = 20
CONCENTRATION_WARNING_WEIGHT = 40
REBALANCE_BAND = 5


def parse_float(value):
    if value in (None, "", "--"):
        return None
    try:
        if isinstance(value, str):
            value = value.strip().replace("%", "").replace(",", "")
            if value in ("", "--"):
                return None
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def round_money(value):
    return round(value or 0, 2)


def current_price_for(fund):
    return parse_float(fund.get("nav")) or parse_float(fund.get("estimate_nav"))


def price_context_for(fund):
    official_price = parse_float(fund.get("nav"))
    estimated_price = parse_float(fund.get("estimate_nav"))
    if official_price is not None:
        return {
            "current_price": official_price,
            "price_source": "official",
            "price_source_text": "正式净值",
            "price_date": fund.get("nav_date") or "--",
            "estimated_price": estimated_price,
            "estimate_time": fund.get("estimate_time") or "--",
        }
    return {
        "current_price": estimated_price,
        "price_source": "estimated" if estimated_price is not None else "missing",
        "price_source_text": "估算净值" if estimated_price is not None else "无净值",
        "price_date": fund.get("estimate_time") or "--",
        "estimated_price": estimated_price,
        "estimate_time": fund.get("estimate_time") or "--",
    }


def score_fund(fund, theme_signal=None):
    if not fund.get("success"):
        return 0, ["数据获取失败"]

    score = 50
    reasons = []

    estimate_change = parse_float(fund.get("estimate_change"))
    if estimate_change is not None:
        if estimate_change > 1:
            score += 4
            reasons.append("当日估值偏强")
        elif estimate_change > 0:
            score += 2
            reasons.append("当日估值小幅上涨")
        elif estimate_change < -3:
            score -= 6
            reasons.append("当日估值大跌")
        elif estimate_change < 0:
            score -= 2
            reasons.append("当日估值回落")

    week = parse_float(fund.get("week_growth"))
    if week is not None:
        if week >= 2:
            score += 8
            reasons.append("近1周强势")
        elif week >= 0:
            score += 4
            reasons.append("近1周为正")
        elif week <= -2:
            score -= 8
            reasons.append("近1周走弱")
        else:
            score -= 4
            reasons.append("近1周为负")

    month = parse_float(fund.get("month_growth"))
    if month is not None:
        if month >= 5:
            score += 12
            reasons.append("近1月强势")
        elif month >= 2:
            score += 8
            reasons.append("近1月改善")
        elif month <= -5:
            score -= 12
            reasons.append("近1月明显走弱")
        elif month <= -2:
            score -= 8
            reasons.append("近1月偏弱")

    three_month = parse_float(fund.get("three_month_growth"))
    if three_month is not None:
        if three_month >= 10:
            score += 14
            reasons.append("近3月趋势强")
        elif three_month >= 4:
            score += 8
            reasons.append("近3月趋势向上")
        elif three_month <= -10:
            score -= 14
            reasons.append("近3月趋势弱")
        elif three_month <= -4:
            score -= 8
            reasons.append("近3月承压")

    six_month = parse_float(fund.get("six_month_growth"))
    if six_month is not None:
        if six_month >= 15:
            score += 10
            reasons.append("近6月延续强势")
        elif six_month >= 5:
            score += 5
            reasons.append("近6月为正")
        elif six_month <= -15:
            score -= 10
            reasons.append("近6月明显走弱")
        elif six_month <= -5:
            score -= 5
            reasons.append("近6月偏弱")

    year = parse_float(fund.get("year_growth"))
    if year is not None:
        if year >= 20:
            score += 10
            reasons.append("近1年表现优秀")
        elif year >= 5:
            score += 5
            reasons.append("近1年为正")
        elif year <= -20:
            score -= 10
            reasons.append("近1年大幅落后")
        elif year <= -5:
            score -= 5
            reasons.append("近1年为负")

    if theme_signal:
        theme_score = parse_float(theme_signal.get("score"))
        theme_status = theme_signal.get("status", "--")
        if theme_score is not None:
            if theme_score >= 65:
                score += 8
                reasons.append(f"板块资金{theme_status}")
            elif theme_score >= 55:
                score += 4
                reasons.append(f"板块资金{theme_status}")
            elif theme_score <= 35:
                score -= 12
                reasons.append(f"板块资金{theme_status}")
            elif theme_score <= 45:
                score -= 6
                reasons.append(f"板块资金{theme_status}")

    score = int(round(clamp(score, 0, 100)))
    if not reasons:
        reasons.append("可用趋势数据不足")
    return score, reasons


def valid_position(raw):
    if not isinstance(raw, dict):
        return None
    buy_price = parse_float(raw.get("buy_price"))
    amount = parse_float(raw.get("amount"))
    if buy_price is None or buy_price <= 0 or amount is None or amount <= 0:
        return None
    return {"buy_price": buy_price, "amount": amount}


def monthly_expectation(fund):
    month = parse_float(fund.get("month_growth"))
    three_month = parse_float(fund.get("three_month_growth"))
    if month is None and three_month is None:
        return 0
    if month is None:
        trend = three_month / 3
    elif three_month is None:
        trend = month
    else:
        trend = month * 0.6 + (three_month / 3) * 0.4
    return clamp(trend * 0.5, -6, 8)


def classify_decision(item, total_current_value, rebalance_threshold):
    score = item["score"]
    theme_signal = item.get("theme") or {}
    theme_score = parse_float(theme_signal.get("score"))
    theme_weak = theme_score is not None and theme_score < 45
    current_weight = item["current_value"] / total_current_value * 100 if total_current_value else 0
    target_weight = item["target_weight"]
    target_value = total_current_value * target_weight / 100 if total_current_value else 0
    rebalance_amount = target_value - item["current_value"]

    if item["needs_position"]:
        if score >= 80 and not theme_weak:
            return "input", "watch_candidate", "观察池强势候选；如准备买入，再录入计划金额后测算仓位"
        if score >= 60:
            return "input", "candidate_watch", "走势尚可，先观察并补录持仓数据"
        return "input", "avoid", "评分偏弱，暂不作为买入候选"

    if score < 30:
        return "sell", "sell", "趋势评分低，优先退出弱势标的"
    if theme_weak and score >= 70:
        return "hold", "hold_with_risk", "基金趋势仍强，但对应板块资金偏弱，不建议继续加仓"
    if current_weight >= CONCENTRATION_WARNING_WEIGHT:
        if current_weight > target_weight + REBALANCE_BAND:
            return "reduce", "reduce_concentration", f"当前仓位{current_weight:.2f}%过于集中，超过单只风控阈值{CONCENTRATION_WARNING_WEIGHT}%"
        return "hold", "hold_with_risk", f"趋势仍强，但当前仓位{current_weight:.2f}%偏集中，不建议继续加仓"
    if score < 45 and rebalance_amount < -rebalance_threshold:
        return "reduce", "reduce", "趋势偏弱且当前仓位高于目标仓位"
    if score >= 70 and rebalance_amount > rebalance_threshold:
        return "buy", "add", "趋势强且当前仓位低于目标仓位"
    return "hold", "hold", "趋势和仓位暂未触发明确调仓信号"


def build_next_actions(items, overview_context):
    actions = []

    for item in items:
        if item["decision"] in ("reduce_concentration", "hold_with_risk", "reduce", "sell", "add"):
            priority = {
                "reduce_concentration": 1,
                "sell": 2,
                "reduce": 3,
                "hold_with_risk": 4,
                "add": 5,
            }[item["decision"]]
            actions.append({
                "type": item["decision"] if item["decision"] == "hold_with_risk" else item["action"],
                "priority": priority,
                "code": item["code"],
                "name": item["name"],
                "title": item["decision_text"],
                "amount": item["rebalance_amount"],
                "reason": item["decision_reason"],
            })

    candidate_buys = [
        item for item in items
        if item["decision"] in ("candidate_buy", "watch_candidate")
    ][:3]
    for idx, item in enumerate(candidate_buys, 1):
        actions.append({
            "type": item["decision"],
            "priority": 10 + idx,
            "code": item["code"],
            "name": item["name"],
            "title": item["decision_text"],
            "amount": None,
            "reason": item["decision_reason"],
        })

    if overview_context["missing_positions"]:
        actions.append({
            "type": "input",
            "priority": 20,
            "code": None,
            "name": None,
            "title": "补全持仓输入",
            "amount": None,
            "reason": f"还有{overview_context['missing_positions']}只基金缺少买入价格和金额，完整录入后建议金额才可靠",
        })

    actions.sort(key=lambda action: action["priority"])
    return actions[:8]


def build_portfolio_recommendation(items, missing_positions, average_score, total_current_value, held_count, watch_count):
    warnings = []
    stance = "等待"
    conclusion = "先补全持仓数据，再执行买卖动作。"

    concentrated = [
        item for item in items
        if item["decision"] in ("reduce_concentration", "hold_with_risk")
    ]
    add_candidates = [
        item for item in items
        if item["decision"] in ("add", "candidate_buy")
    ]
    weak_exits = [
        item for item in items
        if item["decision"] in ("reduce", "sell")
    ]

    if missing_positions:
        warnings.append(f"{missing_positions}只基金缺少买入价和金额，调仓金额只对已录入部分可靠")

    if concentrated:
        stance = "控制集中度"
        names = "、".join(item["name"] for item in concentrated[:2])
        conclusion = f"{names}仓位过重，优先降低单只集中度；强势不等于可以继续重仓。"
        warnings.append("当前组合集中度过高，继续加仓会放大回撤风险")
    elif weak_exits:
        stance = "先防守"
        conclusion = "先处理弱势或超配基金，再考虑新增买入。"
    elif add_candidates and average_score >= 70:
        stance = "精选加仓"
        conclusion = "持仓池整体偏强，可只选择评分靠前且仓位不足的基金分批加仓。"
    elif average_score >= 70:
        stance = "持有观察"
        conclusion = "基金池趋势偏强，但当前仓位未出现明确加仓信号，适合持有观察。"
    elif average_score >= 50:
        stance = "均衡观望"
        conclusion = "基金池强弱分化，建议等待更明确的趋势信号。"
    else:
        stance = "防守回避"
        conclusion = "基金池整体偏弱，优先控制仓位，不急于买入。"

    if total_current_value == 0:
        conclusion = "还没有有效持仓金额，先录入已买基金的买入价和金额，再输出可执行调仓金额。"
    elif watch_count:
        warnings.append(f"{watch_count}只未持有基金仅作为观察池，不参与当前持仓调仓金额")

    return {
        "stance": stance,
        "conclusion": conclusion,
        "warnings": warnings,
        "can_execute": bool(total_current_value and held_count),
    }


def build_strategy_report(funds, positions, theme_signals=None):
    theme_signals = theme_signals or {}
    scored = []
    for fund in funds:
        code = fund.get("code")
        theme_signal = theme_signals.get(code, {})
        score, reasons = score_fund(fund, theme_signal)
        raw_weight = max(score - 40, 0) if fund.get("success") else 0
        scored.append({
            "fund": fund,
            "score": score,
            "reasons": reasons,
            "raw_weight": raw_weight,
            "theme": theme_signal,
        })

    held_codes = {
        code for code, position in (positions or {}).items()
        if valid_position(position)
    }
    total_raw_weight = sum(
        item["raw_weight"] for item in scored
        if item["fund"].get("code") in held_codes
    )
    target_weights = {}
    for item in scored:
        code = item["fund"].get("code")
        if code not in held_codes:
            target_weights[code] = 0
        elif total_raw_weight > 0:
            target_weights[code] = item["raw_weight"] / total_raw_weight * 100
        elif scored:
            target_weights[code] = 100 / len(held_codes) if held_codes else 0
        else:
            target_weights[code] = 0

    prepared_items = []
    total_invested = 0
    total_current_value = 0
    missing_positions = 0
    held_count = 0
    watch_count = 0

    for item in scored:
        fund = item["fund"]
        code = fund.get("code")
        raw_position = (positions or {}).get(code)
        position = valid_position(raw_position)
        price_context = price_context_for(fund)
        price = price_context["current_price"]
        needs_position = position is None
        position_status = "watch" if needs_position else "held"
        current_value = 0
        profit_amount = 0
        profit_percent = None

        if needs_position:
            watch_count += 1
            # 完全未录入的基金视为观察池；录入过但数据不完整/非法的才算"缺失"
            if raw_position:
                missing_positions += 1
        else:
            held_count += 1
            total_invested += position["amount"]
            if price:
                current_value = position["amount"] / position["buy_price"] * price
                profit_amount = current_value - position["amount"]
                profit_percent = profit_amount / position["amount"] * 100
            else:
                current_value = position["amount"]
                profit_amount = 0
                profit_percent = 0
            total_current_value += current_value

        prepared_items.append({
            "fund": fund,
            "score": item["score"],
            "reasons": item["reasons"],
            "position": position,
            "price": price,
            "price_context": price_context,
            "theme": item["theme"],
            "needs_position": needs_position,
            "position_status": position_status,
            "current_value": current_value,
            "profit_amount": profit_amount,
            "profit_percent": profit_percent,
            "target_weight": target_weights.get(code, 0),
        })

    rebalance_threshold = max(total_current_value * 0.02, 100) if total_current_value else 100
    output_items = []

    for item in prepared_items:
        fund = item["fund"]
        score = item["score"]
        target_value = total_current_value * item["target_weight"] / 100 if total_current_value else 0
        rebalance_amount = target_value - item["current_value"]
        action, decision, decision_reason = classify_decision(item, total_current_value, rebalance_threshold)

        output_items.append({
            "code": fund.get("code"),
            "name": fund.get("name", fund.get("code")),
            "success": bool(fund.get("success")),
            "score": score,
            "action": action,
            "action_text": ACTION_LABELS[action],
            "decision": decision,
            "decision_text": DECISION_LABELS[decision],
            "decision_reason": decision_reason,
            "theme": item["theme"],
            "target_weight": round(item["target_weight"], 2),
            "current_weight": round(item["current_value"] / total_current_value * 100, 2) if total_current_value else 0,
            "current_price": item["price"],
            "price_source": item["price_context"]["price_source"],
            "price_source_text": item["price_context"]["price_source_text"],
            "price_date": item["price_context"]["price_date"],
            "estimated_price": item["price_context"]["estimated_price"],
            "estimate_time": item["price_context"]["estimate_time"],
            "buy_price": item["position"]["buy_price"] if item["position"] else None,
            "invested_amount": round_money(item["position"]["amount"]) if item["position"] else None,
            "current_value": round_money(item["current_value"]),
            "profit_amount": round_money(item["profit_amount"]),
            "profit_percent": round(item["profit_percent"], 2) if item["profit_percent"] is not None else None,
            "target_value": round_money(target_value),
            "rebalance_amount": round_money(rebalance_amount),
            "needs_position": item["needs_position"],
            "position_status": item["position_status"],
            "reason": "、".join(item["reasons"][:4]),
            "metrics": {
                "estimate_change": fund.get("estimate_change", "--"),
                "week_growth": fund.get("week_growth", "--"),
                "month_growth": fund.get("month_growth", "--"),
                "three_month_growth": fund.get("three_month_growth", "--"),
                "six_month_growth": fund.get("six_month_growth", "--"),
                "year_growth": fund.get("year_growth", "--"),
            },
        })

    output_items.sort(key=lambda x: x["score"], reverse=True)
    action_counts = Counter(item["action"] for item in output_items)
    for action in ACTION_LABELS:
        action_counts.setdefault(action, 0)

    scenario_base = 0
    if output_items and total_raw_weight > 0:
        for item in scored:
            code = item["fund"].get("code")
            scenario_base += monthly_expectation(item["fund"]) * target_weights.get(code, 0) / 100
    elif output_items:
        scenario_base = sum(monthly_expectation(item["fund"]) for item in scored) / len(scored)

    scenario_base = round(scenario_base, 2)
    scenario = {
        "conservative": {
            "percent": round(scenario_base - 3, 2),
            "amount": round_money(total_current_value * (scenario_base - 3) / 100),
        },
        "base": {
            "percent": scenario_base,
            "amount": round_money(total_current_value * scenario_base / 100),
        },
        "optimistic": {
            "percent": round(scenario_base + 4, 2),
            "amount": round_money(total_current_value * (scenario_base + 4) / 100),
        },
    }

    average_score = round(sum(item["score"] for item in scored) / len(scored), 1) if scored else 0
    if average_score >= 70:
        risk_level = "进攻"
    elif average_score >= 50:
        risk_level = "均衡"
    else:
        risk_level = "防守"

    overview_context = {
        "missing_positions": missing_positions,
    }
    recommendation = build_portfolio_recommendation(
        output_items,
        missing_positions,
        average_score,
        total_current_value,
        held_count,
        watch_count
    )
    next_actions = build_next_actions(output_items, overview_context)

    return {
        "overview": {
            "total_funds": len(funds),
            "held_count": held_count,
            "watch_count": watch_count,
            "missing_positions": missing_positions,
            "total_invested": round_money(total_invested),
            "current_value": round_money(total_current_value),
            "profit_amount": round_money(total_current_value - total_invested),
            "profit_percent": round((total_current_value - total_invested) / total_invested * 100, 2) if total_invested else 0,
            "average_score": average_score,
            "risk_level": risk_level,
            "action_counts": dict(action_counts),
            "recommendation": recommendation,
            "next_actions": next_actions,
            "scenario": scenario,
            "disclaimer": "情景预期仅基于当前持仓池的趋势分数测算，不代表收益承诺。",
        },
        "items": output_items,
    }
