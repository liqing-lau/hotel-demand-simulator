"""
Web interface for the Hotel Demand Simulator.
Allows viewing and managing simulation runs.
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import logging
from pathlib import Path
from simulator import HotelDemandSimulator
from datetime import datetime

# Configure logging to write to files
def setup_logging():
    """Setup logging to write to files in the logs folder with a new file per app restart."""
    # Create logs directory if it doesn't exist
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    # Generate timestamp for this app session
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = logs_dir / f'hotel_simulator_{timestamp}.log'

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # File handler - logs everything to file
            logging.FileHandler(log_filename, encoding='utf-8'),
            # Console handler - logs INFO and above to console
            logging.StreamHandler()
        ]
    )

    # Set console handler to INFO level (less verbose than file)
    console_handler = logging.getLogger().handlers[1]  # StreamHandler is second
    console_handler.setLevel(logging.INFO)

    return log_filename

# Setup logging and get the log file path
log_file_path = setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'simulations'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

logger.info("Flask app initialized")
logger.info(f"Simulations folder: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
logger.info(f"Logging to file: {log_file_path}")

# Global simulator instance
simulator = HotelDemandSimulator()


@app.route('/')
def index():
    """Main page showing available simulations."""
    logger.debug("API: Loading index page")

    simulations = []

    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.endswith('.json'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_stat = os.stat(filepath)
                simulations.append({
                    'name': filename,
                    'path': filepath,
                    'size': file_stat.st_size,
                    'modified': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })

    simulations.sort(key=lambda x: x['modified'], reverse=True)
    logger.debug(f"API: Found {len(simulations)} simulations")
    return render_template('index.html', simulations=simulations)


@app.route('/api/generate', methods=['POST'])
def generate_simulation():
    """Generate a new simulation."""
    try:
        data = request.json
        total_users = int(data.get('total_users', 100))
        proportion_casual = float(data.get('proportion_casual', 0.8))
        hotel_capacity = int(data.get('hotel_capacity', 50))

        logger.info(f"API: Generating simulation - users={total_users}, casual={proportion_casual*100:.1f}%, capacity={hotel_capacity}")

        # Generate demand
        simulator.generate_demand(total_users, proportion_casual, hotel_capacity)

        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"simulation_{timestamp}.json"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        simulator.save_run(filepath)

        logger.info(f"API: Simulation generated and saved as {filename}")

        return jsonify({
            'success': True,
            'filename': filename,
            'message': f'Simulation generated with {total_users} users'
        })
    except Exception as e:
        logger.error(f"API: Error generating simulation: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/load/<filename>', methods=['GET'])
def load_simulation(filename):
    """Load a simulation from file."""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        logger.info(f"API: Loading simulation {filename}")

        # Security check
        if not os.path.abspath(filepath).startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
            logger.warning(f"API: Security check failed for {filename}")
            return jsonify({'success': False, 'error': 'Invalid file path'}), 400

        if not os.path.exists(filepath):
            logger.warning(f"API: File not found: {filename}")
            return jsonify({'success': False, 'error': 'File not found'}), 404

        simulator.load_run(filepath)

        # Get summary statistics
        total_users = len(simulator.users)
        total_itineraries = sum(len(itineraries) for itineraries in simulator.users.values())
        total_demands = sum(
            len(itinerary.demands)
            for itineraries in simulator.users.values()
            for itinerary in itineraries
        )

        logger.info(f"API: Simulation loaded - {total_users} users, {total_demands} demands")

        return jsonify({
            'success': True,
            'parameters': simulator.simulation_parameters,
            'stats': {
                'total_users': total_users,
                'total_itineraries': total_itineraries,
                'total_demands': total_demands
            }
        })
    except Exception as e:
        logger.error(f"API: Error loading simulation {filename}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/simulation/<filename>/details', methods=['GET'])
def get_simulation_details(filename):
    """Get detailed information about a simulation."""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        logger.debug(f"API: Getting details for {filename}")

        # Security check
        if not os.path.abspath(filepath).startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
            logger.warning(f"API: Security check failed for details request on {filename}")
            return jsonify({'success': False, 'error': 'Invalid file path'}), 400

        if not os.path.exists(filepath):
            logger.warning(f"API: File not found for details: {filename}")
            return jsonify({'success': False, 'error': 'File not found'}), 404

        # Load the simulation to ensure we have the correct data
        temp_simulator = HotelDemandSimulator()
        temp_simulator.load_run(filepath)

        # Calculate statistics from the loaded simulator
        casual_users = sum(1 for user_id in temp_simulator.users.keys() if user_id.startswith('casual'))
        business_users = sum(1 for user_id in temp_simulator.users.keys() if user_id.startswith('business'))

        total_demands = sum(
            len(itinerary.demands)
            for itineraries in temp_simulator.users.values()
            for itinerary in itineraries
        )

        booked_count = sum(
            1 for itineraries in temp_simulator.users.values()
            for itinerary in itineraries
            if itinerary.is_booked
        )

        total_itineraries = sum(
            len(itineraries)
            for itineraries in temp_simulator.users.values()
        )

        logger.debug(f"API: Details retrieved - {casual_users} casual, {business_users} business, {booked_count} booked, {total_demands} demands")

        return jsonify({
            'success': True,
            'parameters': temp_simulator.simulation_parameters,
            'stats': {
                'casual_users': casual_users,
                'business_users': business_users,
                'total_demands': total_demands,
                'booked_itineraries': booked_count,
                'total_itineraries': total_itineraries
            }
        })
    except Exception as e:
        logger.error(f"API: Error getting details for {filename}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/simulation/<filename>/download', methods=['GET'])
def download_simulation(filename):
    """Download a simulation file."""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        logger.info(f"API: Downloading simulation {filename}")

        # Security check
        if not os.path.abspath(filepath).startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
            logger.warning(f"API: Security check failed for download of {filename}")
            return jsonify({'success': False, 'error': 'Invalid file path'}), 400

        if not os.path.exists(filepath):
            logger.warning(f"API: File not found for download: {filename}")
            return jsonify({'success': False, 'error': 'File not found'}), 404

        logger.info(f"API: Sending file {filename} for download")
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"API: Error downloading {filename}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/simulation/<filename>/delete', methods=['DELETE'])
def delete_simulation(filename):
    """Delete a simulation file."""
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        logger.info(f"API: Deleting simulation {filename}")

        # Security check
        if not os.path.abspath(filepath).startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
            logger.warning(f"API: Security check failed for delete of {filename}")
            return jsonify({'success': False, 'error': 'Invalid file path'}), 400

        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"API: Simulation {filename} deleted successfully")
        else:
            logger.warning(f"API: File not found for deletion: {filename}")

        return jsonify({'success': True, 'message': 'Simulation deleted'})
    except Exception as e:
        logger.error(f"API: Error deleting {filename}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/supplier')
def supplier_interface():
    """Supplier strategy testing interface."""
    logger.debug("API: Loading supplier interface")

    simulations = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.endswith('.json'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_stat = os.stat(filepath)
                simulations.append({
                    'name': filename,
                    'path': filepath,
                    'size': file_stat.st_size,
                    'modified': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })

    simulations.sort(key=lambda x: x['modified'], reverse=True)
    return render_template('supplier.html', simulations=simulations)


@app.route('/api/supplier/run', methods=['POST'])
def run_supplier_simulation():
    """Run a supplier strategy simulation."""
    try:
        data = request.json
        simulation_filename = data.get('simulation_filename')
        strategy = data.get('strategy')  # 'fixed' or 'availability'

        if strategy == 'fixed':
            price_per_night = float(data.get('price_per_night', 100))
            logger.info(f"API: Running supplier simulation with FIXED strategy - price=${price_per_night}")
        elif strategy == 'availability':
            min_price = float(data.get('min_price', 50))
            max_price = float(data.get('max_price', 200))
            logger.info(f"API: Running supplier simulation with AVAILABILITY strategy - min=${min_price}, max=${max_price}")
        else:
            return jsonify({'success': False, 'error': 'Invalid strategy'}), 400

        # Load the simulation
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], simulation_filename)

        # Security check
        if not os.path.abspath(filepath).startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
            logger.warning(f"API: Security check failed for supplier simulation")
            return jsonify({'success': False, 'error': 'Invalid file path'}), 400

        if not os.path.exists(filepath):
            logger.warning(f"API: Simulation file not found: {simulation_filename}")
            return jsonify({'success': False, 'error': 'Simulation file not found'}), 404

        # Create a fresh simulator instance for this run
        temp_simulator = HotelDemandSimulator()
        temp_simulator.load_run(filepath)

        # Run the supplier simulation
        metrics = _run_supplier_strategy(temp_simulator, strategy, data)

        logger.info(f"API: Supplier simulation completed - Revenue: ${metrics['total_revenue']:.2f}, Occupancy: {metrics['occupancy_rate']:.1f}%")

        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        logger.error(f"API: Error running supplier simulation: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


def _run_supplier_strategy(simulator, strategy, params):
    """
    Run a complete supplier strategy simulation from Day -20 to Day 99.

    Args:
        simulator: HotelDemandSimulator instance with loaded demand
        strategy: 'fixed' or 'availability'
        params: Dictionary with strategy parameters

    Returns:
        Dictionary with final metrics and day-level data
    """
    hotel_capacity = simulator.simulation_parameters['hotel_capacity_per_day']
    total_capacity = hotel_capacity * 100  # 100 days (0-99)

    # Track metrics
    total_revenue = 0
    total_booked_nights = 0
    total_demanded_nights = 0
    demand_lost_to_price = 0
    demand_lost_to_capacity = 0

    # Track rejection reasons per itinerary
    itinerary_rejections = {}  # (user_id, trip_id) -> 'price' | 'capacity' | 'both'

    # Day-level tracking
    day_metrics = {}  # day -> {occupancy, min_price, max_price, missed_demand}

    # First pass: count total demanded nights (one per itinerary, not per demand)
    for user_id, itineraries in simulator.users.items():
        for itinerary in itineraries:
            if itinerary.demands:  # Only count if itinerary has demands
                # All demands in an itinerary represent the same stay, so count once
                demand = itinerary.demands[0]
                stay_start = demand.stay_start_date
                stay_end = demand.stay_end_date
                num_nights = stay_end - stay_start + 1
                total_demanded_nights += num_nights

    # Run simulation day by day
    for simulation_day in range(-20, 100):
        # Generate daily prices based on strategy
        if strategy == 'fixed':
            price_per_night = float(params.get('price_per_night', 100))
            daily_prices = {str(day): price_per_night for day in range(0, 100)}
        else:  # availability
            min_price = float(params.get('min_price', 50))
            max_price = float(params.get('max_price', 200))
            daily_prices = {}

            for day in range(0, 100):
                rooms_available = simulator.hotel_capacity.get(day, 0)
                # Linear interpolation: price = min + (max - min) * (capacity_used / total_capacity)
                capacity_used = hotel_capacity - rooms_available
                price = min_price + (max_price - min_price) * (capacity_used / hotel_capacity)
                daily_prices[str(day)] = price

        # Process demand for this day and track rejections
        bookings = simulator.process_daily_prices(simulation_day, daily_prices)

        # Track revenue from bookings
        for booking in bookings:
            stay_start = booking['stay_dates']['start_date']
            stay_end = booking['stay_dates']['end_date']
            num_nights = stay_end - stay_start + 1
            total_revenue += booking['booked_price_per_night'] * num_nights
            total_booked_nights += num_nights

        # Track rejection reasons for unbooked itineraries that had demands today
        for user_id, itineraries in simulator.users.items():
            for itinerary in itineraries:
                if not itinerary.is_booked:
                    # Check if this itinerary had demands for today
                    matching_demands = [d for d in itinerary.demands if d.shopping_date == simulation_day]
                    if matching_demands:
                        demand = matching_demands[0]
                        itinerary_key = (user_id, itinerary.trip_id)

                        # Calculate average price for the stay
                        stay_dates = range(demand.stay_start_date, demand.stay_end_date + 1)
                        prices_for_stay = []
                        for date in stay_dates:
                            price = daily_prices.get(str(date), float('inf'))
                            prices_for_stay.append(price)
                        avg_price = sum(prices_for_stay) / len(prices_for_stay) if prices_for_stay else float('inf')

                        # Check rejection reasons
                        price_acceptable = avg_price <= demand.max_price_per_night
                        capacity_available = all(
                            simulator.hotel_capacity.get(date, 0) > 0
                            for date in stay_dates
                        )

                        # Record rejection reason (only if not already recorded)
                        if itinerary_key not in itinerary_rejections:
                            if not price_acceptable and not capacity_available:
                                itinerary_rejections[itinerary_key] = 'both'
                            elif not price_acceptable:
                                itinerary_rejections[itinerary_key] = 'price'
                            elif not capacity_available:
                                itinerary_rejections[itinerary_key] = 'capacity'

    # Track missed demands with details
    missed_demands_list = []

    # Calculate day-level metrics
    for day in range(0, 100):
        rooms_booked = hotel_capacity - simulator.hotel_capacity.get(day, 0)
        occupancy = (rooms_booked / hotel_capacity * 100) if hotel_capacity > 0 else 0

        # Get price range for this day
        if strategy == 'fixed':
            price_per_night = float(params.get('price_per_night', 100))
            min_price_day = price_per_night
            max_price_day = price_per_night
        else:
            min_price = float(params.get('min_price', 50))
            max_price = float(params.get('max_price', 200))
            rooms_available = simulator.hotel_capacity.get(day, 0)
            capacity_used = hotel_capacity - rooms_available
            price = min_price + (max_price - min_price) * (capacity_used / hotel_capacity)
            min_price_day = min_price
            max_price_day = max_price

        # Count missed demand for this day and collect details
        missed_demand = 0
        for user_id, itineraries in simulator.users.items():
            for itinerary in itineraries:
                if not itinerary.is_booked:
                    for demand in itinerary.demands:
                        if demand.shopping_date == day:
                            missed_demand += 1


                            break

        day_metrics[day] = {
            'occupancy': occupancy,
            'min_price': min_price_day,
            'max_price': max_price_day,
            'missed_demand': missed_demand,
            'rooms_booked': rooms_booked
        }

    # Build aggregated missed demands per itinerary (one row per itinerary)
    missed_demands_list = []
    for user_id, itineraries in simulator.users.items():
        for itinerary in itineraries:
            if not itinerary.is_booked and itinerary.demands:
                user_type = 'Casual' if user_id.startswith('casual') else 'Business'
                shopping_start = min(d.shopping_date for d in itinerary.demands)
                shopping_end = max(d.shopping_date for d in itinerary.demands)
                stay_start = itinerary.demands[0].stay_start_date
                stay_end = itinerary.demands[0].stay_end_date
                num_nights = stay_end - stay_start + 1
                price_min = min(d.max_price_per_night for d in itinerary.demands)
                price_max = max(d.max_price_per_night for d in itinerary.demands)

                missed_demands_list.append({
                    'user_id': user_id,
                    'user_type': user_type,
                    'shopping_start': shopping_start,
                    'shopping_end': shopping_end,
                    'stay_start': stay_start,
                    'stay_end': stay_end,
                    'num_nights': num_nights,
                    'price_min': price_min,
                    'price_max': price_max
                })
    # Calculate unmet demand using tracked rejection reasons
    for user_id, itineraries in simulator.users.items():
        for itinerary in itineraries:
            if not itinerary.is_booked and itinerary.demands:
                itinerary_key = (user_id, itinerary.trip_id)
                rejection_reason = itinerary_rejections.get(itinerary_key, 'price')  # Default to price if not tracked

                if rejection_reason == 'price':
                    demand_lost_to_price += 1
                elif rejection_reason == 'capacity':
                    demand_lost_to_capacity += 1
                elif rejection_reason == 'both':
                    # If both price and capacity were issues, prioritize capacity
                    # (since capacity is a harder constraint)
                    demand_lost_to_capacity += 1

    # Calculate final metrics
    occupancy_rate = (total_booked_nights / total_capacity * 100) if total_capacity > 0 else 0
    revpar = total_revenue / total_capacity if total_capacity > 0 else 0
    adr = total_revenue / total_booked_nights if total_booked_nights > 0 else 0

    return {
        'total_available_room_days': total_capacity,
        'total_demanded_room_days': total_demanded_nights,
        'total_booked_room_days': total_booked_nights,
        'occupancy_rate': occupancy_rate,
        'total_revenue': total_revenue,
        'demand_lost_to_price': demand_lost_to_price,
        'demand_lost_to_capacity': demand_lost_to_capacity,
        'revpar': revpar,
        'adr': adr,
        'day_metrics': day_metrics,
        'missed_demands': missed_demands_list
    }


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Starting Hotel Demand Simulator Web Interface")
    logger.info("=" * 60)
    logger.info(f"Server running on http://127.0.0.1:5000")
    logger.info(f"Simulations folder: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    logger.info("Press CTRL+C to stop the server")
    logger.info("=" * 60)
    app.run(debug=True, port=5000)

