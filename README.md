# Hotel Demand Simulator

A hotel booking demand simulator that generates synthetic customer demand patterns to test hotel pricing strategies. The simulator models two distinct user personas (Casual and Business Travellers) with different booking behaviors and price sensitivities.

## Overview

This simulator generates a "year" of hotel booking demand (100 simulated days) with customer behavior patterns. The simulator can be used to test different pricing strategies and understand their impact on revenue, occupancy, and customer behavior.

### Key Concepts

- **Two User Personas**: Casual Travellers (2 trips/year) and Business Travellers (5 trips/year)
- **Shopping Windows**: Customers shop for hotels within a certain window before their trip
-- This adds a "bitemporal" complication to the data
- **Dynamic Pricing**: Customers have varying willingness-to-pay based on booking timing
- **Simple Web Interface**: View, manage, and analyze simulation runs
- **JSON-based Storage**: Easy to save, load, and analyze simulation data

## Installation

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd hotel-demand-simulator
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
   - **Windows**: `.\venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start - Web Interface

1. Run setup and start Flask web server:
```bash
python setup.py
python app.py
```

2. Open your browser and navigate to `http://127.0.0.1:5000/`

3. Generate a new simulation by setting:
   - Total Users (e.g., 100)
   - Casual Traveller Proportion (e.g., 80%)
   - Hotel Capacity per Day (e.g., 50 rooms)

4. View, download, or delete existing simulations

### Programmatic Usage

```python
from simulator import HotelDemandSimulator

# Create simulator
simulator = HotelDemandSimulator()

# Generate demand
simulator.generate_demand(
    total_users=100,
    proportion_casual=0.8,
    hotel_capacity=50
)

# Save simulation
simulator.save_run('simulations/my_simulation.json')

# Load simulation
simulator.load_run('simulations/my_simulation.json')

# Process daily prices and get bookings
daily_prices = {str(day): 100 + day * 0.5 for day in range(100)}
bookings = simulator.process_daily_prices(
    simulation_day=-10,
    daily_prices=daily_prices
)

print(f"Bookings made: {len(bookings)}")
```

See `example_usage.py` for a complete example.

## Data Structures

### Demand
Represents a single user shopping for a hotel on a specific day.

```python
@dataclass
class Demand:
    shopping_date: int              # Day user is shopping (e.g., -15)
    stay_start_date: int            # Start of intended stay
    stay_end_date: int              # End of intended stay
    max_price_per_night: float      # Max price willing to pay
```

In hindsight could possible "refactor" stay_start_date and stay_end_date into a single "stay_dates" as a separate part of itinerary
Actual shopping price determined on creation by interpolation between stay_start_date and stay_end_date for casual traveller and fixed price for business traveller

### Itinerary
A collection of Demand objects for one trip by a single user.

```python
@dataclass
class Itinerary:
    user_id: str                    # User identifier
    trip_id: int                    # Trip number for this user
    demands: List[Demand]           # All shopping days for this trip
    is_booked: bool                 # Whether trip was booked
    booked_price_per_night: float   # Price paid if booked
```

## User Personas

### Casual Traveller
- **Trips per Year**: 2
- **Trip Length**: Normal(8, 2) days
- **Shopping Window**: starts 50-20 days before trip, ends 15-5 days before
- **Price Logic**: Dynamic pricing with linear interpolation
  - Base max price: Normal(μ=110, σ=20)
  - Min price: 70-90% of max price
  - Willingness to pay increases as stay date approaches (mimicking increased desperation for a spot)

### Business Traveller
- **Trips per Year**: 5 (1 long + 4 short)
- **Trip Length**:
  - Long trip: Normal(20, 5) days
  - Short trips: Normal(5, 1) days
- **Shopping Window**: 7-3 days before trip
- **Price Logic**: Fixed high willingness-to-pay
  - Max price: Normal(150, 10)
  - Constant for entire shopping window

## API Reference

### HotelDemandSimulator

#### `generate_demand(total_users, proportion_casual, hotel_capacity)`
Generates a complete simulation run with all users and itineraries.

**Parameters:**
- `total_users` (int): Total number of users to simulate
- `proportion_casual` (float): Proportion of casual travellers (0.0-1.0)
- `hotel_capacity` (int): Number of available rooms per day

#### `save_run(filepath)`
Saves the generated demand to a JSON file.

**Parameters:**
- `filepath` (str): Path where to save the JSON file

#### `load_run(filepath)`
Loads a previously saved demand run from JSON.

**Parameters:**
- `filepath` (str): Path to the JSON file to load

#### `process_daily_prices(simulation_day, daily_prices)`
Processes daily prices and generates bookings for the given day.

**Parameters:**
- `simulation_day` (int): Current simulated day
- `daily_prices` (dict): Mapping of stay dates (as strings) to prices

**Returns:**
List of successful bookings with structure:
```json
[
  {
    "user_id": "casual-042",
    "booked_price_per_night": 115.75,
    "stay_dates": {"start_date": 25, "end_date": 33}
  }
]
```

## JSON File Format

Simulations are saved in the following JSON structure:

```json
{
  "simulation_parameters": {
    "total_users": 100,
    "proportion_casual": 0.8,
    "hotel_capacity_per_day": 50
  },
  "users": {
    "casual-001": [
      {
        "trip_id": 0,
        "demands": [
          {
            "shopping_date": -15,
            "stay_start_date": 5,
            "stay_end_date": 12,
            "max_price_per_night": 120.5
          }
        ],
        "is_booked": false,
        "booked_price_per_night": null
      }
    ]
  }
}
```

## Testing

Run the test suite:

```
python -m unittest test_simulator -v
```

## Day-based simulation
1. GET API should accept a particular supplier-scenario ID - respond with current status of supplier-scenario
  a. no such supplier-scenario exists
  b. supplier-scenario exists, with the next expected shopping day
2. POST API should accept a particular supplier-scenario ID and a request input of the next shopping day's prices


The prices input should be in the following format:
the "prices" object is a dictionary of
day numbers: hotel prices/availabilities

Note that there is also a "travel_platform", which represents the price/availability that the travel platform itself is offering. 

```json
{
  "prices": {
    "0": {
      "hotel_a": {
        "price": 100,
        "capacity": 50
      },
      "hotel_b": {
        "price": 90,
        "capacity": 20
      },
      "travel_platform": {
        "price": 85,
        "capacity": 30
      }
    },
    "1": {
      "hotel_a": {
        "price": 100,
        "capacity": 50
      },
      "hotel_b": {
        "price": 90,
        "capacity": 20
      },
      "travel_platform": {
        "price": 85,
        "capacity": 30
      }
    }
  }
}
```

## Web UI Features

- main page to generate simulations
- /supplier page to test supplier strategies

## Project Structure

```
hotel-demand-simulator/
├── simulator.py           # Core simulator class
├── app.py                 # Flask web application
├── test_simulator.py      # Unit tests
├── example_usage.py       # Usage example
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Web interface
└── simulations/          # Saved simulation files
```

## Requirements

- Flask 3.0.0
- Werkzeug 3.0.1
- Python 3.8+

## License

Apache License 2.0 - See LICENSE file for details

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass: `python -m unittest test_simulator -v`
2. Code follows the existing style
3. New features include tests

## Future Enhancements

- Allowing for iterative end-point based simulation - for more complex pricing strategies that use previous day's shopping information for next day's prices. 
