#!/usr/bin/env python
"""
Validate sample sheets for bioinformatics pipelines.
Checks for common issues like missing values, duplicates, and format problems.
"""

import sys
import pandas as pd
import os
import re

def check_required_columns(df, required_cols):
    """Check if all required columns are present."""
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return f"Missing required columns: {', '.join(missing_cols)}"
    return None

def check_missing_values(df, critical_cols):
    """Check for missing values in critical columns."""
    errors = []
    for col in critical_cols:
        if col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                missing_rows = df[df[col].isna()].index.tolist()
                errors.append(f"Column '{col}' has {missing_count} missing values at rows: {missing_rows}")
    return errors

def check_file_paths(df, path_columns):
    """Check if file paths exist and have correct extensions."""
    warnings = []
    for col in path_columns:
        if col in df.columns:
            for idx, path in df[col].items():
                if pd.notna(path):
                    if not os.path.exists(path):
                        # Check if it's a .gz file that's referenced without extension
                        if os.path.exists(f"{path}.gz"):
                            warnings.append(f"Row {idx}: {col} file exists as .gz: {path}.gz")
                        else:
                            warnings.append(f"Row {idx}: {col} file not found: {path}")
    return warnings

def check_sample_names(df):
    """Check for issues with sample names."""
    errors = []
    warnings = []
    
    if 'sample' in df.columns:
        # Check for duplicates
        duplicates = df[df['sample'].duplicated()]['sample'].tolist()
        if duplicates:
            errors.append(f"Duplicate sample names found: {', '.join(set(duplicates))}")
        
        # Check for invalid characters
        for idx, sample in df['sample'].items():
            if pd.notna(sample):
                if not re.match(r'^[a-zA-Z0-9_\-\.]+$', str(sample)):
                    warnings.append(f"Row {idx}: Sample name contains special characters: {sample}")
                if len(str(sample)) > 50:
                    warnings.append(f"Row {idx}: Sample name is very long (>50 chars): {sample}")
    
    return errors, warnings

def check_conditions(df):
    """Check condition/group assignments."""
    warnings = []
    
    if 'condition' in df.columns:
        conditions = df['condition'].value_counts()
        
        # Warn about single-sample conditions
        single_sample_conditions = conditions[conditions == 1].index.tolist()
        if single_sample_conditions:
            warnings.append(f"Conditions with only one sample: {', '.join(single_sample_conditions)}")
        
        # Check for standard condition names
        if 'Normal' in conditions.index and 'Tumor' in conditions.index:
            print("✓ Found standard Tumor/Normal conditions")
    
    return warnings

def check_patient_assignments(df):
    """Check patient assignments for paired analyses."""
    info = []
    
    if 'patient' in df.columns:
        patient_counts = df.groupby('patient').size()
        
        # Report single-sample patients
        single_sample_patients = patient_counts[patient_counts == 1].index.tolist()
        if single_sample_patients:
            info.append(f"Patients with only one sample: {len(single_sample_patients)}")
        
        # Report multi-sample patients
        multi_sample_patients = patient_counts[patient_counts > 1].index.tolist()
        if multi_sample_patients:
            info.append(f"Patients with multiple samples: {len(multi_sample_patients)}")
            
            # Check if they have both tumor and normal
            if 'condition' in df.columns:
                for patient in multi_sample_patients:
                    patient_df = df[df['patient'] == patient]
                    conditions = patient_df['condition'].unique()
                    if 'Normal' not in conditions:
                        info.append(f"  Patient {patient} has no Normal sample")
                    if 'Tumor' not in conditions:
                        info.append(f"  Patient {patient} has no Tumor sample")
    
    return info

def main(sample_sheet):
    """Main validation function."""
    if not os.path.exists(sample_sheet):
        print(f"Error: Sample sheet not found: {sample_sheet}")
        return 1
    
    # Detect delimiter
    with open(sample_sheet, 'r') as f:
        first_line = f.readline()
        if '\t' in first_line:
            sep = '\t'
            print("✓ Detected tab-delimited file")
        elif ',' in first_line:
            sep = ','
            print("✓ Detected comma-delimited file")
        else:
            print("Error: Cannot detect delimiter (should be tab or comma)")
            return 1
    
    try:
        df = pd.read_csv(sample_sheet, sep=sep)
        print(f"✓ Loaded sample sheet with {len(df)} samples and {len(df.columns)} columns")
    except Exception as e:
        print(f"Error reading sample sheet: {e}")
        return 1
    
    errors = []
    warnings = []
    info = []
    
    # Define expected columns based on common patterns
    if {'patient', 'sample', 'condition', 'path'}.issubset(df.columns):
        # Patient-specific DMR pipeline format
        print("✓ Detected patient-specific DMR pipeline format")
        required_cols = ['patient', 'sample', 'condition', 'path']
        critical_cols = ['patient', 'sample', 'condition', 'path']
        path_cols = ['path']
    else:
        # Generic format
        required_cols = []
        critical_cols = [col for col in df.columns if 'sample' in col.lower() or 'name' in col.lower()]
        path_cols = [col for col in df.columns if 'path' in col.lower() or 'file' in col.lower()]
    
    # Run checks
    col_error = check_required_columns(df, required_cols)
    if col_error:
        errors.append(col_error)
    
    errors.extend(check_missing_values(df, critical_cols))
    warnings.extend(check_file_paths(df, path_cols))
    
    name_errors, name_warnings = check_sample_names(df)
    errors.extend(name_errors)
    warnings.extend(name_warnings)
    
    warnings.extend(check_conditions(df))
    info.extend(check_patient_assignments(df))
    
    # Report results
    if errors:
        print("\nSample sheet validation ERRORS:")
        for error in errors:
            print(f"  ❌ {error}")
    
    if warnings:
        print("\nSample sheet validation warnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    
    if info:
        print("\nSample sheet information:")
        for item in info:
            print(f"  ℹ️  {item}")
    
    if not errors:
        print("\n✅ Sample sheet validation passed (with {} warnings)".format(len(warnings)))
    
    return 1 if errors else 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: check_sample_sheet.py <sample_sheet>")
        sys.exit(1)
    
    sys.exit(main(sys.argv[1]))