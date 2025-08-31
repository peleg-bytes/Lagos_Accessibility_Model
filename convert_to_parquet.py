#!/usr/bin/env python3
"""
Convert Base Scenario Excel file to Parquet format for faster loading
This script converts the large Excel file to a much faster Parquet format.
"""

import pandas as pd
import numpy as np
import time
from pathlib import Path
import argparse

def convert_excel_to_parquet(
    excel_path: str = "Data/Base Scenario.xlsx",
    parquet_path: str = "Data/Base Scenario.parquet",
    chunk_size: int = 50000
):
    """Convert Excel file to Parquet with optimization."""
    
    print("Converting Base Scenario from Excel to Parquet...")
    start_time = time.time()
    
    # Check if input file exists
    if not Path(excel_path).exists():
        print(f"Error: {excel_path} not found!")
        return False
    
    try:
        # Read Excel file with optimizations
        print("Reading Excel file...")
        df = pd.read_excel(
            excel_path,
            usecols=[0, 1, 2],  # Only first 3 columns
            engine='openpyxl',
            dtype={
                0: 'int32',  # origin_node
                1: 'int32',  # destination_node  
                2: str       # travel_time (handle "--" values)
            }
        )
        
        # Set column names
        df.columns = ["origin_node", "destination_node", "travel_time"]
        
        print(f"Loaded {len(df):,} rows")
        
        # Clean data
        print("Cleaning data...")
        
        # Remove "--" values and convert to numeric
        mask = df["travel_time"] != "--"
        df = df[mask].copy()
        df["travel_time"] = pd.to_numeric(df["travel_time"], errors="coerce")
        df = df.dropna(subset=["travel_time"])
        
        # Optimize data types
        df["origin_node"] = df["origin_node"].astype("int32")
        df["destination_node"] = df["destination_node"].astype("int32")
        df["travel_time"] = df["travel_time"].astype("float32")  # float32 is sufficient for travel times
        
        print(f"Cleaned to {len(df):,} rows")
        
        # Save as Parquet
        print("Saving as Parquet...")
        df.to_parquet(
            parquet_path,
            engine='pyarrow',
            compression='snappy',  # Fast compression
            index=False
        )
        
        # Verify the conversion
        print("Verifying conversion...")
        df_test = pd.read_parquet(parquet_path)
        
        # Get file sizes
        excel_size = Path(excel_path).stat().st_size / (1024 * 1024)  # MB
        parquet_size = Path(parquet_path).stat().st_size / (1024 * 1024)  # MB
        
        end_time = time.time()
        
        print("\n" + "="*50)
        print("CONVERSION SUCCESSFUL!")
        print("="*50)
        print(f"Excel file:    {excel_size:.1f} MB")
        print(f"Parquet file:  {parquet_size:.1f} MB")
        print(f"Size reduction: {(1 - parquet_size/excel_size)*100:.1f}%")
        print(f"Conversion time: {end_time - start_time:.1f} seconds")
        print(f"Rows: {len(df_test):,}")
        print(f"Columns: {list(df_test.columns)}")
        print("\nTo use the new format, update your config.yaml:")
        print(f"   base_scenario: \"{parquet_path}\"")
        
        return True
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False

def test_loading_speed(excel_path: str, parquet_path: str):
    """Compare loading speeds between Excel and Parquet."""
    print("\nSPEED TEST")
    print("="*30)
    
    # Test Excel loading
    if Path(excel_path).exists():
        print("Testing Excel loading...")
        start = time.time()
        df_excel = pd.read_excel(excel_path, usecols=[0, 1, 2])
        excel_time = time.time() - start
        print(f"Excel loading: {excel_time:.2f} seconds")
    else:
        excel_time = None
        print("Excel file not found for comparison")
    
    # Test Parquet loading
    if Path(parquet_path).exists():
        print("Testing Parquet loading...")
        start = time.time()
        df_parquet = pd.read_parquet(parquet_path)
        parquet_time = time.time() - start
        print(f"Parquet loading: {parquet_time:.2f} seconds")
        
        if excel_time:
            speedup = excel_time / parquet_time
            print(f"Speedup: {speedup:.1f}x faster!")
    else:
        print("Parquet file not found")

def main():
    parser = argparse.ArgumentParser(description="Convert Excel Base Scenario to Parquet format")
    parser.add_argument("--input", default="Data/Base Scenario.xlsx", help="Input Excel file path")
    parser.add_argument("--output", default="Data/Base Scenario.parquet", help="Output Parquet file path")
    parser.add_argument("--test-speed", action="store_true", help="Test loading speed comparison")
    
    args = parser.parse_args()
    
    # Convert file
    success = convert_excel_to_parquet(args.input, args.output)
    
    if success and args.test_speed:
        test_loading_speed(args.input, args.output)
    
    if success:
        print("\nReady to update your dashboard!")
        print("Next steps:")
        print("1. Update config.yaml to use the new Parquet file")
        print("2. Install pyarrow if not already installed: pip install pyarrow")
        print("3. Restart your dashboard to see the speed improvement")

if __name__ == "__main__":
    main()
