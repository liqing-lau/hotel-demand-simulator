"""
Pricing Engine
Handles dynamic pricing for hotels and fixed pricing for travel agents.
"""

import logging
from typing import Dict, List
from .models import Hotel, TravelAgent, SimulationConfig, PricingStrategy, SupplierType

logger = logging.getLogger(__name__)


class PricingEngine:
    """Handles pricing calculations for hotels and travel agents"""
    
    def __init__(self, config: SimulationConfig):
        """
        Initialize pricing engine
        
        Args:
            config: Simulation configuration
        """
        self.config = config
    
    def calculate_hotel_price(self, hotel: Hotel, current_day: int, stay_day: int) -> float:
        """
        Calculate dynamic hotel price based on lead time
        
        Args:
            hotel: Hotel object
            current_day: Current day (when booking is made)
            stay_day: Day of the stay
            
        Returns:
            Price for the room on that day
        """
        lead_time = stay_day - current_day
        
        # Determine pricing multiplier based on lead time
        if lead_time <= 7:
            multiplier = hotel.dynamic_pricing_config.get("lead_time_0_7", 1.5)
        elif lead_time <= 14:
            multiplier = hotel.dynamic_pricing_config.get("lead_time_8_14", 1.3)
        elif lead_time <= 30:
            multiplier = hotel.dynamic_pricing_config.get("lead_time_15_30", 1.1)
        else:
            multiplier = hotel.dynamic_pricing_config.get("lead_time_31_plus", 1.0)
        
        price = hotel.base_price * multiplier
        
        logger.debug(f"Hotel {hotel.hotel_id}: base=${hotel.base_price:.2f}, "
                    f"lead_time={lead_time}, multiplier={multiplier:.2f}, "
                    f"price=${price:.2f}")
        
        return price
    
    def calculate_travel_agent_price(self, agent: TravelAgent, hotel_cost: float) -> float:
        """
        Calculate fixed travel agent price
        
        Args:
            agent: TravelAgent object
            hotel_cost: Cost basis from hotel
            
        Returns:
            Price the travel agent will charge
        """
        # Add operating cost
        price = hotel_cost + agent.operating_cost_per_room
        
        # Add profit margin
        price = price * (1 + agent.profit_margin)
        
        logger.debug(f"Travel agent {agent.agent_id}: cost=${hotel_cost:.2f}, "
                    f"operating=${agent.operating_cost_per_room:.2f}, "
                    f"margin={agent.profit_margin:.2%}, price=${price:.2f}")
        
        return price
    
    def get_best_offer(self, simulation_id: str, current_day: int, 
                       stay_dates: List[int], max_price_per_night: float,
                       supply_manager) -> Dict:
        """
        Find the best available offer for a given stay
        
        Args:
            simulation_id: Simulation identifier
            current_day: Current day (when shopping)
            stay_dates: List of days for the stay
            max_price_per_night: Maximum price user is willing to pay per night
            supply_manager: SupplyManager instance
            
        Returns:
            Dict with best offer details, or None if no suitable offer found
        """
        best_offer = None
        best_avg_price = float('inf')
        
        # Check each hotel
        for hotel in self.config.hotels:
            # Check direct hotel booking
            offer = self._evaluate_hotel_offer(
                simulation_id, hotel, current_day, stay_dates, 
                max_price_per_night, supply_manager
            )
            
            if offer and offer['avg_price'] < best_avg_price:
                best_offer = offer
                best_avg_price = offer['avg_price']
            
            # Check travel agent offers for this hotel
            for agent in self.config.travel_agents:
                offer = self._evaluate_travel_agent_offer(
                    simulation_id, agent, hotel, current_day, stay_dates,
                    max_price_per_night, supply_manager
                )
                
                if offer and offer['avg_price'] < best_avg_price:
                    best_offer = offer
                    best_avg_price = offer['avg_price']
        
        return best_offer
    
    def _evaluate_hotel_offer(self, simulation_id: str, hotel: Hotel,
                              current_day: int, stay_dates: List[int],
                              max_price_per_night: float, supply_manager) -> Dict:
        """
        Evaluate a direct hotel booking offer
        
        Returns:
            Offer dict if valid, None otherwise
        """
        total_price = 0.0
        
        # Check availability and calculate price for all days
        for stay_day in stay_dates:
            daily_supply = supply_manager.get_daily_supply(
                simulation_id, hotel.hotel_id, stay_day
            )
            
            if not daily_supply or daily_supply.hotel_rooms_remaining <= 0:
                return None  # Not available
            
            # Calculate dynamic price
            price = self.calculate_hotel_price(hotel, current_day, stay_day)
            total_price += price
        
        avg_price = total_price / len(stay_dates)
        
        # Check if price is acceptable
        if avg_price > max_price_per_night:
            return None
        
        return {
            'supplier_id': hotel.hotel_id,
            'supplier_type': SupplierType.HOTEL,
            'hotel_id': hotel.hotel_id,
            'avg_price': avg_price,
            'total_price': total_price,
            'available': True
        }
    
    def _evaluate_travel_agent_offer(self, simulation_id: str, agent: TravelAgent,
                                     hotel: Hotel, current_day: int, 
                                     stay_dates: List[int], max_price_per_night: float,
                                     supply_manager) -> Dict:
        """
        Evaluate a travel agent booking offer
        
        Returns:
            Offer dict if valid, None otherwise
        """
        total_price = 0.0
        
        # Check availability for all days
        for stay_day in stay_dates:
            daily_supply = supply_manager.get_daily_supply(
                simulation_id, hotel.hotel_id, stay_day
            )
            
            if not daily_supply:
                return None
            
            # Find this agent's allocation
            agent_allocation = None
            for allocation in daily_supply.travel_agent_allocations:
                if allocation.supplier_id == agent.agent_id:
                    agent_allocation = allocation
                    break
            
            if not agent_allocation or agent_allocation.rooms_remaining <= 0:
                return None  # Not available
            
            # Calculate fixed price based on cost basis
            price = self.calculate_travel_agent_price(agent, agent_allocation.cost_basis)
            total_price += price
        
        avg_price = total_price / len(stay_dates)
        
        # Check if price is acceptable
        if avg_price > max_price_per_night:
            return None
        
        return {
            'supplier_id': agent.agent_id,
            'supplier_type': SupplierType.TRAVEL_AGENT,
            'hotel_id': hotel.hotel_id,
            'avg_price': avg_price,
            'total_price': total_price,
            'available': True
        }
    
    def update_hotel_prices(self, simulation_id: str, current_day: int, 
                           supply_manager):
        """
        Update all hotel prices based on current day (dynamic pricing)
        
        Args:
            simulation_id: Simulation identifier
            current_day: Current day
            supply_manager: SupplyManager instance
        """
        for hotel in self.config.hotels:
            for day in range(current_day, self.config.operational_end_day + 1):
                daily_supply = supply_manager.get_daily_supply(
                    simulation_id, hotel.hotel_id, day
                )
                
                if daily_supply:
                    # Calculate new price
                    new_price = self.calculate_hotel_price(hotel, current_day, day)
                    daily_supply.hotel_price = new_price
                    
                    # Update in database
                    supply_manager._save_daily_supply(daily_supply)
        
        logger.debug(f"Updated hotel prices for day {current_day}")
    
    def get_pricing_summary(self, simulation_id: str, day: int, supply_manager) -> Dict:
        """
        Get a summary of all prices for a given day
        
        Args:
            simulation_id: Simulation identifier
            day: Day to get prices for
            supply_manager: SupplyManager instance
            
        Returns:
            Dictionary with pricing summary
        """
        summary = {
            'day': day,
            'hotels': [],
            'travel_agents': []
        }
        
        for hotel in self.config.hotels:
            daily_supply = supply_manager.get_daily_supply(simulation_id, hotel.hotel_id, day)
            if daily_supply:
                summary['hotels'].append({
                    'hotel_id': hotel.hotel_id,
                    'name': hotel.name,
                    'price': daily_supply.hotel_price,
                    'rooms_available': daily_supply.hotel_rooms_remaining
                })
                
                # Add travel agent prices for this hotel
                for allocation in daily_supply.travel_agent_allocations:
                    agent = self.config.get_travel_agent_by_id(allocation.supplier_id)
                    if agent:
                        price = self.calculate_travel_agent_price(agent, allocation.cost_basis)
                        summary['travel_agents'].append({
                            'agent_id': agent.agent_id,
                            'name': agent.name,
                            'hotel_id': hotel.hotel_id,
                            'price': price,
                            'rooms_available': allocation.rooms_remaining
                        })
        
        return summary