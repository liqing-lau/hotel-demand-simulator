"""
Example usage of the Hotel Demand Simulator.

This script demonstrates how to:
1. Generate a simulation
2. Save it to a file
3. Load it back
4. Process daily prices and generate bookings
"""

from simulator import HotelDemandSimulator
import json

def main():
    print("=" * 60)
    print("Hotel Demand Simulator - Example Usage")
    print("=" * 60)
    
    # Create a simulator instance
    simulator = HotelDemandSimulator()
    
    # Generate demand for 100 users (80% casual, 20% business)
    print("\n1. Generating demand for 100 users...")
    simulator.generate_demand(
        total_users=100,
        proportion_casual=0.8,
        hotel_capacity=50
    )
    print(f"   ✓ Generated {len(simulator.users)} users")
    
    # Count total demands
    total_demands = sum(
        len(itinerary.demands)
        for itineraries in simulator.users.values()
        for itinerary in itineraries
    )
    print(f"   ✓ Total demands: {total_demands}")
    
    # Save the simulation
    print("\n2. Saving simulation to file...")
    filepath = "simulations/example_simulation.json"
    simulator.save_run(filepath)
    print(f"   ✓ Saved to {filepath}")
    
    # Load the simulation
    print("\n3. Loading simulation from file...")
    new_simulator = HotelDemandSimulator()
    new_simulator.load_run(filepath)
    print(f"   ✓ Loaded {len(new_simulator.users)} users")
    
    # Process daily prices for a specific day
    print("\n4. Processing daily prices for Day -10...")
    
    # Create a pricing strategy: prices increase as we get closer to the stay date
    daily_prices = {}
    for day in range(100):
        # Simple pricing: base price of $100, increases by $0.50 per day closer to stay
        price = 100 + (day * 0.5)
        daily_prices[str(day)] = price
    
    bookings = new_simulator.process_daily_prices(
        simulation_day=-10,
        daily_prices=daily_prices
    )
    
    print(f"   ✓ Bookings made: {len(bookings)}")
    
    if bookings:
        print("\n   Sample bookings:")
        for booking in bookings[:3]:
            print(f"     - User: {booking['user_id']}")
            print(f"       Price per night: ${booking['booked_price_per_night']:.2f}")
            print(f"       Stay: Day {booking['stay_dates']['start_date']} to {booking['stay_dates']['end_date']}")
    
    # Show remaining capacity
    print("\n5. Hotel capacity after bookings:")
    print(f"   Day 0: {new_simulator.hotel_capacity[0]} rooms remaining")
    print(f"   Day 50: {new_simulator.hotel_capacity[50]} rooms remaining")
    print(f"   Day 99: {new_simulator.hotel_capacity[99]} rooms remaining")
    
    # Show statistics
    print("\n6. Simulation Statistics:")
    casual_users = sum(1 for uid in new_simulator.users.keys() if uid.startswith('casual'))
    business_users = sum(1 for uid in new_simulator.users.keys() if uid.startswith('business'))
    print(f"   Casual travellers: {casual_users}")
    print(f"   Business travellers: {business_users}")
    print(f"   Total bookings made: {len(new_simulator.bookings)}")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

