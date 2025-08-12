#!/usr/bin/env python
"""
Advanced genome build consistency checker that integrates with your database config.
"""

import re
import yaml
import sys
import os
from pathlib import Path

def load_database_config():
    """Load the central database configuration."""
    db_config_path = "/data1/greenbab/users/ahunos/apps/llm_configs/databases_config.yaml"
    if os.path.exists(db_config_path):
        with open(db_config_path, 'r') as f:
            return yaml.safe_load(f)
    return None

def extract_genome_build_from_path(path, db_config):
    """Intelligently extract genome build from file path using database config."""
    # First check against known paths in database config
    if db_config and 'reference_genomes' in db_config:
        for location in ['local', 'remote']:
            if location in db_config['reference_genomes']:
                for build, resources in db_config['reference_genomes'][location].items():
                    if isinstance(resources, dict):
                        for resource_type, resource_path in resources.items():
                            if resource_path and str(resource_path) in str(path):
                                return build
    
    # Fallback to pattern matching
    # Common patterns in paths
    patterns = [
        (r'/GRCh37[-_]?lite/', 'GRCh37'),
        (r'/human_GRCh37/', 'GRCh37'),
        (r'/hg19/', 'hg19'),  # Note: hg19 ≈ GRCh37
        (r'/GRCh38/', 'GRCh38'),
        (r'/hg38/', 'hg38'),  # Note: hg38 ≈ GRCh38
        (r'/mm10/', 'mm10'),
        (r'/mm39/', 'mm39'),
        (r'/t2t[-_]?CHM13/', 'CHM13'),
    ]
    
    for pattern, build in patterns:
        if re.search(pattern, path, re.I):
            return build
    
    # Extract from filename
    filename_patterns = [
        (r'(GRCh37|GRCh38|hg19|hg38|mm10|mm39|CHM13)', None)
    ]
    
    for pattern, _ in filename_patterns:
        match = re.search(pattern, Path(path).name, re.I)
        if match:
            return match.group(1)
    
    return None

def normalize_build_name(build):
    """Normalize genome build names to handle equivalencies."""
    equivalencies = {
        'hg19': 'GRCh37',
        'hg38': 'GRCh38',
        'grch37': 'GRCh37',
        'grch38': 'GRCh38',
    }
    normalized = build.lower()
    return equivalencies.get(normalized, build)

def check_config_file(config_path):
    """Check a config file for genome build consistency."""
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Try to parse as YAML to get structured data
    try:
        config_data = yaml.safe_load(content)
    except:
        config_data = None
    
    db_config = load_database_config()
    
    # Find all file paths in the config
    path_pattern = r'(/data[^\s:\"\']+|s3://[^\s:\"\']+)'
    paths = re.findall(path_pattern, content)
    
    # Extract genome builds
    build_info = {}
    for path in paths:
        build = extract_genome_build_from_path(path, db_config)
        if build:
            normalized = normalize_build_name(build)
            if normalized not in build_info:
                build_info[normalized] = []
            build_info[normalized].append({
                'path': path,
                'original_build': build,
                'line': next((i+1 for i, line in enumerate(content.split('\n')) 
                             if path in line), None)
            })
    
    # Check for inconsistencies
    if len(build_info) > 1:
        print("⚠️  Multiple genome builds detected in config!")
        print(f"   Found builds: {', '.join(build_info.keys())}")
        print("\n   This will likely cause coordinate mismatches and incorrect results!")
        print("\n   Details:")
        
        for build, occurrences in build_info.items():
            print(f"\n   {build} ({len(occurrences)} files):")
            for occ in occurrences[:3]:  # Show first 3 examples
                print(f"     Line {occ['line']}: {Path(occ['path']).name}")
            if len(occurrences) > 3:
                print(f"     ... and {len(occurrences)-3} more")
        
        # Suggest fixes
        most_common = max(build_info.keys(), key=lambda k: len(build_info[k]))
        print(f"\n   Suggestion: Standardize on {most_common} (most common in this config)")
        
        # Check if resources exist for other builds
        if db_config:
            print("\n   Available in your database config:")
            for build in build_info.keys():
                if build in db_config['reference_genomes']['local']:
                    print(f"     ✓ {build} resources available locally")
                else:
                    print(f"     ✗ {build} resources NOT in database config")
        
        return False
    
    elif len(build_info) == 1:
        build = list(build_info.keys())[0]
        print(f"✓ Consistent genome build detected: {build}")
        return True
    
    else:
        print("ℹ️  No genome build references detected in config")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: check_genome_consistency.py <config_file>")
        sys.exit(1)
    
    success = check_config_file(sys.argv[1])
    sys.exit(0 if success else 1)