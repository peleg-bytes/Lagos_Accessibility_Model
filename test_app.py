"""
Simple test script to validate the refactored application components
"""
import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        from models import AppConfig, AnalysisConfig, MapConfig, ATTRIBUTE_METADATA
        print("✅ Models imported successfully")
        
        from data_processing import safe_load_data, calculate_accessibility
        print("✅ Data processing imported successfully")
        
        from map_utils import create_base_map, assign_colors_to_zones
        print("✅ Map utils imported successfully")
        
        from ui_components import setup_page_config, load_custom_css
        print("✅ UI components imported successfully")
        
        from export_utils import export_map_as_png, create_data_export
        print("✅ Export utils imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        from models import AppConfig
        
        # Test default config creation
        config = AppConfig()
        assert config.map_config.center == [6.5244, 3.3792]
        assert config.cache_ttl_hours == 1
        print("✅ Default configuration created successfully")
        
        # Test YAML loading (will use defaults if file doesn't exist)
        config_from_yaml = AppConfig.load_from_yaml()
        assert config_from_yaml is not None
        print("✅ Configuration loaded from YAML successfully")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_data_validation():
    """Test data validation functions."""
    try:
        from data_processing import validate_dataframe, safe_numeric_conversion
        import pandas as pd
        
        # Test DataFrame validation
        df = pd.DataFrame({
            'ZONE_ID': [1, 2, 3],
            'geometry': ['point1', 'point2', 'point3']
        })
        
        result = validate_dataframe(df, ['ZONE_ID', 'geometry'], 'test_df')
        assert result == True
        print("✅ DataFrame validation working")
        
        # Test numeric conversion
        series = pd.Series(['1', '2', '3', 'invalid'])
        converted = safe_numeric_conversion(series)
        assert len(converted) == 4
        print("✅ Numeric conversion working")
        
        return True
    except Exception as e:
        print(f"❌ Data validation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Lagos Accessibility Dashboard Components\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_config),
        ("Data Validation Tests", test_data_validation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print(f"\n🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactored application is ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
