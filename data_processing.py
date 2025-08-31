"""
Data loading and processing utilities for Lagos Accessibility Dashboard
"""
import pandas as pd
import geopandas as gpd
import logging
import math
from typing import Optional, Tuple, List, Dict
from pathlib import Path
import streamlit as st

from models import AppConfig, ATTRIBUTE_METADATA

logger = logging.getLogger(__name__)

class DataLoadError(Exception):
    """Custom exception for data loading errors."""
    pass

class ValidationError(Exception):
    """Custom exception for data validation errors."""
    pass

def log_error_with_context(func_name: str, error: Exception, context: dict = None):
    """Log errors with context for better debugging."""
    logger.error(f"Error in {func_name}: {str(error)}")
    if context:
        logger.error(f"Context: {context}")
    logger.error(f"Traceback: {error}")

def validate_dataframe(df: pd.DataFrame, required_columns: List[str], name: str) -> bool:
    """Validate DataFrame has required columns."""
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValidationError(f"{name} is missing required columns: {missing_cols}")
    return True

def safe_numeric_conversion(series: pd.Series, errors: str = 'coerce') -> pd.Series:
    """Safely convert series to numeric with error handling."""
    try:
        if isinstance(series, pd.Series):
            return pd.to_numeric(series, errors=errors)
        else:
            return pd.Series(series)
    except Exception as e:
        logger.warning(f"Error converting series to numeric: {e}")
        return pd.Series(series)

