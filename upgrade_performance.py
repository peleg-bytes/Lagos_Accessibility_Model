#!/usr/bin/env python3
"""
Performance Upgrade Script for Lagos Accessibility Dashboard
This script helps upgrade your dashboard for maximum performance.
"""

import subprocess
import sys
from pathlib import Path
import pandas as pd
import time

def check_pyarrow():
    """Check if pyarrow is installed."""
    try:
        import pyarrow
        print("✅ PyArrow is installed")
        return True
    except ImportError:
        print("❌ PyArrow not found")
        return False

def install_pyarrow():
    """Install pyarrow for Parquet support."""
    print("📦 Installing PyArrow for Parquet support...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyarrow>=12.0.0"])
        print("✅ PyArrow installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install PyArrow")
        return False

def convert_base_scenario():
    """Convert Base Scenario to Parquet if needed."""
    excel_path = Path("Data/Base Scenario.xlsx")
    parquet_path = Path("Data/Base Scenario.parquet")
    
    if not excel_path.exists():
        print(f"⚠️  Excel file not found: {excel_path}")
        return False
    
    if parquet_path.exists():
        print("✅ Parquet file already exists")
        return True
    
    print("🔄 Converting Excel to Parquet...")
    try:
        # Use the conversion script
        result = subprocess.run([
            sys.executable, "convert_to_parquet.py", 
            "--input", str(excel_path),
            "--output", str(parquet_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Conversion successful!")
            return True
        else:
            print(f"❌ Conversion failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return False

def update_config():
    """Update config.yaml to use Parquet file."""
    config_path = Path("config.yaml")
    parquet_path = "data/Base Scenario.parquet"
    
    if not config_path.exists():
        print("⚠️  config.yaml not found")
        return False
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Check if already using parquet
        if "Base Scenario.parquet" in content:
            print("✅ Config already uses Parquet format")
            return True
        
        # Update to use parquet
        if "Base Scenario.xlsx" in content:
            new_content = content.replace(
                "data/Base Scenario.xlsx", 
                parquet_path
            )
            
            # Backup original
            backup_path = config_path.with_suffix('.yaml.backup')
            if not backup_path.exists():
                with open(backup_path, 'w') as f:
                    f.write(content)
                print(f"📋 Backup created: {backup_path}")
            
            # Write updated config
            with open(config_path, 'w') as f:
                f.write(new_content)
            
            print("✅ Config updated to use Parquet format")
            return True
        else:
            print("⚠️  Could not find Base Scenario path in config")
            return False
            
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False

def performance_test():
    """Test loading performance."""
    excel_path = Path("Data/Base Scenario.xlsx")
    parquet_path = Path("Data/Base Scenario.parquet")
    
    print("\n🏃‍♂️ PERFORMANCE TEST")
    print("="*40)
    
    # Test Parquet
    if parquet_path.exists():
        print("Testing Parquet loading...")
        start = time.time()
        try:
            df = pd.read_parquet(parquet_path)
            parquet_time = time.time() - start
            print(f"🚀 Parquet: {parquet_time:.2f}s ({len(df):,} rows)")
        except Exception as e:
            print(f"❌ Parquet test failed: {e}")
            return
    else:
        print("⚠️  Parquet file not found")
        return
    
    # Test Excel for comparison
    if excel_path.exists():
        print("Testing Excel loading...")
        start = time.time()
        try:
            df = pd.read_excel(excel_path, usecols=[0, 1, 2])
            excel_time = time.time() - start
            speedup = excel_time / parquet_time
            print(f"📊 Excel: {excel_time:.2f}s ({len(df):,} rows)")
            print(f"⚡ Speedup: {speedup:.1f}x faster with Parquet!")
        except Exception as e:
            print(f"❌ Excel test failed: {e}")

def main():
    """Main upgrade process."""
    print("🚀 Lagos Accessibility Dashboard - Performance Upgrade")
    print("="*55)
    
    # Step 1: Check/install PyArrow
    if not check_pyarrow():
        if not install_pyarrow():
            print("❌ Cannot proceed without PyArrow")
            return
    
    # Step 2: Convert to Parquet
    print("\n📊 STEP 2: Convert data format")
    print("-"*30)
    if not convert_base_scenario():
        print("❌ Data conversion failed")
        return
    
    # Step 3: Update config
    print("\n⚙️  STEP 3: Update configuration")
    print("-"*30)
    if not update_config():
        print("❌ Config update failed")
        return
    
    # Step 4: Performance test
    print("\n🏃‍♂️ STEP 4: Performance test")
    print("-"*30)
    performance_test()
    
    print("\n" + "="*55)
    print("✅ PERFORMANCE UPGRADE COMPLETE!")
    print("="*55)
    print("\n🎉 Your dashboard should now load much faster!")
    print("\nExpected improvements:")
    print("• 5-10x faster data loading")
    print("• 3-4x smaller file size")
    print("• Reduced memory usage")
    print("\n🚀 Run your dashboard now:")
    print("   python run_optimized.py")

if __name__ == "__main__":
    main()
