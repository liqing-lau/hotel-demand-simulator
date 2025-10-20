#!/usr/bin/env python3
"""
Test script to validate the metrics reported by the supplier strategy.
Uses simulation_20251020_121116.json as test case.
"""

import json
from simulator import HotelDemandSimulator
from app import _run_supplier_strategy

def load_test_simulation():
    """Load the test simulation file."""
    simulator = HotelDemandSimulator()
    simulator.load_run('simulations/simulation_20251020_121116.json')
    return simulator

def analyze_simulation_data(simulator):
    """Analyze the raw simulation data to understand demand patterns."""
    print("=== SIMULATION DATA ANALYSIS ===")
    print(f"Hotel capacity per day: {simulator.simulation_parameters['hotel_capacity_per_day']}")
    print(f"Total users: {len(simulator.users)}")
    
    total_itineraries = 0
    total_demands = 0
    total_unique_stays = 0
    
    print("\nUser breakdown:")
    for user_id, itineraries in simulator.users.items():
        print(f"  {user_id}: {len(itineraries)} itineraries")
        total_itineraries += len(itineraries)
        
        for itinerary in itineraries:
            total_demands += len(itinerary.demands)
            if itinerary.demands:
                # Each itinerary represents one unique stay
                demand = itinerary.demands[0]
                stay_nights = demand.stay_end_date - demand.stay_start_date + 1
                total_unique_stays += stay_nights
                
                print(f"    Trip {itinerary.trip_id}: {len(itinerary.demands)} shopping days, "
                      f"stay days {demand.stay_start_date}-{demand.stay_end_date} ({stay_nights} nights), "
                      f"booked: {itinerary.is_booked}")
    
    print(f"\nSummary:")
    print(f"  Total itineraries: {total_itineraries}")
    print(f"  Total demands (shopping events): {total_demands}")
    print(f"  Total unique stay room-nights: {total_unique_stays}")
    print(f"  Expected total demanded room-days: {total_unique_stays}")
    
    return total_unique_stays

def test_availability_pricing():
    """Test availability-based pricing with min=80, max=120."""
    print("\n=== TESTING AVAILABILITY-BASED PRICING (80-120) ===")
    
    simulator = load_test_simulation()
    expected_demanded = analyze_simulation_data(simulator)
    
    # Run supplier strategy
    strategy = 'availability'
    params = {'min_price': 80, 'max_price': 120}
    
    metrics = _run_supplier_strategy(simulator, strategy, params)
    
    print(f"\nMetrics Results:")
    print(f"  Total Available Room-Days: {metrics['total_available_room_days']}")
    print(f"  Total Demanded Room-Days: {metrics['total_demanded_room_days']}")
    print(f"  Total Booked Room-Days: {metrics['total_booked_room_days']}")
    print(f"  Occupancy Rate: {metrics['occupancy_rate']:.1f}%")
    print(f"  Total Revenue: ${metrics['total_revenue']:.2f}")
    print(f"  Demand Lost to Price: {metrics['demand_lost_to_price']}")
    print(f"  Demand Lost to Capacity: {metrics['demand_lost_to_capacity']}")
    print(f"  RevPAR: ${metrics['revpar']:.2f}")
    print(f"  ADR: ${metrics['adr']:.2f}")
    
    # Validation
    print(f"\n=== VALIDATION ===")
    print(f"Expected demanded room-days: {expected_demanded}")
    print(f"Reported demanded room-days: {metrics['total_demanded_room_days']}")
    
    if metrics['total_demanded_room_days'] == expected_demanded:
        print("✅ Total demanded room-days is correct!")
    else:
        print("❌ Total demanded room-days is incorrect!")
        print(f"   Difference: {metrics['total_demanded_room_days'] - expected_demanded}")
    
    # Check missed demands details
    print(f"\nMissed Demands Summary:")
    print(f"  Total missed demands: {len(metrics['missed_demands'])}")
    
    if metrics['missed_demands']:
        print(f"  Sample missed demands:")
        for i, demand in enumerate(metrics['missed_demands'][:5]):
            print(f"    {i+1}. {demand['user_id']} ({demand['user_type']}): "
                  f"Shopping Days {demand['shopping_start']}-{demand['shopping_end']}, "
                  f"Stay Days {demand['stay_start']}-{demand['stay_end']} ({demand['num_nights']} nights), "
                  f"Price range: ${demand['price_min']:.0f}-${demand['price_max']:.0f}")
    
    # Check specific user mentioned in the issue
    print(f"\n=== CHECKING BUSINESS-002 ===")
    business_002_found = False
    for demand in metrics['missed_demands']:
        if demand['user_id'] == 'business-002':
            business_002_found = True
            print(f"Found business-002 in missed demands:")
            print(f"  Shopping Days: {demand['shopping_start']}-{demand['shopping_end']}")
            print(f"  Stay Days: {demand['stay_start']}-{demand['stay_end']} ({demand['num_nights']} nights)")
            print(f"  Price range: ${demand['price_min']:.0f}-${demand['price_max']:.0f}")
            break

    if not business_002_found:
        print("business-002 not found in missed demands (may have been booked)")

    # Check all business-002 itineraries
    print(f"\nAll business-002 itineraries:")
    for user_id, itineraries in simulator.users.items():
        if user_id == 'business-002':
            for itinerary in itineraries:
                if itinerary.is_booked:
                    demand = itinerary.demands[0]
                    print(f"  ✅ Trip {itinerary.trip_id}: BOOKED at ${itinerary.booked_price_per_night:.2f}/night")
                    print(f"      Stay: Days {demand.stay_start_date}-{demand.stay_end_date} ({demand.stay_end_date - demand.stay_start_date + 1} nights)")
                else:
                    demand = itinerary.demands[0]
                    print(f"  ❌ Trip {itinerary.trip_id}: NOT BOOKED")
                    print(f"      Stay: Days {demand.stay_start_date}-{demand.stay_end_date} ({demand.stay_end_date - demand.stay_start_date + 1} nights)")
                    print(f"      Max price: ${demand.max_price_per_night:.2f}/night")

    # Detailed categorization analysis
    print(f"\n=== CATEGORIZATION ANALYSIS ===")
    price_lost = []
    capacity_lost = []
    for demand in metrics['missed_demands']:
        if demand['user_id'] == 'business-002':
            # This should be capacity-lost based on the logs
            capacity_lost.append(demand)
        else:
            price_lost.append(demand)

    print(f"Expected categorization based on analysis:")
    print(f"  Price-lost: {len(price_lost)} itineraries")
    print(f"  Capacity-lost: {len(capacity_lost)} itineraries")
    print(f"Actual metrics:")
    print(f"  Demand Lost to Price: {metrics['demand_lost_to_price']}")
    print(f"  Demand Lost to Capacity: {metrics['demand_lost_to_capacity']}")

    if len(capacity_lost) != metrics['demand_lost_to_capacity']:
        print(f"⚠️  Categorization mismatch detected!")
        print(f"   Expected capacity-lost: {len(capacity_lost)}")
        print(f"   Reported capacity-lost: {metrics['demand_lost_to_capacity']}")

if __name__ == '__main__':
    test_availability_pricing()
