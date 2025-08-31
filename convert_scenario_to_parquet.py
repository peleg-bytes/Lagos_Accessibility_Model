#!/usr/bin/env python3
"""
Convert scenario Excel files to Parquet format for faster uploads
This script helps users convert their scenario files to Parquet for better performance.
"""

import pandas as pd
import time
from pathlib import Path
import argparse
import sys

def convert_scenario_file(input_path: str, output_path: str = None):
    """Convert a scenario Excel file to Parquet format."""
    
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file {input_path} not found!")
        return False
    
    if output_path is None:
        output_path = str(input_file.with_suffix('.parquet'))
    
    print(f"Converting: {input_path}")
    print(f"Output: {output_path}")
    
    start_time = time.time()
    
    try:
        # Read Excel file
        print("Reading Excel file...")
        df = pd.read_excel(
            input_path,
            usecols=[0, 1, 2],
            engine='openpyxl',
            dtype={2: str}  # Handle "--" values
        )
        df.columns = ["origin_node", "destination_node", "travel_time"]
        
        print(f"Loaded {len(df):,} rows")
        
        # Clean data
        print("Cleaning data...")
        mask = df["travel_time"] != "--"
        df = df[mask].copy()
        df["travel_time"] = pd.to_numeric(df["travel_time"], errors="coerce")
        df = df.dropna(subset=["travel_time"])
        
        # Optimize data types
        df["origin_node"] = df["origin_node"].astype("int32")
        df["destination_node"] = df["destination_node"].astype("int32")
        df["travel_time"] = df["travel_time"].astype("float32")
        
        print(f"Cleaned to {len(df):,} rows")
        
        # Save as Parquet
        print("Saving as Parquet...")
        df.to_parquet(
            output_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Get file sizes
        excel_size = input_file.stat().st_size / (1024 * 1024)  # MB
        parquet_size = Path(output_path).stat().st_size / (1024 * 1024)  # MB
        
        end_time = time.time()
        
        print("\n" + "="*50)
        print("CONVERSION SUCCESSFUL!")
        print("="*50)
        print(f"Excel file:    {excel_size:.1f} MB")
        print(f"Parquet file:  {parquet_size:.1f} MB")
        print(f"Size reduction: {(1 - parquet_size/excel_size)*100:.1f}%")
        print(f"Conversion time: {end_time - start_time:.1f} seconds")
        print(f"Rows: {len(df):,}")
        
        # Test loading speed
        print("\nTesting loading speeds...")
        
        # Excel
        start = time.time()
        pd.read_excel(input_path, usecols=[0, 1, 2])
        excel_time = time.time() - start
        
        # Parquet
        start = time.time()
        pd.read_parquet(output_path)
        parquet_time = time.time() - start
        
        speedup = excel_time / parquet_time if parquet_time > 0 else 0
        
        print(f"Excel loading: {excel_time:.2f} seconds")
        print(f"Parquet loading: {parquet_time:.2f} seconds")
        print(f"Speedup: {speedup:.1f}x faster!")
        
        print(f"\nYour optimized scenario file is ready: {output_path}")
        print("Upload this .parquet file to your dashboard for much faster loading!")
        
        return True
        
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Convert scenario Excel files to Parquet format",
        epilog="Example: python convert_scenario_to_parquet.py my_scenario.xlsx"
    )
    parser.add_argument("input_file", help="Input Excel file path")
    parser.add_argument("-o", "--output", help="Output Parquet file path (optional)")
    
    args = parser.parse_args()
    
    print("Scenario File Converter - Excel to Parquet")
    print("="*45)
    
    success = convert_scenario_file(args.input_file, args.output)
    
    if success:
        print("\nBenefits of using Parquet files:")
        print("• Much faster upload and processing")
        print("• Smaller file sizes (typically 70-80% reduction)")
        print("• Better data integrity and type preservation")
        print("• Faster analysis and comparison in the dashboard")
    else:
        print("\nConversion failed. Please check your input file.")
        sys.exit(1)

if __name__ == "__main__":
    main()
