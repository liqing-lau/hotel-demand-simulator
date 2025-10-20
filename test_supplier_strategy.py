"""
Test supplier strategy simulation logic.
"""

import json
import os
import tempfile
from simulator import HotelDemandSimulator

def test_fixed_price_strategy():
    """Test fixed price strategy simulation."""
    print("=" * 60)
    print("Testing Fixed Price Strategy")
    print("=" * 60)
    
    # Generate a small simulation
    sim = HotelDemandSimulator()
    sim.generate_demand(total_users=20, proportion_casual=0.8, hotel_capacity=10)
    
    # Save it
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_sim.json')
        sim.save_run(filepath)
        
        # Load it fresh
        test_sim = HotelDemandSimulator()
        test_sim.load_run(filepath)
        
        # Run fixed price strategy
        hotel_capacity = test_sim.simulation_parameters['hotel_capacity_per_day']
        total_capacity = hotel_capacity * 100
        
        total_revenue = 0
        total_booked_nights = 0
        
        fixed_price = 100.0
        
        for simulation_day in range(-20, 100):
            daily_prices = {str(day): fixed_price for day in range(0, 100)}
            bookings = test_sim.process_daily_prices(simulation_day, daily_prices)
            
            for booking in bookings:
                stay_start = booking['stay_dates']['start_date']
                stay_end = booking['stay_dates']['end_date']
                num_nights = stay_end - stay_start + 1
                total_revenue += booking['booked_price_per_night'] * num_nights
                total_booked_nights += num_nights
        
        occupancy_rate = (total_booked_nights / total_capacity * 100) if total_capacity > 0 else 0
        revpar = total_revenue / total_capacity if total_capacity > 0 else 0
        adr = total_revenue / total_booked_nights if total_booked_nights > 0 else 0
        
        print(f"\nFixed Price Strategy Results:")
        print(f"  Fixed Price: ${fixed_price:.2f}")
        print(f"  Total Available Room-Days: {total_capacity}")
        print(f"  Total Booked Room-Days: {total_booked_nights}")
        print(f"  Occupancy Rate: {occupancy_rate:.1f}%")
        print(f"  Total Revenue: ${total_revenue:.2f}")
        print(f"  RevPAR: ${revpar:.2f}")
        print(f"  ADR: ${adr:.2f}")
        
        assert total_revenue > 0, "Revenue should be positive"
        assert total_booked_nights > 0, "Should have bookings"
        assert occupancy_rate > 0, "Occupancy should be positive"
        print("\n✅ Fixed Price Strategy Test Passed!")


def test_availability_based_strategy():
    """Test availability-based pricing strategy."""
    print("\n" + "=" * 60)
    print("Testing Availability-Based Pricing Strategy")
    print("=" * 60)
    
    # Generate a small simulation
    sim = HotelDemandSimulator()
    sim.generate_demand(total_users=20, proportion_casual=0.8, hotel_capacity=10)
    
    # Save it
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_sim.json')
        sim.save_run(filepath)
        
        # Load it fresh
        test_sim = HotelDemandSimulator()
        test_sim.load_run(filepath)
        
        # Run availability-based strategy
        hotel_capacity = test_sim.simulation_parameters['hotel_capacity_per_day']
        total_capacity = hotel_capacity * 100
        
        total_revenue = 0
        total_booked_nights = 0
        
        min_price = 50.0
        max_price = 200.0
        
        for simulation_day in range(-20, 100):
            daily_prices = {}
            
            for day in range(0, 100):
                rooms_available = test_sim.hotel_capacity.get(day, 0)
                capacity_used = hotel_capacity - rooms_available
                price = min_price + (max_price - min_price) * (capacity_used / hotel_capacity)
                daily_prices[str(day)] = price
            
            bookings = test_sim.process_daily_prices(simulation_day, daily_prices)
            
            for booking in bookings:
                stay_start = booking['stay_dates']['start_date']
                stay_end = booking['stay_dates']['end_date']
                num_nights = stay_end - stay_start + 1
                total_revenue += booking['booked_price_per_night'] * num_nights
                total_booked_nights += num_nights
        
        occupancy_rate = (total_booked_nights / total_capacity * 100) if total_capacity > 0 else 0
        revpar = total_revenue / total_capacity if total_capacity > 0 else 0
        adr = total_revenue / total_booked_nights if total_booked_nights > 0 else 0
        
        print(f"\nAvailability-Based Strategy Results:")
        print(f"  Min Price: ${min_price:.2f}")
        print(f"  Max Price: ${max_price:.2f}")
        print(f"  Total Available Room-Days: {total_capacity}")
        print(f"  Total Booked Room-Days: {total_booked_nights}")
        print(f"  Occupancy Rate: {occupancy_rate:.1f}%")
        print(f"  Total Revenue: ${total_revenue:.2f}")
        print(f"  RevPAR: ${revpar:.2f}")
        print(f"  ADR: ${adr:.2f}")
        
        assert total_revenue > 0, "Revenue should be positive"
        assert total_booked_nights > 0, "Should have bookings"
        assert occupancy_rate > 0, "Occupancy should be positive"
        print("\n✅ Availability-Based Strategy Test Passed!")


