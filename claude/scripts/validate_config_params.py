#!/usr/bin/env python
"""
Validate config parameters for bioinformatics pipelines.
Ensures parameters are within expected ranges and types.
"""

import sys
import yaml
import os

def validate_dmr_config(config):
    """Validate DMR pipeline specific parameters."""
    warnings = []
    errors = []
    
    # Check effect size threshold
    if 'effect_size_threshold' in config:
        threshold = config['effect_size_threshold']
        if not isinstance(threshold, (int, float)):
            errors.append(f"effect_size_threshold must be numeric, got {type(threshold).__name__}")
        elif threshold < 0 or threshold > 1:
            errors.append(f"effect_size_threshold must be between 0 and 1, got {threshold}")
        elif threshold > 0.5:
            warnings.append(f"effect_size_threshold of {threshold} is quite high, typical values are 0.1-0.3")
    
    # Check Cohen's h threshold
    if 'cohen_h_threshold' in config:
        threshold = config['cohen_h_threshold']
        if not isinstance(threshold, (int, float)):
            errors.append(f"cohen_h_threshold must be numeric, got {type(threshold).__name__}")
        elif threshold < 0:
            errors.append(f"cohen_h_threshold must be positive, got {threshold}")
    
    # Check minimum coverage
    if 'min_coverage' in config:
        min_cov = config['min_coverage']
        if not isinstance(min_cov, int):
            errors.append(f"min_coverage must be an integer, got {type(min_cov).__name__}")
        elif min_cov < 1:
            errors.append(f"min_coverage must be at least 1, got {min_cov}")
        elif min_cov < 5:
            warnings.append(f"min_coverage of {min_cov} is very low, consider using at least 5-10")
    
    # Check threads
    if 'threads' in config:
        threads = config['threads']
        if not isinstance(threads, int):
            errors.append(f"threads must be an integer, got {type(threads).__name__}")
        elif threads < 1:
            errors.append(f"threads must be at least 1, got {threads}")
    
    # Check file paths exist
    path_fields = ['samples_sheet', 'reference', 'genome_sizes', 'modkit_container']
    for field in path_fields:
        if field in config and config[field]:
            path = config[field]
            if not os.path.exists(path):
                warnings.append(f"{field}: Path does not exist: {path}")
    
    return errors, warnings

def validate_general_config(config):
    """General config validation applicable to any pipeline."""
    warnings = []
    errors = []
    
    # Check for required fields based on common patterns
    if 'samples_sheet' in config and not config.get('samples_sheet'):
        errors.append("samples_sheet is defined but empty")
    
    if 'outdir' in config:
        outdir = config['outdir']
        if not isinstance(outdir, str):
            errors.append(f"outdir must be a string, got {type(outdir).__name__}")
    
    return errors, warnings

def main(config_file):
    """Main validation function."""
    if not os.path.exists(config_file):
        print(f"Error: Config file not found: {config_file}")
        return 1
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML syntax: {e}")
        return 1
    except Exception as e:
        print(f"Error reading config file: {e}")
        return 1
    
    if config is None:
        print("Warning: Config file is empty")
        return 0
    
    errors = []
    warnings = []
    
    # Run general validation
    gen_errors, gen_warnings = validate_general_config(config)
    errors.extend(gen_errors)
    warnings.extend(gen_warnings)
    
    # Run specific validation based on config content
    if any(key in config for key in ['effect_size_threshold', 'cohen_h_threshold', 'min_dmr_sites']):
        dmr_errors, dmr_warnings = validate_dmr_config(config)
        errors.extend(dmr_errors)
        warnings.extend(dmr_warnings)
    
    # Report results
    if errors:
        print("Config validation ERRORS:")
        for error in errors:
            print(f"  ❌ {error}")
    
    if warnings:
        print("Config validation warnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    
    if not errors and not warnings:
        print("✅ Config validation passed")
    
    return 1 if errors else 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: validate_config_params.py <config_file>")
        sys.exit(1)
    
    sys.exit(main(sys.argv[1]))