"""
MongoDB Models for Hotel Simulation
Defines data structures for hotels, travel agents, and supply tracking.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class SupplierType(Enum):
    """Types of suppliers in the system"""
    HOTEL = "hotel"
    TRAVEL_AGENT = "travel_agent"


class PricingStrategy(Enum):
    """Pricing strategies available"""
    DYNAMIC = "dynamic"  # Hotels - price based on lead time
    FIXED = "fixed"      # Travel agents - cost + markup


@dataclass
class Hotel:
    """Represents a hotel with its properties"""
    hotel_id: str
    name: str
    total_rooms: int
    base_price: float  # Base price per night
    dynamic_pricing_config: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        # Default dynamic pricing configuration
        if not self.dynamic_pricing_config:
            self.dynamic_pricing_config = {
                "lead_time_0_7": 1.5,      # 150% of base (0-7 days before)
                "lead_time_8_14": 1.3,     # 130% of base (8-14 days before)
                "lead_time_15_30": 1.1,    # 110% of base (15-30 days before)
                "lead_time_31_plus": 1.0   # 100% of base (31+ days before)
            }


@dataclass
class TravelAgent:
    """Represents a travel agent with their inventory"""
    agent_id: str
    name: str
    operating_cost_per_room: float  # Operating cost per room
    profit_margin: float  # Profit margin percentage (e.g., 0.15 for 15%)
    allocation_schedule: List[int] = field(default_factory=list)  # Days when allocation happens
    
    def __post_init__(self):
        # Default allocation schedule: every 25 days starting from day -20
        if not self.allocation_schedule:
            self.allocation_schedule = list(range(-20, 100, 25))


@dataclass
class SupplyAllocation:
    """Tracks room allocation per supplier per day"""
    supplier_id: str
    supplier_type: SupplierType
    day: int
    hotel_id: str  # Which hotel the rooms come from
    rooms_allocated: int
    rooms_remaining: int
    cost_basis: float  # Cost per room for this allocation
    

@dataclass
class DailySupply:
    """Represents the supply state for a specific day and hotel"""
    simulation_id: str
    hotel_id: str
    day: int
    
    # Direct hotel supply
    hotel_rooms_total: int
    hotel_rooms_remaining: int
    hotel_price: float
    
    # Travel agent supplies (list of allocations)
    travel_agent_allocations: List[SupplyAllocation] = field(default_factory=list)
    
    # Bookings made
    bookings_count: int = 0
    total_revenue: float = 0.0
    
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Booking:
    """Represents a completed booking"""
    simulation_id: str
    user_id: str
    trip_id: int
    supplier_id: str
    supplier_type: SupplierType
    
    booking_day: int  # Day when booking was made
    stay_dates: List[int]
    price_per_night: float
    total_price: float
    
    hotel_id: str  # Actual hotel booked
    
    created_at: datetime = field(default_factory=datetime.now)


class SimulationConfig:
    """Configuration for a simulation run"""
    def __init__(self):
        # Hotels configuration
        self.hotels = [
            Hotel(
                hotel_id="boutique_hotel",
                name="Boutique Hotel",
                total_rooms=20,
                base_price=150.0
            ),
            Hotel(
                hotel_id="large_hotel",
                name="Large Hotel",
                total_rooms=80,
                base_price=120.0
            )
        ]
        
        # Travel agents configuration
        self.travel_agents = [
            TravelAgent(
                agent_id="travel_agent_1",
                name="Premium Travel Co.",
                operating_cost_per_room=10.0,
                profit_margin=0.15  # 15% markup
            )
        ]
        
        # Allocation rules (rooms per allocation per hotel)
        self.allocation_rules = {
            "travel_agent_1": {
                "boutique_hotel": 5,   # Gets 5 rooms from boutique
                "large_hotel": 20      # Gets 20 rooms from large
            }
        }
        
        # Simulation period
        self.simulation_start_day = -20
        self.simulation_end_day = 99
        self.operational_start_day = 0
        self.operational_end_day = 99
    
    def get_total_hotel_capacity(self) -> int:
        """Get total capacity across all hotels"""
        return sum(h.total_rooms for h in self.hotels)
    
    def get_hotel_by_id(self, hotel_id: str) -> Optional[Hotel]:
        """Get a hotel by its ID"""
        for hotel in self.hotels:
            if hotel.hotel_id == hotel_id:
                return hotel
        return None
    
    def get_travel_agent_by_id(self, agent_id: str) -> Optional[TravelAgent]:
        """Get a travel agent by ID"""
        for agent in self.travel_agents:
            if agent.agent_id == agent_id:
                return agent
        return None