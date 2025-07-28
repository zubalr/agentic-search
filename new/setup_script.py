#!/usr/bin/env python3
"""
Setup script for the Agentic Search LLM Judge System.
Helps with initial configuration and validation.
"""

import os
import sys
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def create_directories():
    """Create necessary directories."""
    directories = ["data", "raw", "output", "logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}/")

def setup_env_file():
    """Create .env file from .env.example if it doesn't exist."""
    if not Path(".env").exists():
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file from .env.example")
            print("⚠️  Please edit .env file with your API keys")
        else:
            print("⚠️  .env.example not found, creating basic .env file")
            with open(".env", "w") as f:
                f.write("# Add your API keys here\n")
                f.write("CEREBRAS_API_KEY=your_key_here\n")
                f.write("GROQ_API_KEY=your_key_here\n")
                f.write("GOOGLE_PLACES_API_KEY=your_key_here\n")
            print("⚠️  Please edit .env file with your API keys")
    else:
        print("✅ .env file already exists")

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        "requests",
        "langchain_core", 
        "langchain_cerebras",
        "langchain_groq"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r config/requirements.txt")
        return False
    
    return True

def validate_structure():
    """Validate the project structure."""
    required_files = [
        "src/utils/config.py",
        "src/core/api_client.py",
        "scripts/main.py"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            return False
    
    return True

def show_next_steps():
    """Show next steps to the user."""
    print("\n🎉 Setup Complete! Next steps:")
    print("\n1. Configure API keys:")
    print("   Edit .env file with your actual API keys")
    print("\n2. Test the system:")
    print("   python3 example.py")
    print("\n3. Run the complete workflow:")
    print("   python3 scripts/main.py process")
    print("   python3 scripts/main.py fetch --source both")
    print("   python3 scripts/main.py evaluate --evaluator llm_judge")
    print("\n4. Get help:")
    print("   python3 scripts/main.py --help")

def main():
    """Main setup function."""
    print("🚀 Agentic Search LLM Judge System - Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    print("\n📁 Creating directories...")
    create_directories()
    
    # Setup .env file
    print("\n⚙️  Setting up environment...")
    setup_env_file()
    
    # Validate structure
    print("\n🏗️  Validating project structure...")
    if not validate_structure():
        print("❌ Project structure validation failed")
        sys.exit(1)
    
    # Check dependencies
    print("\n📦 Checking dependencies...")
    dependencies_ok = check_dependencies()
    
    if dependencies_ok:
        print("\n✅ All dependencies satisfied")
    else:
        print("\n⚠️  Some dependencies are missing")
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    main()
