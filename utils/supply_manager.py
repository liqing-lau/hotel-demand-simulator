"""
Supply Manager
Handles supply allocation, tracking, and MongoDB operations.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pymongo import MongoClient
from .models import (
    Hotel, TravelAgent, DailySupply, SupplyAllocation,
    Booking, SupplierType, SimulationConfig
)

logger = logging.getLogger(__name__)


class SupplyManager:
    """Manages hotel and travel agent supply, with MongoDB persistence"""
    
    def __init__(self, mongodb_uri: str = "mongodb://localhost:27017/", 
                 db_name: str = "hotel_simulation"):
        """
        Initialize the supply manager
        
        Args:
            mongodb_uri: MongoDB connection string
            db_name: Database name
        """
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
        
        # Collections
        self.daily_supply_collection = self.db['daily_supply']
        self.bookings_collection = self.db['bookings']
        self.simulations_collection = self.db['simulations']
        
        # Create indexes for performance
        self._create_indexes()
        
    def _create_indexes(self):
        """Create database indexes for better query performance"""
        self.daily_supply_collection.create_index([
            ("simulation_id", 1),
            ("hotel_id", 1),
            ("day", 1)
        ], unique=True)
        
        self.bookings_collection.create_index([
            ("simulation_id", 1),
            ("user_id", 1)
        ])
        
    def initialize_simulation(self, simulation_id: str, config: SimulationConfig):
        """
        Initialize supply for a new simulation
        
        Args:
            simulation_id: Unique simulation identifier
            config: Simulation configuration with hotels and travel agents
        """
        logger.info(f"Initializing simulation {simulation_id}")
        
        # Store simulation config
        self.simulations_collection.update_one(
            {"simulation_id": simulation_id},
            {
                "$set": {
                    "simulation_id": simulation_id,
                    "config": self._config_to_dict(config),
                    "created_at": datetime.now(),
                    "status": "initialized"
                }
            },
            upsert=True
        )
        
        # Initialize daily supply for each hotel for each operational day
        for day in range(config.operational_start_day, config.operational_end_day + 1):
            for hotel in config.hotels:
                daily_supply = DailySupply(
                    simulation_id=simulation_id,
                    hotel_id=hotel.hotel_id,
                    day=day,
                    hotel_rooms_total=hotel.total_rooms,
                    hotel_rooms_remaining=hotel.total_rooms,
                    hotel_price=hotel.base_price,
                    travel_agent_allocations=[]
                )
                
                self._save_daily_supply(daily_supply)
        
        # Allocate rooms to travel agents based on schedule
        self._allocate_travel_agent_inventory(simulation_id, config)
        
        logger.info(f"Simulation {simulation_id} initialized successfully")
    
    def _allocate_travel_agent_inventory(self, simulation_id: str, config: SimulationConfig):
        """
        Allocate inventory to travel agents on their scheduled days
        
        Args:
            simulation_id: Simulation identifier
            config: Simulation configuration
        """
        for agent in config.travel_agents:
            for allocation_day in agent.allocation_schedule:
                if allocation_day < config.operational_start_day:
                    continue
                
                # Get allocation rules for this agent
                allocation_rules = config.allocation_rules.get(agent.agent_id, {})
                
                for hotel_id, num_rooms in allocation_rules.items():
                    hotel = config.get_hotel_by_id(hotel_id)
                    if not hotel:
                        continue
                    
                    # Allocate rooms for all remaining days
                    for day in range(allocation_day, config.operational_end_day + 1):
                        # Get current supply for this day
                        daily_supply = self.get_daily_supply(simulation_id, hotel_id, day)
                        if not daily_supply:
                            continue
                        
                        # Check if hotel has enough rooms
                        rooms_to_allocate = min(num_rooms, daily_supply.hotel_rooms_remaining)
                        
                        if rooms_to_allocate > 0:
                            # Create allocation
                            allocation = SupplyAllocation(
                                supplier_id=agent.agent_id,
                                supplier_type=SupplierType.TRAVEL_AGENT,
                                day=day,
                                hotel_id=hotel_id,
                                rooms_allocated=rooms_to_allocate,
                                rooms_remaining=rooms_to_allocate,
                                cost_basis=daily_supply.hotel_price
                            )
                            
                            # Update daily supply
                            daily_supply.hotel_rooms_remaining -= rooms_to_allocate
                            daily_supply.travel_agent_allocations.append(allocation)
                            
                            self._save_daily_supply(daily_supply)
                            
                            logger.debug(f"Allocated {rooms_to_allocate} rooms to {agent.agent_id} "
                                       f"from {hotel_id} for day {day}")
    
    def get_daily_supply(self, simulation_id: str, hotel_id: str, day: int) -> Optional[DailySupply]:
        """
        Get supply information for a specific day and hotel
        
        Args:
            simulation_id: Simulation identifier
            hotel_id: Hotel identifier
            day: Day number
            
        Returns:
            DailySupply object or None if not found
        """
        doc = self.daily_supply_collection.find_one({
            "simulation_id": simulation_id,
            "hotel_id": hotel_id,
            "day": day
        })
        
        if not doc:
            return None
        
        return self._doc_to_daily_supply(doc)
    
    def get_available_suppliers(self, simulation_id: str, day: int, 
                               config: SimulationConfig) -> List[Dict]:
        """
        Get all suppliers with available inventory for a given day
        
        Args:
            simulation_id: Simulation identifier
            day: Day number
            config: Simulation configuration
            
        Returns:
            List of supplier information dicts
        """
        suppliers = []
        
        # Check each hotel
        for hotel in config.hotels:
            daily_supply = self.get_daily_supply(simulation_id, hotel.hotel_id, day)
            if daily_supply and daily_supply.hotel_rooms_remaining > 0:
                suppliers.append({
                    "supplier_id": hotel.hotel_id,
                    "supplier_type": SupplierType.HOTEL,
                    "hotel_id": hotel.hotel_id,
                    "rooms_available": daily_supply.hotel_rooms_remaining,
                    "price": daily_supply.hotel_price
                })
            
            # Check travel agents for this hotel
            if daily_supply:
                for allocation in daily_supply.travel_agent_allocations:
                    if allocation.rooms_remaining > 0:
                        agent = config.get_travel_agent_by_id(allocation.supplier_id)
                        if agent:
                            # Calculate travel agent price
                            price = allocation.cost_basis + agent.operating_cost_per_room
                            price = price * (1 + agent.profit_margin)
                            
                            suppliers.append({
                                "supplier_id": allocation.supplier_id,
                                "supplier_type": SupplierType.TRAVEL_AGENT,
                                "hotel_id": hotel.hotel_id,
                                "rooms_available": allocation.rooms_remaining,
                                "price": price
                            })
        
        return suppliers
    
    def book_room(self, simulation_id: str, supplier_id: str, supplier_type: SupplierType,
                  hotel_id: str, booking_day: int, stay_dates: List[int],
                  user_id: str, trip_id: int, config: SimulationConfig) -> Optional[Booking]:
        """
        Book a room from a supplier for given stay dates
        
        Args:
            simulation_id: Simulation identifier
            supplier_id: ID of the supplier (hotel or travel agent)
            supplier_type: Type of supplier
            hotel_id: Hotel where booking is made
            booking_day: Day when booking is made
            stay_dates: List of days for the stay
            user_id: User making the booking
            trip_id: Trip identifier
            config: Simulation configuration
            
        Returns:
            Booking object if successful, None otherwise
        """
        # Check if all days have availability
        for day in stay_dates:
            daily_supply = self.get_daily_supply(simulation_id, hotel_id, day)
            if not daily_supply:
                logger.warning(f"No supply data for {hotel_id} on day {day}")
                return None
            
            # Check if supplier has rooms
            has_room = False
            if supplier_type == SupplierType.HOTEL:
                has_room = daily_supply.hotel_rooms_remaining > 0
            else:  # TRAVEL_AGENT
                for allocation in daily_supply.travel_agent_allocations:
                    if (allocation.supplier_id == supplier_id and 
                        allocation.rooms_remaining > 0):
                        has_room = True
                        break
            
            if not has_room:
                logger.warning(f"Supplier {supplier_id} has no rooms for day {day}")
                return None
        
        # Calculate price
        total_price = 0.0
        price_per_night = 0.0
        
        for day in stay_dates:
            daily_supply = self.get_daily_supply(simulation_id, hotel_id, day)
            
            if supplier_type == SupplierType.HOTEL:
                price = daily_supply.hotel_price
            else:  # TRAVEL_AGENT
                agent = config.get_travel_agent_by_id(supplier_id)
                for allocation in daily_supply.travel_agent_allocations:
                    if allocation.supplier_id == supplier_id:
                        price = allocation.cost_basis + agent.operating_cost_per_room
                        price = price * (1 + agent.profit_margin)
                        break
            
            total_price += price
        
        price_per_night = total_price / len(stay_dates)
        
        # Decrement inventory for all days
        for day in stay_dates:
            daily_supply = self.get_daily_supply(simulation_id, hotel_id, day)
            
            if supplier_type == SupplierType.HOTEL:
                daily_supply.hotel_rooms_remaining -= 1
            else:  # TRAVEL_AGENT
                for allocation in daily_supply.travel_agent_allocations:
                    if allocation.supplier_id == supplier_id:
                        allocation.rooms_remaining -= 1
                        break
            
            # Update revenue
            daily_supply.bookings_count += 1
            daily_supply.total_revenue += price_per_night
            
            self._save_daily_supply(daily_supply)
        
        # Create booking record
        booking = Booking(
            simulation_id=simulation_id,
            user_id=user_id,
            trip_id=trip_id,
            supplier_id=supplier_id,
            supplier_type=supplier_type,
            booking_day=booking_day,
            stay_dates=stay_dates,
            price_per_night=price_per_night,
            total_price=total_price,
            hotel_id=hotel_id
        )
        
        # Save booking
        self._save_booking(booking)
        
        logger.info(f"Booking created: {user_id} booked {hotel_id} via {supplier_id} "
                   f"for days {stay_dates[0]}-{stay_dates[-1]} at ${price_per_night:.2f}/night")
        
        return booking
    
    def get_simulation_statistics(self, simulation_id: str, config: SimulationConfig) -> Dict:
        """
        Get comprehensive statistics for a simulation
        
        Args:
            simulation_id: Simulation identifier
            config: Simulation configuration
            
        Returns:
            Dictionary with statistics
        """
        bookings = list(self.bookings_collection.find({"simulation_id": simulation_id}))
        
        total_bookings = len(bookings)
        total_revenue = sum(b["total_price"] for b in bookings)
        
        # Calculate occupancy
        total_room_days = 0
        booked_room_days = 0
        
        for day in range(config.operational_start_day, config.operational_end_day + 1):
            for hotel in config.hotels:
                daily_supply = self.get_daily_supply(simulation_id, hotel.hotel_id, day)
                if daily_supply:
                    total_room_days += hotel.total_rooms
                    booked_room_days += (hotel.total_rooms - daily_supply.hotel_rooms_remaining)
                    
        occupancy_rate = (booked_room_days / total_room_days * 100) if total_room_days > 0 else 0
        
        # Bookings by supplier type
        hotel_bookings = sum(1 for b in bookings if b["supplier_type"] == SupplierType.HOTEL.value)
        agent_bookings = sum(1 for b in bookings if b["supplier_type"] == SupplierType.TRAVEL_AGENT.value)
        
        return {
            "total_bookings": total_bookings,
            "total_revenue": total_revenue,
            "total_room_days": total_room_days,
            "booked_room_days": booked_room_days,
            "occupancy_rate": occupancy_rate,
            "hotel_bookings": hotel_bookings,
            "travel_agent_bookings": agent_bookings,
            "avg_price_per_night": total_revenue / booked_room_days if booked_room_days > 0 else 0
        }
    
    def _save_daily_supply(self, daily_supply: DailySupply):
        """Save or update daily supply in MongoDB"""
        doc = self._daily_supply_to_doc(daily_supply)
        
        self.daily_supply_collection.update_one(
            {
                "simulation_id": daily_supply.simulation_id,
                "hotel_id": daily_supply.hotel_id,
                "day": daily_supply.day
            },
            {"$set": doc},
            upsert=True
        )
    
    def _save_booking(self, booking: Booking):
        """Save a booking to MongoDB"""
        doc = self._booking_to_doc(booking)
        self.bookings_collection.insert_one(doc)
    
    def _config_to_dict(self, config: SimulationConfig) -> Dict:
        """Convert SimulationConfig to dictionary for MongoDB"""
        return {
            "hotels": [
                {
                    "hotel_id": h.hotel_id,
                    "name": h.name,
                    "total_rooms": h.total_rooms,
                    "base_price": h.base_price,
                    "dynamic_pricing_config": h.dynamic_pricing_config
                }
                for h in config.hotels
            ],
            "travel_agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "operating_cost_per_room": a.operating_cost_per_room,
                    "profit_margin": a.profit_margin,
                    "allocation_schedule": a.allocation_schedule
                }
                for a in config.travel_agents
            ],
            "allocation_rules": config.allocation_rules
        }
    
    def _daily_supply_to_doc(self, daily_supply: DailySupply) -> Dict:
        """Convert DailySupply to MongoDB document"""
        return {
            "simulation_id": daily_supply.simulation_id,
            "hotel_id": daily_supply.hotel_id,
            "day": daily_supply.day,
            "hotel_rooms_total": daily_supply.hotel_rooms_total,
            "hotel_rooms_remaining": daily_supply.hotel_rooms_remaining,
            "hotel_price": daily_supply.hotel_price,
            "travel_agent_allocations": [
                {
                    "supplier_id": a.supplier_id,
                    "supplier_type": a.supplier_type.value,
                    "day": a.day,
                    "hotel_id": a.hotel_id,
                    "rooms_allocated": a.rooms_allocated,
                    "rooms_remaining": a.rooms_remaining,
                    "cost_basis": a.cost_basis
                }
                for a in daily_supply.travel_agent_allocations
            ],
            "bookings_count": daily_supply.bookings_count,
            "total_revenue": daily_supply.total_revenue,
            "updated_at": daily_supply.updated_at
        }
    
    def _doc_to_daily_supply(self, doc: Dict) -> DailySupply:
        """Convert MongoDB document to DailySupply"""
        allocations = [
            SupplyAllocation(
                supplier_id=a["supplier_id"],
                supplier_type=SupplierType(a["supplier_type"]),
                day=a["day"],
                hotel_id=a["hotel_id"],
                rooms_allocated=a["rooms_allocated"],
                rooms_remaining=a["rooms_remaining"],
                cost_basis=a["cost_basis"]
            )
            for a in doc.get("travel_agent_allocations", [])
        ]
        
        return DailySupply(
            simulation_id=doc["simulation_id"],
            hotel_id=doc["hotel_id"],
            day=doc["day"],
            hotel_rooms_total=doc["hotel_rooms_total"],
            hotel_rooms_remaining=doc["hotel_rooms_remaining"],
            hotel_price=doc["hotel_price"],
            travel_agent_allocations=allocations,
            bookings_count=doc.get("bookings_count", 0),
            total_revenue=doc.get("total_revenue", 0.0),
            updated_at=doc.get("updated_at", datetime.now())
        )
    
    def _booking_to_doc(self, booking: Booking) -> Dict:
        """Convert Booking to MongoDB document"""
        return {
            "simulation_id": booking.simulation_id,
            "user_id": booking.user_id,
            "trip_id": booking.trip_id,
            "supplier_id": booking.supplier_id,
            "supplier_type": booking.supplier_type.value,
            "booking_day": booking.booking_day,
            "stay_dates": booking.stay_dates,
            "price_per_night": booking.price_per_night,
            "total_price": booking.total_price,
            "hotel_id": booking.hotel_id,
            "created_at": booking.created_at
        }
    
    def cleanup_simulation(self, simulation_id: str):
        """Remove all data for a simulation"""
        self.daily_supply_collection.delete_many({"simulation_id": simulation_id})
        self.bookings_collection.delete_many({"simulation_id": simulation_id})
        self.simulations_collection.delete_one({"simulation_id": simulation_id})
        logger.info(f"Cleaned up simulation {simulation_id}")