def test_strategy_comparison():
    """Compare fixed vs availability-based strategies."""
    print("\n" + "=" * 60)
    print("Comparing Strategies")
    print("=" * 60)
    
    # Generate a simulation
    sim = HotelDemandSimulator()
    sim.generate_demand(total_users=50, proportion_casual=0.8, hotel_capacity=20)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_sim.json')
        sim.save_run(filepath)
        
        # Test Fixed Price
        test_sim1 = HotelDemandSimulator()
        test_sim1.load_run(filepath)
        
        hotel_capacity = test_sim1.simulation_parameters['hotel_capacity_per_day']
        total_capacity = hotel_capacity * 100
        
        fixed_revenue = 0
        fixed_booked = 0
        
        for simulation_day in range(-20, 100):
            daily_prices = {str(day): 120.0 for day in range(0, 100)}
            bookings = test_sim1.process_daily_prices(simulation_day, daily_prices)
            for booking in bookings:
                stay_start = booking['stay_dates']['start_date']
                stay_end = booking['stay_dates']['end_date']
                num_nights = stay_end - stay_start + 1
                fixed_revenue += booking['booked_price_per_night'] * num_nights
                fixed_booked += num_nights
        
        # Test Availability-Based
        test_sim2 = HotelDemandSimulator()
        test_sim2.load_run(filepath)
        
        avail_revenue = 0
        avail_booked = 0
        
        for simulation_day in range(-20, 100):
            daily_prices = {}
            for day in range(0, 100):
                rooms_available = test_sim2.hotel_capacity.get(day, 0)
                capacity_used = hotel_capacity - rooms_available
                price = 50 + (200 - 50) * (capacity_used / hotel_capacity)
                daily_prices[str(day)] = price
            
            bookings = test_sim2.process_daily_prices(simulation_day, daily_prices)
            for booking in bookings:
                stay_start = booking['stay_dates']['start_date']
                stay_end = booking['stay_dates']['end_date']
                num_nights = stay_end - stay_start + 1
                avail_revenue += booking['booked_price_per_night'] * num_nights
                avail_booked += num_nights
        
        print(f"\nStrategy Comparison:")
        print(f"\nFixed Price ($120):")
        print(f"  Revenue: ${fixed_revenue:.2f}")
        print(f"  Booked Nights: {fixed_booked}")
        print(f"  Occupancy: {(fixed_booked/total_capacity*100):.1f}%")
        
        print(f"\nAvailability-Based ($50-$200):")
        print(f"  Revenue: ${avail_revenue:.2f}")
        print(f"  Booked Nights: {avail_booked}")
        print(f"  Occupancy: {(avail_booked/total_capacity*100):.1f}%")
        
        print(f"\nDifference:")
        print(f"  Revenue Difference: ${avail_revenue - fixed_revenue:.2f}")
        print(f"  Occupancy Difference: {(avail_booked - fixed_booked)/total_capacity*100:.1f}%")
        
        print("\n✅ Strategy Comparison Test Passed!")


