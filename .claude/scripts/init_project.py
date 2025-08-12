#!/usr/bin/env python
"""Initialize a new computational biology project."""

import os
import argparse
from pathlib import Path
import json
from datetime import datetime

def create_project_structure(project_name):
    """Create the standard project directory structure."""
    
    base_path = Path(project_name)
    
    # Define directory structure
    directories = [
        "data/raw",
        "data/processed",
        "data/external",
        "notebooks/exploratory",
        "notebooks/reports",
        "src/data",
        "src/features",
        "src/models",
        "src/visualization",
        "results/figures",
        "results/models",
        "results/reports",
        "tests",
        "config",
        "docs",
    ]
    
    # Create directories
    for dir_path in directories:
        (base_path / dir_path).mkdir(parents=True, exist_ok=True)
        
        # Add README to each directory
        readme_path = base_path / dir_path / "README.md"
        with open(readme_path, 'w') as f:
            f.write(f"# {dir_path}\n\n")
            f.write(get_directory_description(dir_path))
    
    # Create initial config file
    config = {
        "project_name": project_name,
        "created_date": datetime.now().isoformat(),
        "version": "0.1.0",
        "author": "",
        "description": "",
    }
    
    with open(base_path / "config" / "project_config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Project '{project_name}' initialized successfully!")
    print(f"📁 Project structure created at: {base_path.absolute()}")

def get_directory_description(dir_path):
    """Get description for each directory."""
    descriptions = {
        "data/raw": "Store raw, immutable data here. Never modify these files directly.",
        "data/processed": "Store cleaned and processed data ready for analysis.",
        "data/external": "Data from external sources (databases, APIs, etc.).",
        "notebooks/exploratory": "Jupyter notebooks for exploration and prototyping.",
        "notebooks/reports": "Polished notebooks for presenting results.",
        "src/data": "Scripts for downloading and processing data.",
        "src/features": "Scripts for feature engineering.",
        "src/models": "Scripts for training and evaluating models.",
        "src/visualization": "Scripts for creating visualizations.",
        "results/figures": "Generated plots and figures.",
        "results/models": "Trained model files and checkpoints.",
        "results/reports": "Generated analysis reports.",
        "tests": "Unit tests and integration tests.",
        "config": "Configuration files for the project.",
        "docs": "Project documentation.",
    }
    return descriptions.get(dir_path, "")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize a new project")
    parser.add_argument("--name", required=True, help="Project name")
    args = parser.parse_args()
    
    create_project_structure(args.name)