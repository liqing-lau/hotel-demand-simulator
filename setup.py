"""
Web Interface Setup Script

This script sets up the complete web interface with all necessary files.
"""

import os
import shutil
import sys

def create_directory_structure():
    """Create necessary directories"""
    directories = ['templates', 'simulations', 'logs']
    
    print("Creating directory structure...")
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"  ✓ Created {directory}/")
        else:
            print(f"  ✓ {directory}/ already exists")
    print()

def check_dependencies():
    """Check if required Python modules are installed"""
    print("Checking dependencies...")
    
    required_modules = ['flask', 'pymongo']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module} installed")
        except ImportError:
            print(f"  ✗ {module} NOT installed")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n  ⚠ Missing modules: {', '.join(missing_modules)}")
        print("  Run: pip install -r requirements.txt")
    
    print()
    return len(missing_modules) == 0


def check_mongodb():
    """Check if MongoDB is accessible"""
    print("Checking MongoDB...")
    
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.server_info()
        print("  ✓ MongoDB is running and accessible")
        print()
        return True
    except Exception as e:
        print(f"  ✗ MongoDB not accessible: {e}")
        print("\n  To start MongoDB:")
        print("    macOS: brew services start mongodb-community")
        print("    Ubuntu: sudo systemctl start mongodb")
        print("    Docker: docker run -d -p 27017:27017 mongo")
        print()
        return False


def create_run_script():
    """Create a simple run script"""
    print("Creating run script...")
    
    run_script = """#!/usr/bin/env python3
\"\"\"
Quick start script for the hotel simulation web interface
\"\"\"

import os
import sys

# Check if MongoDB is running
try:
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    client.server_info()
except Exception as e:
    print("Error: MongoDB is not running!")
    print("\\nPlease start MongoDB first:")
    print("  macOS: brew services start mongodb-community")
    print("  Ubuntu: sudo systemctl start mongodb")
    print("  Docker: docker run -d -p 27017:27017 mongo")
    sys.exit(1)

# Check if app file exists
if not os.path.exists('app_refactored.py'):
    print("Error: app_refactored.py not found!")
    print("Make sure you're in the correct directory.")
    sys.exit(1)

print("=" * 60)
print("Starting Hotel Simulation Web Interface")
print("=" * 60)
print("\\n Server will start at: http://127.0.0.1:5000")
print("\\n Main page: http://127.0.0.1:5000/")
print("Supplier config: http://127.0.0.1:5000/supplier")
print("\\nPress CTRL+C to stop the server")
print("=" * 60)
print()

# Run the Flask app
os.system('python app_refactored.py')
"""
    
    with open('run_web.py', 'w') as f:
        f.write(run_script)
    
    # Make it executable on Unix-like systems
    try:
        os.chmod('run_web.py', 0o755)
    except:
        pass
    
    print("  ✓ Created run_web.py")
    print()


def print_next_steps():
    """Print next steps for the user"""
    print("=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print()
    print("1. Make sure MongoDB is running:")
    print("   brew services start mongodb-community  # macOS")
    print("   sudo systemctl start mongodb           # Ubuntu")
    print()
    print("2. Start the web server:")
    print("   python run_web.py")
    print("   OR")
    print("   python app_refactored.py")
    print()
    print("3. Open your browser:")
    print("   Main page:     http://127.0.0.1:5000/")
    print("   Supplier page: http://127.0.0.1:5000/supplier")
    print()
    print("4. Generate a simulation and test different configurations!")
    print()
    print("=" * 60)


def main():
    """Main setup process"""
    print()
    print("=" * 60)
    print("Hotel Simulation Web Interface - Setup")
    print("=" * 60)
    print()
    
    # Create directories
    create_directory_structure()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check MongoDB
    mongodb_ok = check_mongodb()
    
    # Create run script
    create_run_script()
    
    # Print next steps
    print_next_steps()
    
    # Summary
    if deps_ok and mongodb_ok:
        print(" Everything is ready! Run 'python app.py' to start.")
    elif not deps_ok:
        print("Install dependencies first: pip install -r requirements.txt")
    elif not mongodb_ok:
        print("Start MongoDB first, then run 'python run_web.py'")
    
    print()


if __name__ == "__main__":
    main()