def validate_and_clean_data(zones_df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Validate and clean zone data."""
    try:
        # Check for negative values
        numeric_cols = zones_df.select_dtypes(include=['int64', 'float64']).columns
        outlier_summary = {}
        
        for col in numeric_cols:
            if col != "ZONE_ID":
                # Replace negative values with 0
                zones_df[col] = zones_df[col].clip(lower=0)
                
                # Check for outliers with different thresholds based on column type
                mean_val = zones_df[col].mean()
                std_val = zones_df[col].std()
                
                # Use more lenient threshold for employment and population data
                if "Emp" in col or "POP" in col or "Area" in col:
                    threshold = mean_val + 4 * std_val  # 4 standard deviations
                else:
                    threshold = mean_val + 3 * std_val  # 3 standard deviations
                
                outlier_mask = zones_df[col] > threshold
                if outlier_mask.any():
                    outlier_summary[col] = outlier_mask.sum()
        
        # Log summary
        if outlier_summary:
            total_outliers = sum(outlier_summary.values())
            logger.info(f"Data validation complete: Found {total_outliers} total outliers across {len(outlier_summary)} columns")
        
        return zones_df
    except Exception as e:
        log_error_with_context("validate_and_clean_data", e)
        return zones_df

def validate_uploaded_file(uploaded_file, config: AppConfig) -> bool:
    """Validate uploaded file for security and format."""
    try:
        # Check file size
        max_size = config.max_file_size_mb * 1024 * 1024
        if uploaded_file.size > max_size:
            st.error(f"File too large. Maximum size is {config.max_file_size_mb}MB.")
            return False
        
        # Check file extension - now supporting Parquet for faster uploads
        allowed_extensions = ['.xlsx', '.xls', '.parquet']
        file_extension = Path(uploaded_file.name).suffix.lower()
        if file_extension not in allowed_extensions:
            st.error("Invalid file type. Please upload Excel (.xlsx, .xls) or Parquet (.parquet) files only.")
            return False
        
        return True
    except Exception as e:
        log_error_with_context("validate_uploaded_file", e)
        return False

@st.cache_data(ttl=7200, show_spinner=False)  # Cache for 2 hours, hide spinner for cached loads
def load_zones(config: AppConfig) -> Optional[gpd.GeoDataFrame]:
    """Load and prepare transportation analysis zones."""
    try:
        # Read the geojson file (spinner handled at app level)
        gdf = gpd.read_file(config.data_paths.zones)
        
        # Validate required columns
        required_cols = ["ZONE_ID", "geometry"]
        validate_dataframe(gdf, required_cols, "Transportation zones")
        
        # Ensure ZONE_ID is loaded as int32
        zone_id_series = safe_numeric_conversion(gdf["ZONE_ID"])
        if hasattr(zone_id_series, 'fillna'):
            zone_id_series = zone_id_series.fillna(0)
        gdf["ZONE_ID"] = zone_id_series.astype("int32")
        
        # Convert known numeric columns to appropriate types
        numeric_cols = [
            "POP_2024", "Emp 2024", 
            "HEALTH_BLDG", "EDU_PRIM", "EDU_SEC", "EDU", "HLT_BLDG"
        ]
        
        for col in numeric_cols:
            if col in gdf.columns:
                gdf[col] = safe_numeric_conversion(gdf[col])
                # Check if all values are integers
                if gdf[col].notna().all() and (gdf[col] % 1 == 0).all():
                    gdf[col] = gdf[col].astype('int64')

        # Simplify geometry
        gdf["geometry"] = gdf["geometry"].simplify(config.geometry_simplification, preserve_topology=True)
        
        # Apply data validation and cleaning
        gdf = validate_and_clean_data(gdf)
        
        return gdf
            
    except FileNotFoundError:
        log_error_with_context("load_zones", FileNotFoundError("File not found"), {"file": config.data_paths.zones})
        raise DataLoadError(f"Transportation zones file ({config.data_paths.zones}) not found")
    except Exception as e:
        log_error_with_context("load_zones", e, {"file": config.data_paths.zones})
        raise DataLoadError(f"Failed to load transportation zones: {str(e)}")

@st.cache_data(ttl=7200, show_spinner=False, max_entries=3)  # Cache for 2 hours, hide spinner, limit cache size
def load_base_skim(config: AppConfig) -> Optional[pd.DataFrame]:
    """Load base scenario travel time matrix and convert from node-based to zone-based."""
    try:
        file_path = Path(str(config.data_paths.base_scenario))
        
        # Auto-detect file format and use appropriate loader
        if file_path.suffix.lower() == '.parquet':
            # Load Parquet file (much faster!)
            df = pd.read_parquet(config.data_paths.base_scenario)
            # Parquet files are already cleaned, so minimal processing needed
            if "travel_time" not in df.columns:
                df.columns = ["origin_node", "destination_node", "travel_time"]
        else:
            # Load Excel file (legacy support)
            df = pd.read_excel(
                config.data_paths.base_scenario, 
                usecols=[0, 1, 2],
                engine='openpyxl',  # Use faster engine
                dtype={'travel_time': str}  # Read as string first to handle "--" values
            )
            df.columns = ["origin_node", "destination_node", "travel_time"]
            
            # Clean Excel data (Parquet files are pre-cleaned)
            mask = df["travel_time"] != "--"
            df = df[mask].copy()  # Create copy to avoid SettingWithCopyWarning
            df["travel_time"] = pd.to_numeric(df["travel_time"], errors="coerce")
            df = df.dropna(subset=["travel_time"])

        # Load node to zone mapping
        node_to_zone_df = load_node_to_taz_mapping(config)
        
        # Ensure zone_id is int32 in mapping
        node_to_zone_df["zone_id"] = node_to_zone_df["zone_id"].astype("int32")
        
        # Convert node IDs to zone IDs
        df = df.merge(
            node_to_zone_df[["node_id", "zone_id"]], 
            left_on="origin_node", 
            right_on="node_id"
        ).rename(columns={"zone_id": "origin_zone"}).drop(columns=["node_id"])
        
        df = df.merge(
            node_to_zone_df[["node_id", "zone_id"]], 
            left_on="destination_node", 
            right_on="node_id"
        ).rename(columns={"zone_id": "destination_zone"}).drop(columns=["node_id"])

        # Clean up and prepare final skim
        df = df.dropna(subset=["origin_zone", "destination_zone"])
        df["origin_zone"] = df["origin_zone"].astype("int32")
        df["destination_zone"] = df["destination_zone"].astype("int32")

        # Average travel times for same zone pairs
        skim = df.groupby(["origin_zone", "destination_zone"])["travel_time"].mean().reset_index()
        
        return skim
    except FileNotFoundError:
        log_error_with_context("load_base_skim", FileNotFoundError("File not found"), {"file": config.data_paths.base_scenario})
        raise DataLoadError(f"Base scenario file ({config.data_paths.base_scenario}) not found")
    except Exception as e:
        log_error_with_context("load_base_skim", e, {"file": config.data_paths.base_scenario})
        raise DataLoadError(f"Failed to load base scenario: {str(e)}")

@st.cache_data(ttl=7200, show_spinner=False)  # Cache for 2 hours, hide spinner
def load_node_to_taz_mapping(config: AppConfig) -> pd.DataFrame:
    """Load mapping between network nodes and transportation zones."""
    try:
        df = pd.read_excel(config.data_paths.node_mapping)
        df = df.rename(columns={"ID": "node_id", "TAZ": "zone_id"})
        
        # Validate the mapping data
        if df.empty:
            raise ValidationError("Node-to-TAZ mapping file is empty")
        
        # Check for missing values
        missing_nodes = df["node_id"].isna().sum()
        missing_zones = df["zone_id"].isna().sum()
        
        if missing_nodes > 0 or missing_zones > 0:
            logger.warning(f"Found {missing_nodes} missing node IDs and {missing_zones} missing zone IDs")
        
        return df
    except Exception as e:
        log_error_with_context("load_node_to_taz_mapping", e, {"file": config.data_paths.node_mapping})
        raise DataLoadError(f"Failed to load node-to-TAZ mapping: {str(e)}")

@st.cache_data(ttl=7200, show_spinner=False)  # Cache for 2 hours, hide spinner
def load_lga_gdf(config: AppConfig):
    """Load LGA boundaries."""
    try:
        lga_gdf = gpd.read_file(config.data_paths.lgas)
        # If LGA_NAME is missing or null, fill with index as string
        if "LGA_NAME" not in lga_gdf.columns:
            lga_gdf["LGA_NAME"] = lga_gdf.index.astype(str)
        lga_gdf["LGA_NAME"] = lga_gdf["LGA_NAME"].fillna(pd.Series(lga_gdf.index.astype(str), index=lga_gdf.index))
        return lga_gdf
    except Exception as e:
        logger.warning(f"Could not load LGAs.geojson: {e}")
        return None

@st.cache_data(ttl=1800, show_spinner=False)  # Cache uploaded files for 30 minutes
def load_uploaded_skim(uploaded_file, node_to_zone_df: pd.DataFrame, config: AppConfig) -> Optional[pd.DataFrame]:
    """Load and process an uploaded scenario skim file with optimizations."""
    try:
        # Validate file before processing
        if not validate_uploaded_file(uploaded_file, config):
            return None
        
        # Auto-detect file format and load accordingly
        file_extension = Path(uploaded_file.name).suffix.lower()
        
        if file_extension == '.parquet':
            # Load Parquet file (much faster!)
            df = pd.read_parquet(uploaded_file)
            # Ensure columns are named correctly
            if len(df.columns) >= 3 and "travel_time" not in df.columns:
                df.columns = ["origin_node", "destination_node", "travel_time"]
            # Parquet files are typically pre-cleaned
        else:
            # Load Excel file with optimizations
            df = pd.read_excel(
                uploaded_file, 
                usecols=[0, 1, 2],
                engine='openpyxl',  # Use faster engine
                dtype={2: str}  # Read travel_time as string to handle "--" values
            )
            df.columns = ["origin_node", "destination_node", "travel_time"]
            
            # Clean Excel data (Parquet files are typically pre-cleaned)
            mask = df["travel_time"] != "--"
            df = df[mask].copy()  # Create copy to avoid warnings
            df["travel_time"] = pd.to_numeric(df["travel_time"], errors="coerce")
            df = df.dropna(subset=["travel_time"])
        
        # Convert node IDs to zone IDs
        df = df.merge(
            node_to_zone_df[["node_id", "zone_id"]], 
            left_on="origin_node", 
            right_on="node_id"
        ).rename(columns={"zone_id": "origin_zone"}).drop(columns=["node_id"])
        
        df = df.merge(
            node_to_zone_df[["node_id", "zone_id"]], 
            left_on="destination_node", 
            right_on="node_id"
        ).rename(columns={"zone_id": "destination_zone"}).drop(columns=["node_id"])

        # Clean up and prepare final skim
        df = df.dropna(subset=["origin_zone", "destination_zone"])
        df["origin_zone"] = df["origin_zone"].astype("int32")
        df["destination_zone"] = df["destination_zone"].astype("int32")

        # Average travel times for same zone pairs
        skim = df.groupby(["origin_zone", "destination_zone"])["travel_time"].mean().reset_index()
        
        # Log successful processing
        logger.info(f"Successfully processed uploaded skim file: {uploaded_file.name}")
        
        return skim
    except Exception as e:
        log_error_with_context("load_uploaded_skim", e, {"file": uploaded_file.name if uploaded_file else "unknown"})
        st.error(f"Error loading scenario file: {str(e)}")
        return None

@st.cache_data(ttl=3600, show_spinner=False)  # Cache calculations for 1 hour
def calculate_accessibility(_skim_df: pd.DataFrame, _zone_df: gpd.GeoDataFrame, time_limit: int, attribute: str) -> pd.DataFrame:
    """Calculate accessibility with dynamic attribute selection."""
    # Filter skim data first to reduce processing
    filtered_skim = _skim_df[_skim_df["travel_time"] <= time_limit].copy()
    
    # Prepare destinations data
    destinations = _zone_df[["ZONE_ID", attribute]].rename(
        columns={"ZONE_ID": "destination_zone", attribute: "attribute_value"}
    )
    
    # Optimized merge and aggregation
    joined = filtered_skim.merge(destinations, on="destination_zone", how="inner")  # Use inner join for efficiency
    access = joined.groupby("origin_zone", as_index=False)["attribute_value"].sum()
    access.columns = ["ZONE_ID", "accessible_value"]
    return access

def calculate_time_band_accessibility(skim_df: pd.DataFrame, time_band: int) -> Dict[str, pd.DataFrame]:
    """Calculate which zones are accessible within each time band."""
    time_bands = {}
    
    # Pre-sort data for more efficient filtering
    skim_sorted = skim_df.sort_values("travel_time")
    
    for i in range(1, 6):  # Create 5 time bands
        upper_limit = i * time_band
        lower_limit = (i - 1) * time_band if i > 1 else 0
        
        # Optimized filtering
        mask = (skim_sorted["travel_time"] > lower_limit) & (skim_sorted["travel_time"] <= upper_limit)
        band_skim = skim_sorted[mask]
        
        # Count accessible zones for each origin
        band_access = band_skim.groupby("origin_zone", as_index=False).size()
        band_access.columns = ["origin_zone", f"zones_{lower_limit}_{upper_limit}"]
        time_bands[f"zones_{lower_limit}_{upper_limit}"] = band_access
    
    return time_bands

def organize_available_attributes(zones_df: gpd.GeoDataFrame) -> Tuple[List[str], Dict[str, str]]:
    """Organize available attributes into categories with proper display names."""
    # Get all numeric columns, including both float and integer types
    numeric_columns = zones_df.select_dtypes(include=['int64', 'int32', 'float64']).columns
    available_attributes = []
    attribute_display_names = {}
    
    # Define attributes to exclude from the interface
    excluded_attributes = ["dev type_2", "dev_type_2"]
    
    # First add known attributes from metadata
    for category, attrs in ATTRIBUTE_METADATA.items():
        for col, metadata in attrs.items():
            if col in numeric_columns and col not in excluded_attributes:
                available_attributes.append(col)
                attribute_display_names[col] = f"{metadata['name']} ({metadata['unit']})"
    
    # Then add any remaining numeric columns (except ZONE_ID and excluded attributes)
    for col in numeric_columns:
        if (col not in attribute_display_names and 
            col != "ZONE_ID" and 
            col not in excluded_attributes):
            display_name = col.replace("_", " ").title()
            available_attributes.append(col)
            attribute_display_names[col] = display_name
    
    return available_attributes, attribute_display_names

def safe_load_data(config: AppConfig) -> Tuple[Optional[gpd.GeoDataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Safely load all required data files with error handling."""
    try:
        # Load all data files (spinner handled at app level)
        zones = load_zones(config)
        if zones is None:
            raise DataLoadError("Failed to load zones")
        
        base_skim = load_base_skim(config)
        if base_skim is None:
            raise DataLoadError("Failed to load base scenario")
        
        node_to_taz = load_node_to_taz_mapping(config)
        if node_to_taz is None:
            raise DataLoadError("Failed to load node-to-TAZ mapping")
        
        return zones, base_skim, node_to_taz
    except Exception as e:
        log_error_with_context("safe_load_data", e)
        st.error(f"**Data Loading Error**: {str(e)}")
        st.info("💡 **Tip**: Check your data files and try refreshing the page.")
        return None, None, None