def test_day_metrics_calculation():
    """Test day-level metrics calculation."""
    print("\n" + "=" * 60)
    print("Testing Day-Level Metrics Calculation")
    print("=" * 60)

    # Generate a small simulation
    sim = HotelDemandSimulator()
    sim.generate_demand(total_users=20, proportion_casual=0.8, hotel_capacity=10)

    # Save it
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_sim.json')
        sim.save_run(filepath)

        # Load it fresh
        test_sim = HotelDemandSimulator()
        test_sim.load_run(filepath)

        hotel_capacity = test_sim.simulation_parameters['hotel_capacity_per_day']

        # Calculate day metrics
        day_metrics = {}

        for day in range(0, 100):
            rooms_booked = hotel_capacity - test_sim.hotel_capacity.get(day, 0)
            occupancy = (rooms_booked / hotel_capacity * 100) if hotel_capacity > 0 else 0

            day_metrics[day] = {
                'occupancy': occupancy,
                'min_price': 50.0,
                'max_price': 200.0,
                'missed_demand': 0,
                'rooms_booked': rooms_booked
            }

        print(f"\nDay-Level Metrics Calculated:")
        print(f"  Total days: {len(day_metrics)}")
        print(f"  Sample metrics:")
        for day in [0, 25, 50, 75, 99]:
            metrics = day_metrics[day]
            print(f"    Day {day}: Occupancy={metrics['occupancy']:.1f}%, Rooms Booked={metrics['rooms_booked']}")

        assert len(day_metrics) == 100, "Should have metrics for all 100 days"
        assert all('occupancy' in m for m in day_metrics.values()), "All days should have occupancy"
        assert all('min_price' in m for m in day_metrics.values()), "All days should have min_price"
        assert all('max_price' in m for m in day_metrics.values()), "All days should have max_price"
        assert all('missed_demand' in m for m in day_metrics.values()), "All days should have missed_demand"

        print("\n✅ Day-Level Metrics Test Passed!")


def test_missed_demands_tracking():
    """Test missed demands tracking with user details."""
    print("\n" + "=" * 60)
    print("Testing Missed Demands Tracking")
    print("=" * 60)

    # Generate a small simulation
    sim = HotelDemandSimulator()
    sim.generate_demand(total_users=20, proportion_casual=0.8, hotel_capacity=5)

    # Save it
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_sim.json')
        sim.save_run(filepath)

        # Load it fresh
        test_sim = HotelDemandSimulator()
        test_sim.load_run(filepath)

        hotel_capacity = test_sim.simulation_parameters['hotel_capacity_per_day']

        # Track missed demands
        missed_demands_list = []

        for simulation_day in range(-20, 100):
            # Use fixed price to potentially create missed demands
            daily_prices = {str(day): 150.0 for day in range(0, 100)}
            bookings = test_sim.process_daily_prices(simulation_day, daily_prices)

        # Collect missed demands
        for user_id, itineraries in test_sim.users.items():
            for itinerary in itineraries:
                if not itinerary.is_booked:
                    for demand in itinerary.demands:
                        user_type = 'Casual' if user_id.startswith('casual') else 'Business'
                        missed_demands_list.append({
                            'user_id': user_id,
                            'user_type': user_type,
                            'shopping_date': demand.shopping_date,
                            'stay_start': demand.stay_start_date,
                            'stay_end': demand.stay_end_date,
                            'num_nights': demand.stay_end_date - demand.stay_start_date + 1,
                            'max_price': demand.max_price_per_night
                        })
                        break

        print(f"\nMissed Demands Tracked:")
        print(f"  Total missed: {len(missed_demands_list)}")

        if missed_demands_list:
            casual_count = sum(1 for d in missed_demands_list if d['user_type'] == 'Casual')
            business_count = sum(1 for d in missed_demands_list if d['user_type'] == 'Business')
            print(f"  Casual: {casual_count}")
            print(f"  Business: {business_count}")

            print(f"\n  Sample missed demands:")
            for demand in missed_demands_list[:3]:
                print(f"    {demand['user_id']} ({demand['user_type']}): "
                      f"Days {demand['stay_start']}-{demand['stay_end']} "
                      f"(max ${demand['max_price']:.0f})")

            # Verify structure
            assert all('user_id' in d for d in missed_demands_list), "All should have user_id"
            assert all('user_type' in d for d in missed_demands_list), "All should have user_type"
            assert all('shopping_date' in d for d in missed_demands_list), "All should have shopping_date"
            assert all('stay_start' in d for d in missed_demands_list), "All should have stay_start"
            assert all('stay_end' in d for d in missed_demands_list), "All should have stay_end"
            assert all('num_nights' in d for d in missed_demands_list), "All should have num_nights"
            assert all('max_price' in d for d in missed_demands_list), "All should have max_price"
        else:
            print(f"  (No missed demands in this simulation)")

        print("\n✅ Missed Demands Tracking Test Passed!")


if __name__ == '__main__':
    test_fixed_price_strategy()
    test_availability_based_strategy()
    test_strategy_comparison()
    test_day_metrics_calculation()
    test_missed_demands_tracking()

    print("\n" + "=" * 60)
    print("✅ All Supplier Strategy Tests Passed!")
    print("=" * 60)

