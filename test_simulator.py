"""
Unit tests for the Hotel Demand Simulator.
"""

import unittest
import json
import os
import tempfile
from simulator import HotelDemandSimulator, Demand, Itinerary


class TestDemandAndItinerary(unittest.TestCase):
    """Test Demand and Itinerary data structures."""
    
    def test_demand_creation(self):
        """Test creating a Demand object."""
        demand = Demand(
            shopping_date=-10,
            stay_start_date=5,
            stay_end_date=10,
            max_price_per_night=120.0
        )
        self.assertEqual(demand.shopping_date, -10)
        self.assertEqual(demand.stay_start_date, 5)
        self.assertEqual(demand.stay_end_date, 10)
        self.assertEqual(demand.max_price_per_night, 120.0)
    
    def test_itinerary_creation(self):
        """Test creating an Itinerary object."""
        demands = [
            Demand(-10, 5, 10, 120.0),
            Demand(-9, 5, 10, 125.0)
        ]
        itinerary = Itinerary(
            user_id="casual-001",
            trip_id=0,
            demands=demands
        )
        self.assertEqual(itinerary.user_id, "casual-001")
        self.assertEqual(itinerary.trip_id, 0)
        self.assertEqual(len(itinerary.demands), 2)
        self.assertFalse(itinerary.is_booked)


class TestSimulatorGeneration(unittest.TestCase):
    """Test demand generation."""
    
    def setUp(self):
        """Create a fresh simulator for each test."""
        self.simulator = HotelDemandSimulator()
    
    def test_generate_demand_basic(self):
        """Test basic demand generation."""
        self.simulator.generate_demand(
            total_users=10,
            proportion_casual=0.8,
            hotel_capacity=50
        )
        
        # Check parameters are stored
        self.assertEqual(self.simulator.simulation_parameters['total_users'], 10)
        self.assertEqual(self.simulator.simulation_parameters['proportion_casual'], 0.8)
        self.assertEqual(self.simulator.simulation_parameters['hotel_capacity_per_day'], 50)
        
        # Check users are generated
        self.assertEqual(len(self.simulator.users), 10)
        
        # Check casual/business split
        casual_count = sum(1 for uid in self.simulator.users.keys() if uid.startswith('casual'))
        business_count = sum(1 for uid in self.simulator.users.keys() if uid.startswith('business'))
        self.assertEqual(casual_count, 8)
        self.assertEqual(business_count, 2)
    
    def test_casual_traveller_trips(self):
        """Test that casual travellers have 2 trips."""
        self.simulator.generate_demand(
            total_users=5,
            proportion_casual=1.0,
            hotel_capacity=50
        )
        
        for user_id, itineraries in self.simulator.users.items():
            self.assertEqual(len(itineraries), 2, f"{user_id} should have 2 trips")
    
    def test_business_traveller_trips(self):
        """Test that business travellers have 5 trips."""
        self.simulator.generate_demand(
            total_users=5,
            proportion_casual=0.0,
            hotel_capacity=50
        )
        
        for user_id, itineraries in self.simulator.users.items():
            self.assertEqual(len(itineraries), 5, f"{user_id} should have 5 trips")
    
    def test_hotel_capacity_initialization(self):
        """Test that hotel capacity is initialized correctly."""
        self.simulator.generate_demand(
            total_users=10,
            proportion_casual=0.8,
            hotel_capacity=75
        )
        
        # Check capacity for all days
        for day in range(-20, 100):
            self.assertEqual(self.simulator.hotel_capacity[day], 75)
    
    def test_demands_have_shopping_dates(self):
        """Test that all demands have valid shopping dates."""
        self.simulator.generate_demand(
            total_users=20,
            proportion_casual=0.5,
            hotel_capacity=50
        )
        
        for user_id, itineraries in self.simulator.users.items():
            for itinerary in itineraries:
                for demand in itinerary.demands:
                    # Shopping date should be before stay date
                    self.assertLess(demand.shopping_date, demand.stay_start_date)
                    # Stay dates should be valid
                    self.assertLessEqual(demand.stay_start_date, demand.stay_end_date)
                    # Stay dates should be in valid range
                    self.assertGreaterEqual(demand.stay_start_date, 0)
                    self.assertLess(demand.stay_end_date, 100)


