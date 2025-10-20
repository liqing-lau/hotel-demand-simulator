"""
Test to verify that shopping dates never go before day -20.
"""

from simulator import HotelDemandSimulator

def test_shopping_date_bounds():
    """Verify all shopping dates are >= -20."""
    
    print("=" * 60)
    print("Testing Shopping Date Bounds (Day -20 minimum)")
    print("=" * 60)
    
    # Generate multiple simulations to test edge cases
    for run in range(5):
        print(f"\nRun {run + 1}: Generating simulation with 100 users...")
        sim = HotelDemandSimulator()
        sim.generate_demand(total_users=100, proportion_casual=0.8, hotel_capacity=50)
        
        # Check all demands have shopping dates >= -20
        min_shopping_date = float('inf')
        max_shopping_date = float('-inf')
        total_demands = 0
        
        for user_id, itineraries in sim.users.items():
            for itinerary in itineraries:
                for demand in itinerary.demands:
                    total_demands += 1
                    shopping_date = demand.shopping_date
                    min_shopping_date = min(min_shopping_date, shopping_date)
                    max_shopping_date = max(max_shopping_date, shopping_date)
                    
                    # Verify shopping date is within bounds
                    if shopping_date < -20:
                        print(f"   ✗ ERROR: {user_id} has shopping_date {shopping_date} < -20")
                        print(f"     Demand: {demand}")
                        raise AssertionError(f"Shopping date {shopping_date} is before day -20")
        
        print(f"   ✓ All {total_demands} demands have valid shopping dates")
        print(f"   - Min shopping date: {min_shopping_date}")
        print(f"   - Max shopping date: {max_shopping_date}")
        
        # Verify min is >= -20
        assert min_shopping_date >= -20, f"Min shopping date {min_shopping_date} is before -20"
        print(f"   ✓ Minimum shopping date is >= -20")
    
    print("\n" + "=" * 60)
    print("✅ Shopping Date Bounds Test Passed!")
    print("=" * 60)
    print("\nConclusion:")
    print("- All shopping dates are >= day -20")
    print("- No demands have shopping dates before the allowed window")
    print("- Shopping window is properly bounded")

if __name__ == '__main__':
    test_shopping_date_bounds()

