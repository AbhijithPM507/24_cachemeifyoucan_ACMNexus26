import json
import os
from pathlib import Path

def generate_open_manifest(route_waypoints: list, available_space_tonnes: float) -> dict:
    """
    Generates an open cargo manifest by matching available truck space
    with local vendors along the route.
    """
    shared_dir = Path(__file__).parent.parent / "shared_exchange"
    vendors_path = shared_dir / "local_vendors.json"
    output_path = shared_dir / "open_cargo_manifest.json"
    
    if not os.path.exists(vendors_path):
        return {
            "status": "error",
            "message": "Vendors database not found",
            "route_waypoints": route_waypoints,
            "total_space_sold_tonnes": 0.0,
            "total_subsidy_earned_inr": 0.0,
            "matched_contracts": []
        }
    
    with open(vendors_path, 'r', encoding='utf-8') as f:
        vendors = json.load(f)
    
    filtered_vendors = [
        v for v in vendors 
        if v["city"] in route_waypoints
    ]
    
    matched_contracts = []
    total_space_sold = 0.0
    total_subsidy = 0.0
    remaining_space = available_space_tonnes
    
    for vendor in filtered_vendors:
        if remaining_space <= 0:
            break
            
        required = vendor["required_capacity_tonnes"]
        tonnes_to_allocate = min(required, remaining_space)
        
        if tonnes_to_allocate > 0:
            payout = tonnes_to_allocate * vendor["bid_price_per_tonne_inr"]
            
            matched_contracts.append({
                "vendor_name": vendor["company_name"],
                "city": vendor["city"],
                "tonnes_matched": round(tonnes_to_allocate, 2),
                "payout_inr": round(payout, 2)
            })
            
            total_space_sold += tonnes_to_allocate
            total_subsidy += payout
            remaining_space -= tonnes_to_allocate
    
    manifest = {
        "status": "success",
        "route_waypoints": route_waypoints,
        "total_space_sold_tonnes": round(total_space_sold, 2),
        "total_subsidy_earned_inr": round(total_subsidy, 2),
        "matched_contracts": matched_contracts
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    return manifest


if __name__ == "__main__":
    test_result = generate_open_manifest(["Kochi", "Thrissur", "Bangalore"], 8.0)
    print(json.dumps(test_result, indent=2))