class TestSaveAndLoad(unittest.TestCase):
    """Test saving and loading simulations."""
    
    def setUp(self):
        """Create a fresh simulator and temp directory."""
        self.simulator = HotelDemandSimulator()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load(self):
        """Test saving and loading a simulation."""
        # Generate
        self.simulator.generate_demand(
            total_users=5,
            proportion_casual=0.8,
            hotel_capacity=50
        )
        
        # Save
        filepath = os.path.join(self.temp_dir, 'test_sim.json')
        self.simulator.save_run(filepath)
        self.assertTrue(os.path.exists(filepath))
        
        # Load into new simulator
        new_simulator = HotelDemandSimulator()
        new_simulator.load_run(filepath)
        
        # Verify parameters match
        self.assertEqual(
            new_simulator.simulation_parameters,
            self.simulator.simulation_parameters
        )
        
        # Verify users match
        self.assertEqual(len(new_simulator.users), len(self.simulator.users))
    
    def test_json_structure(self):
        """Test that saved JSON has correct structure."""
        self.simulator.generate_demand(
            total_users=2,
            proportion_casual=1.0,
            hotel_capacity=50
        )
        
        filepath = os.path.join(self.temp_dir, 'test_structure.json')
        self.simulator.save_run(filepath)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Check top-level structure
        self.assertIn('simulation_parameters', data)
        self.assertIn('users', data)
        
        # Check parameters
        params = data['simulation_parameters']
        self.assertIn('total_users', params)
        self.assertIn('proportion_casual', params)
        self.assertIn('hotel_capacity_per_day', params)
        
        # Check users structure
        for user_id, user_data in data['users'].items():
            self.assertIsInstance(user_data, list)
            for itinerary in user_data:
                self.assertIn('trip_id', itinerary)
                self.assertIn('demands', itinerary)
                self.assertIn('is_booked', itinerary)


class TestProcessDailyPrices(unittest.TestCase):
    """Test the process_daily_prices method."""
    
    def setUp(self):
        """Create a simulator with a simple scenario."""
        self.simulator = HotelDemandSimulator()
        self.simulator.generate_demand(
            total_users=10,
            proportion_casual=0.5,
            hotel_capacity=100
        )
    
    def test_process_daily_prices_no_demands(self):
        """Test processing prices when no demands exist for that day."""
        bookings = self.simulator.process_daily_prices(
            simulation_day=-100,  # Day with no demands
            daily_prices={str(i): 100 for i in range(100)}
        )
        self.assertEqual(len(bookings), 0)
    
    def test_process_daily_prices_successful_booking(self):
        """Test that bookings are made when conditions are met."""
        # Find a demand to test with
        test_demand = None
        for user_id, itineraries in self.simulator.users.items():
            for itinerary in itineraries:
                if itinerary.demands:
                    test_demand = itinerary.demands[0]
                    break
            if test_demand:
                break
        
        if test_demand:
            # Set prices below max price
            daily_prices = {
                str(i): test_demand.max_price_per_night - 10
                for i in range(100)
            }
            
            bookings = self.simulator.process_daily_prices(
                simulation_day=test_demand.shopping_date,
                daily_prices=daily_prices
            )
            
            # Should have at least one booking
            self.assertGreater(len(bookings), 0)
            
            # Check booking structure
            booking = bookings[0]
            self.assertIn('user_id', booking)
            self.assertIn('booked_price_per_night', booking)
            self.assertIn('stay_dates', booking)
    
    def test_capacity_decrements(self):
        """Test that hotel capacity decrements after booking."""
        initial_capacity = self.simulator.hotel_capacity[0]
        
        # Find a demand for day 0
        test_demand = None
        for user_id, itineraries in self.simulator.users.items():
            for itinerary in itineraries:
                for demand in itinerary.demands:
                    if demand.stay_start_date == 0:
                        test_demand = demand
                        break
                if test_demand:
                    break
            if test_demand:
                break
        
        if test_demand:
            daily_prices = {str(i): 50 for i in range(100)}
            
            self.simulator.process_daily_prices(
                simulation_day=test_demand.shopping_date,
                daily_prices=daily_prices
            )
            
            # Capacity should have decreased
            self.assertLess(
                self.simulator.hotel_capacity[0],
                initial_capacity
            )
    
    def test_no_booking_insufficient_capacity(self):
        """Test that booking fails when capacity is insufficient."""
        # Set capacity to 0
        self.simulator.hotel_capacity = {day: 0 for day in range(-20, 100)}
        
        daily_prices = {str(i): 50 for i in range(100)}
        bookings = self.simulator.process_daily_prices(
            simulation_day=-10,
            daily_prices=daily_prices
        )
        
        # Should have no bookings
        self.assertEqual(len(bookings), 0)
    
    def test_no_booking_price_too_high(self):
        """Test that booking fails when price is too high."""
        # Find a demand
        test_demand = None
        for user_id, itineraries in self.simulator.users.items():
            for itinerary in itineraries:
                if itinerary.demands:
                    test_demand = itinerary.demands[0]
                    break
            if test_demand:
                break
        
        if test_demand:
            # Set prices above max price
            daily_prices = {
                str(i): test_demand.max_price_per_night + 100
                for i in range(100)
            }
            
            bookings = self.simulator.process_daily_prices(
                simulation_day=test_demand.shopping_date,
                daily_prices=daily_prices
            )
            
            # Should have no bookings
            self.assertEqual(len(bookings), 0)


if __name__ == '__main__':
    unittest.main()

