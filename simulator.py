"""
Hotel Booking Demand Simulator

Generates realistic customer demand for hotel bookings to test pricing strategies.
Simulates two user personas: Casual Travellers and Business Travellers.
"""

import json
import random
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from datetime import datetime
import os

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Demand:
    """Represents a single user shopping for a hotel on a specific day."""
    shopping_date: int
    stay_start_date: int
    stay_end_date: int
    max_price_per_night: float

@dataclass
class Itinerary:
    """Represents a collection of Demand objects for one trip."""
    user_id: str
    trip_id: int
    demands: List[Demand]
    is_booked: bool = False
    booked_price_per_night: Optional[float] = None

class HotelDemandSimulator:
    """Main simulator class for generating and processing hotel demand."""
    
    def __init__(self):
        self.simulation_parameters = {}
        self.users = {}  # user_id -> list of itineraries
        self.hotel_capacity = {}  # day -> remaining capacity
        self.bookings = []  # list of all bookings made

    def _generate_travellers(self, num_casual: int, num_business: int):
        
        # Generate casual travellers
        for i in range(num_casual):
            user_id = f"casual-{i+1:03d}"
            self._generate_casual_traveller(user_id)

        # Generate business travellers
        for i in range(num_business):
            user_id = f"business-{i+1:03d}"
            self._generate_business_traveller(user_id)

        
    def generate_demand(self, total_users: int, proportion_casual: float, hotel_capacity: int):
        """
        Generate a complete simulation run with all users and their annual itineraries.

        Args:
            total_users: Total number of users to simulate
            proportion_casual: Proportion of casual travellers (0.0 to 1.0)
            hotel_capacity: Number of available rooms per day
        """
        logger.info(f"Starting demand generation: {total_users} users, {proportion_casual*100:.1f}% casual, {hotel_capacity} capacity")

        self.simulation_parameters = {
            "total_users": total_users,
            "proportion_casual": proportion_casual,
            "hotel_capacity_per_day": hotel_capacity
        }

        # Initialize hotel capacity for all days
        self.hotel_capacity = {day: hotel_capacity for day in range(0, 100)}

        # Calculate number of casual and business travellers
        num_casual = int(total_users * proportion_casual)
        num_business = total_users - num_casual
        logger.info(f"Generating {num_casual} casual travellers and {num_business} business travellers")

        self._generate_travellers(num_casual, num_business)
        
        # Calculate total demands
        total_demands = sum(
            len(itinerary.demands)
            for itineraries in self.users.values()
            for itinerary in itineraries
        )
        logger.info(f"Demand generation complete: {total_demands} total demands generated")
    
    def _generate_casual_traveller(self, user_id: str):
        """Generate a casual traveller with 2 trips per year."""
        itineraries = []

        # Generate 2 trips
        trip_dates = self._schedule_trips(num_trips=2, year_length=100)

        for trip_id, start_date in enumerate(trip_dates):
            # Trip length: Normal(8, 2)
            trip_length = max(1, int(random.gauss(8, 2)))
            end_date = min(99, start_date + trip_length - 1)

            # Base max price: Normal(110, 20)
            base_max_price = random.gauss(110, 20)
            min_price = base_max_price * random.uniform(0.7, 0.9)

            # Shopping window: 50-10 days before, ends 10-5 days before
            shop_start = start_date - random.randint(20, 50)
            shop_end = start_date - random.randint(5, 15)

            # Clamp shopping window to start no earlier than day -20
            shop_start = max(shop_start, -20)

            # Ensure shop_end is after shop_start
            if shop_end <= shop_start:
                shop_end = shop_start + 1

            # Generate demands for each shopping day
            demands = []
            for shopping_day in range(shop_start, shop_end + 1):
                # Linear interpolation for price
                progress = (shopping_day - shop_start) / (shop_end - shop_start)
                max_price_per_night = min_price + (base_max_price - min_price) * progress

                demand = Demand(
                    shopping_date=shopping_day,
                    stay_start_date=start_date,
                    stay_end_date=end_date,
                    max_price_per_night=max_price_per_night
                )
                demands.append(demand)
            
            itinerary = Itinerary(
                user_id=user_id,
                trip_id=trip_id,
                demands=demands
            )
            itineraries.append(itinerary)
        
        self.users[user_id] = itineraries
    
    def _generate_business_traveller(self, user_id: str):
        """Generate a business traveller with 5 trips per year (1 long, 4 short)."""
        itineraries = []
        
        # Generate 5 trips: 1 long + 4 short
        trip_lengths = []

        # long trip
        trip_lengths.append(max(1, int(random.gauss(20, 5))))  # Long trip

        # short trip
        for _ in range(4):
            trip_lengths.append(max(1, int(random.gauss(5, 1))))  # Short trips
        
        trip_dates = self._schedule_trips(num_trips=5, year_length=100, trip_lengths=trip_lengths)
        
        for trip_id, start_date in enumerate(trip_dates):
            trip_length = trip_lengths[trip_id]
            end_date = min(99, start_date + trip_length - 1)
            
            # Fixed max price: Normal(150, 10) - Higher willingness to pay (willing to pay a premium)
            max_price_per_night = random.gauss(150, 10)
            
            # Shopping window: 7-3 days before
            shop_start = start_date - random.randint(3, 7)
            shop_end = start_date - 1

            # Clamp shopping window to start no earlier than day -20
            shop_start = max(shop_start, -20)

            # Generate demands for each shopping day
            demands = []
            for shopping_day in range(shop_start, shop_end + 1):
                demand = Demand(
                    shopping_date=shopping_day,
                    stay_start_date=start_date,
                    stay_end_date=end_date,
                    max_price_per_night=max_price_per_night
                )
                demands.append(demand)
            
            itinerary = Itinerary(
                user_id=user_id,
                trip_id=trip_id,
                demands=demands
            )
            itineraries.append(itinerary)
        
        self.users[user_id] = itineraries
    
    # naive trip scheduling method currently doesn't deconflict between clashing trips (uses) a naive 25 day block out period to avoid clashes
    def _schedule_trips(self, num_trips: int, year_length: int, trip_lengths: Optional[List[int]] = None) -> List[int]:
        """Schedule non-overlapping trip start dates for a user."""
        trip_dates = []
        available_days = set(range(0, year_length))

        if trip_lengths:

            # if trip_lengths are decided (business travellers), then use that to schedule rather than blanket 25 day black out window
            assert len(trip_lengths) == num_trips
            trip_lengths = sorted(trip_lengths, reverse=True)

            for length in trip_lengths:
                if not available_days:
                    break
                
                # Pick a random available day
                start_date = random.choice(list(available_days))
                trip_dates.append(start_date)
                
                # Remove this day and some days after (rough estimate of trip length)
                for day in range(start_date, min(start_date + length + 1, year_length)):
                    available_days.discard(day)
                
            return sorted(trip_dates)
        else:
        
            for _ in range(num_trips):
                if not available_days:
                    break
                
                # Pick a random available day
                start_date = random.choice(list(available_days))
                trip_dates.append(start_date)
                
                # Remove this day and some days after (rough estimate of trip length)
                for day in range(start_date, min(start_date + 25, year_length)):
                    available_days.discard(day)
            
            return sorted(trip_dates)
    
    def save_run(self, filepath: str):
        """Save the generated demand to a JSON file."""
        logger.info(f"Saving simulation to {filepath}")

        data = {
            "simulation_parameters": self.simulation_parameters,
            "users": {}
        }

        for user_id, itineraries in self.users.items():
            user_data = []
            for itinerary in itineraries:
                demands_data = [asdict(d) for d in itinerary.demands]
                itinerary_data = {
                    "trip_id": itinerary.trip_id,
                    "demands": demands_data,
                    "is_booked": itinerary.is_booked,
                    "booked_price_per_night": itinerary.booked_price_per_night
                }
                user_data.append(itinerary_data)
            data["users"][user_id] = user_data

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        file_size = os.path.getsize(filepath)
        logger.info(f"Simulation saved successfully: {file_size} bytes")
        logger.debug(f"File path: {os.path.abspath(filepath)}")

    def load_run(self, filepath: str):
        """Load a previously saved demand run from JSON."""
        logger.info(f"Loading simulation from {filepath}")

        with open(filepath, 'r') as f:
            data = json.load(f)

        self.simulation_parameters = data["simulation_parameters"]
        logger.debug(f"Loaded parameters: {self.simulation_parameters}")

        self.users = {}

        for user_id, user_data in data["users"].items():
            itineraries = []
            for itinerary_data in user_data:
                demands = [
                    Demand(**d) for d in itinerary_data["demands"]
                ]
                itinerary = Itinerary(
                    user_id=user_id,
                    trip_id=itinerary_data["trip_id"],
                    demands=demands,
                    is_booked=itinerary_data["is_booked"],
                    booked_price_per_night=itinerary_data["booked_price_per_night"]
                )
                itineraries.append(itinerary)
            self.users[user_id] = itineraries

        # Initialize hotel capacity
        hotel_capacity = self.simulation_parameters["hotel_capacity_per_day"]
        self.hotel_capacity = {day: hotel_capacity for day in range(-20, 100)}

        logger.info(f"Simulation loaded successfully: {len(self.users)} users")

    def process_daily_prices(self, simulation_day: int, daily_prices: Dict[str, float]) -> List[Dict]:
        """
        Process daily prices and generate bookings for the given simulation day.

        Args:
            simulation_day: Current simulated day
            daily_prices: Dict mapping stay dates (as strings) to prices

        Returns:
            List of successful bookings made on this day
        """

        bookings_today = []
        demands_checked = 0
        price_rejections = 0
        capacity_rejections = 0

        # Find all demands for this shopping date
        for user_id, itineraries in self.users.items():
            for itinerary in itineraries:
                # Skip if already booked
                if itinerary.is_booked:
                    continue

                # Find demands for this shopping date
                matching_demands = [d for d in itinerary.demands if d.shopping_date == simulation_day]

                if not matching_demands:
                    continue

                demands_checked += 1

                # Use the first matching demand (they should all be the same for a trip)
                demand = matching_demands[0]

                # Calculate average price for the stay
                stay_dates = range(demand.stay_start_date, demand.stay_end_date + 1)
                prices_for_stay = []

                for date in stay_dates:
                    price = daily_prices.get(str(date), float('inf'))
                    prices_for_stay.append(price)

                avg_price = sum(prices_for_stay) / len(prices_for_stay) if prices_for_stay else float('inf')

                # Check if booking is successful
                # Condition 1: Average price <= max price
                price_acceptable = avg_price <= demand.max_price_per_night

                # Condition 2: Hotel has capacity for all nights
                capacity_available = all(
                    self.hotel_capacity.get(date, 0) > 0
                    for date in stay_dates
                )

                if not price_acceptable:
                    price_rejections += 1
                    logger.info(f"{user_id}: Price ${avg_price:.2f} > max ${demand.max_price_per_night:.2f}")

                if not capacity_available:
                    capacity_rejections += 1
                    logger.debug(f"{user_id}: Insufficient capacity for days {demand.stay_start_date}-{demand.stay_end_date}")

                if price_acceptable and capacity_available:
                    # Mark itinerary as booked
                    itinerary.is_booked = True
                    itinerary.booked_price_per_night = avg_price

                    # Decrement capacity for each night
                    for date in stay_dates:
                        self.hotel_capacity[date] -= 1

                    # Record booking
                    booking = {
                        "user_id": user_id,
                        "booked_price_per_night": avg_price,
                        "stay_dates": {
                            "start_date": demand.stay_start_date,
                            "end_date": demand.stay_end_date
                        }
                    }
                    bookings_today.append(booking)
                    self.bookings.append(booking)

                    logger.info(f"Booking confirmed: {user_id} at ${avg_price:.2f}/night for days {demand.stay_start_date}-{demand.stay_end_date}")

        logger.info(f"Day {simulation_day}: {demands_checked} demands checked, {len(bookings_today)} bookings made, {price_rejections} price rejections, {capacity_rejections} capacity rejections")

        return bookings_today

