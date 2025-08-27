# Claude Code Hooks for Bioinformatics Workflows

This directory contains Claude Code hooks specifically designed to prevent common errors in bioinformatics pipelines, particularly Snakemake workflows.


## Overview

These hooks provide proactive error detection and validation for:
- Snakemake workflow files (`.smk`)
- Configuration files (`config*.yaml`)
- Sample sheets (`*sample*sheet*.tsv`)

## Implemented Hooks

### 1. Pre-commit Snakemake Validation (`pre_edit`)
- **Purpose**: Validates Snakemake syntax before saving changes
- **Triggers on**: `*.smk` files
- **What it does**:
  - Runs `snakemake --lint` to check for syntax errors
  - Validates rule naming conventions
  - Prevents saving files with syntax errors that would fail at runtime

### 2. Post-edit Config Validation (`post_edit`)
- **Purpose**: Ensures configuration parameters are valid
- **Triggers on**: `*config*.yaml` files
- **What it does**:
  - Validates YAML syntax
  - Checks parameter ranges (e.g., effect_size_threshold must be 0-1)
  - Warns about potentially problematic values
  - Verifies file paths exist

### 3. Pre-read Sample Sheet Validation (`pre_read`)
- **Purpose**: Catches sample sheet issues before they cause pipeline failures
- **Triggers on**: `*sample*sheet*.tsv` files
- **What it does**:
  - Detects missing values (NaN)
  - Checks for duplicate sample names
  - Validates file paths
  - Ensures consistent column counts
  - Reports patient/sample statistics

## Usage

These hooks are automatically activated when Claude Code operates on matching files. No manual intervention required.

## Example Output

### Sample Sheet Validation:
```
✓ Detected tab-delimited file
✓ Loaded sample sheet with 45 samples and 4 columns
✓ Detected patient-specific DMR pipeline format

Sample sheet validation ERRORS:
  ❌ Column 'sample' has 1 missing values at rows: [44]

Sample sheet validation warnings:
  ⚠️  Row 15: path file exists as .gz: /path/to/file.bedMethyl.gz
```

### Config Validation:
```
Config validation warnings:
  ⚠️  effect_size_threshold of 0.8 is quite high, typical values are 0.1-0.3
  ⚠️  min_coverage of 3 is very low, consider using at least 5-10

✅ Config validation passed
```

## Customization

To add new validations, edit the Python scripts in the `scripts/` directory:
- `validate_config_params.py` - Add new parameter checks
- `check_sample_sheet.py` - Add new sample sheet validations

## Benefits

Based on today's work, these hooks would have:
1. Caught the NaN error in the sample sheet immediately
2. Prevented the effect_size > 1.0 configuration error
3. Warned about column name mismatches before runtime
4. Saved multiple debugging cycles

## Installation

These hooks are already configured in this directory. Claude Code will automatically use them when working with matching files.

## References to creation of claude md file
- https://github.com/kn1026/cc/blob/main/claudecode.md
- And many more on twitter
