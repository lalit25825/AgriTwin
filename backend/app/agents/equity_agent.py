from backend.app.agents.schemas import AgentRunRequest


def run(request: AgentRunRequest, market_result: dict | None = None) -> dict:
    data = {}
    notes = []
    market_price = None
    if market_result and market_result.get("live"):
        market_price = (((market_result.get("data") or {}).get("latest") or {}).get("modal_price"))
    sale_price = request.expected_sale_price or market_price
    if sale_price is not None:
        data["reference_sale_price_inr_per_quintal"] = sale_price
    if request.production_cost_per_quintal is not None and sale_price is not None:
        margin = sale_price - request.production_cost_per_quintal
        data["estimated_margin_inr_per_quintal"] = round(margin, 2)
        data["break_even_price_inr_per_quintal"] = request.production_cost_per_quintal
        notes.append("Indicative margin is calculated from the supplied production cost and sale price; transport, commission, grading, and finance costs may be missing.")
    elif sale_price is None:
        notes.append("Add a sale quote or configure live mandi data to compare the farmer's price with a market reference.")
    else:
        notes.append("Add production cost per quintal to calculate an indicative break-even and margin.")
    if request.quantity_tonnes is not None:
        data["quantity_quintals"] = round(request.quantity_tonnes * 10, 2)
        if sale_price is not None:
            data["gross_value_inr_before_costs"] = round(request.quantity_tonnes * 10 * sale_price, 2)
    data["fairness_checks"] = [
        "Compare at least two nearby mandi quotes on the same date",
        "Show deductions for transport, weighing, commission, and quality clearly",
        "Record the farmer's net realised price, not only the headline modal price",
    ]
    return {
        "id": "equity", "name": "Equity Agent", "status": "completed",
        "headline": "Farmer-side value and transparency review",
        "summary": "Checks the available price and cost inputs, then highlights the deductions and comparisons needed to understand the farmer's net realisation.",
        "data": data, "actions": notes + data["fairness_checks"],
        "source": "User-provided costs and/or Market Agent live reference", "live": bool(market_price),
    }
