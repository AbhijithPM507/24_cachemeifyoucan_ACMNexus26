def calculate_roi(total_value_at_risk: float,
                  cost_per_shipment: float,
                  num_shipments: int) -> dict:
    """
    Calculate return on investment for rerouting decision.
    """
    loss_if_no_action = total_value_at_risk * 0.8
    total_reroute_cost = cost_per_shipment * num_shipments
    net_savings = loss_if_no_action - total_reroute_cost

    return {
        "value_at_risk": total_value_at_risk,
        "loss_if_no_action": loss_if_no_action,
        "total_reroute_cost": total_reroute_cost,
        "roi_savings": net_savings,
        "roi_positive": net_savings > 0,
        "recommendation": "REROUTE" if net_savings > 0 else "HOLD",
        "roi_ratio": round(net_savings / total_reroute_cost, 2) if total_reroute_cost > 0 else 0
    }