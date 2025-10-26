"""
Web interface for the Hotel Demand Simulator.
Allows viewing and managing simulation runs with multi-hotel support.
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import logging
from pathlib import Path
from simulator import HotelDemandSimulator
from datetime import datetime
from utils.models import SimulationConfig

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
        
        # Get custom configuration if provided
        config_data = data.get('config')
        
        logger.info(f"API: Generating simulation - users={total_users}, casual={proportion_casual*100:.1f}%")
        
        # Create simulator with custom config if provided
        sim = HotelDemandSimulator()
        
        # Apply custom configuration if provided
        if config_data:
            if 'hotels' in config_data:
                for i, hotel_data in enumerate(config_data['hotels']):
                    if i < len(sim.config.hotels):
                        if 'base_price' in hotel_data:
                            sim.config.hotels[i].base_price = float(hotel_data['base_price'])
                        if 'dynamic_pricing_config' in hotel_data:
                            sim.config.hotels[i].dynamic_pricing_config = hotel_data['dynamic_pricing_config']
            
            if 'travel_agents' in config_data:
                for i, agent_data in enumerate(config_data['travel_agents']):
                    if i < len(sim.config.travel_agents):
                        if 'operating_cost_per_room' in agent_data:
                            sim.config.travel_agents[i].operating_cost_per_room = float(agent_data['operating_cost_per_room'])
                        if 'profit_margin' in agent_data:
                            sim.config.travel_agents[i].profit_margin = float(agent_data['profit_margin'])
            
            if 'allocation_rules' in config_data:
                sim.config.allocation_rules = config_data['allocation_rules']
        
        # Generate demand
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        simulation_id = f"simulation_{timestamp}"
        
        sim.generate_demand(total_users, proportion_casual, simulation_id)

        # Save to file
        filename = f"{simulation_id}.json"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        sim.save_run(filepath)

        logger.info(f"API: Simulation generated and saved as {filename}")

        return jsonify({
            'success': True,
            'filename': filename,
            'simulation_id': simulation_id,
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

        # Load the simulation
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Calculate statistics
        casual_users = sum(1 for user_id in data['users'].keys() if user_id.startswith('casual'))
        business_users = sum(1 for user_id in data['users'].keys() if user_id.startswith('business'))
        
        total_demands = sum(
            len(itinerary['demands'])
            for user_data in data['users'].values()
            for itinerary in user_data
        )

        return jsonify({
            'success': True,
            'parameters': data['simulation_parameters'],
            'stats': {
                'casual_users': casual_users,
                'business_users': business_users,
                'total_users': casual_users + business_users,
                'total_demands': total_demands
            }
        })
    except Exception as e:
        logger.error(f"API: Error getting simulation details: {str(e)}", exc_info=True)
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
def supplier():
    """Supplier strategy tester page."""
    logger.debug("API: Loading supplier page")
    
    simulations = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.endswith('.json'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_stat = os.stat(filepath)
                simulations.append({
                    'name': filename,
                    'modified': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    simulations.sort(key=lambda x: x['modified'], reverse=True)
    
    # Get default configuration
    config = SimulationConfig()
    
    return render_template('supplier.html', 
                         simulations=simulations,
                         config=config)


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current simulation configuration."""
    try:
        config = SimulationConfig()
        
        return jsonify({
            'success': True,
            'config': {
                'hotels': [
                    {
                        'hotel_id': h.hotel_id,
                        'name': h.name,
                        'total_rooms': h.total_rooms,
                        'base_price': h.base_price,
                        'dynamic_pricing_config': h.dynamic_pricing_config
                    }
                    for h in config.hotels
                ],
                'travel_agents': [
                    {
                        'agent_id': a.agent_id,
                        'name': a.name,
                        'operating_cost_per_room': a.operating_cost_per_room,
                        'profit_margin': a.profit_margin,
                        'allocation_schedule': a.allocation_schedule
                    }
                    for a in config.travel_agents
                ],
                'allocation_rules': config.allocation_rules
            }
        })
    except Exception as e:
        logger.error(f"API: Error getting config: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/supplier/run', methods=['POST'])
def run_supplier_simulation():
    """Run a simulation with the refactored multi-supplier system."""
    try:
        data = request.json
        simulation_filename = data.get('simulation_filename')
        config_data = data.get('config', {})
        
        if not simulation_filename:
            return jsonify({'success': False, 'error': 'No simulation file specified'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], simulation_filename)
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Simulation file not found'}), 404
        
        logger.info(f"API: Running supplier simulation with {simulation_filename}")
        
        # Create new simulator instance
        sim = HotelDemandSimulator()
        
        # Apply custom configuration
        if 'hotels' in config_data:
            for i, hotel_data in enumerate(config_data['hotels']):
                if i < len(sim.config.hotels):
                    if 'base_price' in hotel_data:
                        sim.config.hotels[i].base_price = float(hotel_data['base_price'])
                    if 'dynamic_pricing_config' in hotel_data:
                        sim.config.hotels[i].dynamic_pricing_config = hotel_data['dynamic_pricing_config']
        
        if 'travel_agents' in config_data:
            for i, agent_data in enumerate(config_data['travel_agents']):
                if i < len(sim.config.travel_agents):
                    if 'operating_cost_per_room' in agent_data:
                        sim.config.travel_agents[i].operating_cost_per_room = float(agent_data['operating_cost_per_room'])
                    if 'profit_margin' in agent_data:
                        sim.config.travel_agents[i].profit_margin = float(agent_data['profit_margin'])
        
        if 'allocation_rules' in config_data:
            sim.config.allocation_rules = config_data['allocation_rules']
        
        # Load the demand data
        sim.load_run(filepath)
        
        # Re-initialize supply with potentially updated configuration
        sim.supply_manager.cleanup_simulation(sim.simulation_id)
        sim.supply_manager.initialize_simulation(sim.simulation_id, sim.config)
        
        # Run the full simulation
        stats = sim.run_full_simulation()
        
        logger.info(f"API: Simulation complete - {stats['total_bookings']} bookings, "
                   f"${stats['total_revenue']:.2f} revenue")
        
        return jsonify({
            'success': True,
            'metrics': stats
        })
        
    except Exception as e:
        logger.error(f"API: Error running supplier simulation: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Starting Hotel Demand Simulator Web Interface (Refactored)")
    logger.info("=" * 60)
    logger.info(f"Server running on http://127.0.0.1:5000")
    logger.info(f"Simulations folder: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    logger.info("Press CTRL+C to stop the server")
    logger.info("=" * 60)
    app.run(debug=True, port=5000)