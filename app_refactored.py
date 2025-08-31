"""
Lagos Accessibility Dashboard - Refactored Version
---------------------------------------------------
A Streamlit application for analyzing and visualizing accessibility metrics
and travel times across Lagos transportation zones.

Features:
- Accessibility analysis showing jobs reachable within time threshold
- Time mapping showing travel times between zones
- Scenario comparison (base vs proposed changes)
- Interactive map visualization
- Data export capabilities
"""

# Standard library imports
import logging
from pathlib import Path

# Third-party imports
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium

# Local imports
from models import AppConfig, AnalysisConfig, MapConfig
from data_processing import (
    safe_load_data, 
    calculate_accessibility, 
    calculate_time_band_accessibility,
    organize_available_attributes,
    load_uploaded_skim,
    load_lga_gdf
)
from map_utils import (
    create_base_map,
    create_accessibility_layer,
    create_time_mapping_layer,
    add_lga_layer,
    assign_colors_to_zones,
    assign_time_mapping_colors
)
from ui_components import (
    setup_page_config,
    load_custom_css,
    display_main_header,
    display_sidebar_settings,
    display_file_upload_section,
    display_map_settings,
    display_zone_info,
    display_analysis_info,
    display_time_mapping_analysis,
    display_statistics,
    display_accessibility_table
)
from export_utils import (
    display_export_section,
    add_keyboard_shortcuts
)

# Enhanced logging setup
def setup_logging():
    """Setup comprehensive logging with file rotation."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('lagos_dashboard.log'),
            logging.StreamHandler()
        ]
    )

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def initialize_session_state(config: AppConfig):
    """Initialize all session state variables with proper configuration."""
    if "analysis_config" not in st.session_state:
        st.session_state.analysis_config = AnalysisConfig()
    
    if "map_config" not in st.session_state:
        st.session_state.map_config = config.map_config
    
    if "clicked_zone_id" not in st.session_state:
        st.session_state.clicked_zone_id = None
    
    if "scenario_file" not in st.session_state:
        st.session_state.scenario_file = None

def process_time_mapping_data(zones, base_skim, scenario_skim, analysis_config):
    """Process time mapping data with proper error handling."""
    try:
        # Calculate time bands for base scenario
        base_time_bands = calculate_time_band_accessibility(base_skim, analysis_config.time_band)
        
        # Merge time band data with zones
        for band_name, band_data in base_time_bands.items():
            zones = zones.merge(band_data, left_on="ZONE_ID", right_on="origin_zone", how="left")
            zones = zones.drop(columns=['origin_zone'])
            zones[band_name] = zones[band_name].fillna(0)
        
        # If we have a scenario file, calculate time bands for it too
        if scenario_skim is not None:
            scenario_time_bands = calculate_time_band_accessibility(scenario_skim, analysis_config.time_band)
            for band_name, band_data in scenario_time_bands.items():
                scenario_band_name = f"{band_name}_scenario"
                zones = zones.merge(band_data, left_on="ZONE_ID", right_on="origin_zone", how="left")
                zones = zones.drop(columns=['origin_zone'])
                zones[scenario_band_name] = zones[scenario_band_name].fillna(0)
        
        return zones
        
    except Exception as e:
        logger.error(f"Error calculating time bands: {str(e)}")
        st.error(f"Error calculating time bands: {str(e)}")
        return zones

def process_accessibility_data(zones, base_skim, scenario_skim, analysis_config):
    """Process accessibility data for both base and scenario."""
    # Calculate base accessibility
    access_a = calculate_accessibility(base_skim, zones, analysis_config.time_threshold, analysis_config.selected_attribute)
    zones = zones.merge(access_a, on="ZONE_ID", how="left").rename(columns={"accessible_value": "access_A"})
    zones["access_A"] = zones["access_A"].fillna(0)

    # Calculate percentage of total
    total_attribute = zones[analysis_config.selected_attribute].sum()
    zones["access_A_pct"] = (zones["access_A"] / total_attribute * 100).round(1)
    zones["access_A_pct_fmt"] = zones["access_A_pct"].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "N/A")

    # Process scenario if available
    if scenario_skim is not None:
        access_b = calculate_accessibility(scenario_skim, zones, analysis_config.time_threshold, analysis_config.selected_attribute)
        zones = zones.merge(access_b, on="ZONE_ID", how="left").rename(columns={"accessible_value": "access_B"})
        zones["access_B"] = zones["access_B"].fillna(0)
        zones["access_B_pct"] = (zones["access_B"] / total_attribute * 100).round(1)
        zones["access_B_pct_fmt"] = zones["access_B_pct"].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "N/A")
        zones["delta"] = zones["access_B"] - zones["access_A"]
    
    return zones

def create_map_layers(zones, analysis_config, map_config, lga_gdf):
    """Create map with appropriate layers based on analysis type."""
    # Create base map
    m = create_base_map(map_config)
    
    # Create zones layer based on analysis type
    if analysis_config.analysis_type == "Accessibility":
        # Determine which column to use for coloring based on view
        if analysis_config.view == "Base Scenario":
            color_column = "access_A"
        elif analysis_config.view != "Base Scenario" and analysis_config.view != "Difference" and "access_B" in zones.columns:
            color_column = "access_B"
        elif analysis_config.view == "Difference" and "delta" in zones.columns:
            color_column = "delta"
        else:
            color_column = "access_A"
        
        # Assign colors to zones
        zones, bins, color_list = assign_colors_to_zones(zones, color_column, analysis_config.selected_attribute)
        
        # Create accessibility layer
        zones_layer = create_accessibility_layer(zones, analysis_config.view, map_config, analysis_config.clicked_zone_id)
        
    else:  # Time Mapping mode
        # Calculate total accessibility for coloring
        time_band_cols = [col for col in zones.columns if col.startswith("zones_") and "scenario" not in col]
        if time_band_cols:
            total_accessibility_col = f"total_zones_{analysis_config.time_band}"
            zones[total_accessibility_col] = zones[time_band_cols].sum(axis=1)
            zones["total_accessible"] = zones[total_accessibility_col]
            
            # Assign time mapping colors
            zones, bins, color_list = assign_time_mapping_colors(zones, total_accessibility_col, 
                                                               st.session_state.app_config.color_schemes["time_mapping"])
        else:
            # Fallback to population
            zones, bins, color_list = assign_colors_to_zones(zones, "POP_2024", "Population")
        
        # Create time mapping layer
        zones_layer = create_time_mapping_layer(zones, map_config, analysis_config.clicked_zone_id)
    
    zones_layer.add_to(m)
    
    # Add LGA layer if enabled
    if map_config.show_lga_layer and lga_gdf is not None:
        add_lga_layer(m, lga_gdf, map_config)
    
    return m, zones

def main():
    """Main application function."""
    # Setup page configuration and styling
    setup_page_config()
    load_custom_css()
    
    # Load configuration
    config = AppConfig.load_from_yaml()
    
    # Initialize session state
    initialize_session_state(config)
    
    # Store config in session state for access throughout the app
    st.session_state.app_config = config
    
    # Display main header
    display_main_header()
    
    # Load data
    zones, base_skim, node_to_taz = safe_load_data(config)
    
    if zones is None or base_skim is None:
        st.error("Failed to load required data. Please check your data files.")
        st.stop()
    
    # Show data validation status
    total_zones = len(zones)
    total_population = zones["POP_2024"].sum()
    total_employment = zones["Emp 2024"].sum()
    
    st.success(f"✅ **Data loaded successfully!** {total_zones:,} zones, {total_population:,.0f} population, {total_employment:,.0f} employment")
    
    # Get organized attributes
    available_attributes, attribute_display_names = organize_available_attributes(zones)
    
    if not available_attributes:
        st.error("No valid attributes found in the data")
        st.stop()
    
    # Format population for tooltips
    zones["POP_2024_fmt"] = zones["POP_2024"].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "N/A")
    
    # Display sidebar settings and get updated configuration
    analysis_config = display_sidebar_settings(
        st.session_state.analysis_config, 
        available_attributes, 
        attribute_display_names
    )
    
    # Handle file upload
    uploaded_file, scenario_name, view = display_file_upload_section()
    analysis_config.view = view
    analysis_config.scenario_name = scenario_name
    
    # Update session state
    st.session_state.analysis_config = analysis_config
    
    # Process uploaded scenario file
    scenario_skim = None
    if uploaded_file:
        scenario_skim = load_uploaded_skim(uploaded_file, node_to_taz, config)
        st.session_state.scenario_file = uploaded_file
    
    # Display map settings and get map configuration
    map_settings = display_map_settings()
    map_config = MapConfig(
        center=config.map_config.center,
        zoom=config.map_config.zoom,
        height=config.map_config.height,
        fill_opacity=map_settings['fill_opacity'],
        line_weight=map_settings['line_weight'],
        show_labels=map_settings['show_labels'],
        show_lga_layer=map_settings['show_lga_layer'],
        lga_border_color=map_settings['lga_border_color'],
        lga_border_weight=map_settings['lga_border_weight'],
        show_lga_labels=map_settings['show_lga_labels']
    )
    
    # Process data based on analysis type
    if analysis_config.analysis_type == "Accessibility":
        zones = process_accessibility_data(zones, base_skim, scenario_skim, analysis_config)
    else:  # Time Mapping
        zones = process_time_mapping_data(zones, base_skim, scenario_skim, analysis_config)
    
    # Load LGA data
    lga_gdf = load_lga_gdf(config)
    
    # Display analysis info
    display_analysis_info(analysis_config)
    
    # Create and display map
    m, zones = create_map_layers(zones, analysis_config, map_config, lga_gdf)
    
    # Display the map
    clicked_data = st_folium(
        m,
        width=None,
        height=map_config.height,
        returned_objects=["last_active_drawing"],
        key="main_map"
    )
    
    # Handle zone clicks
    if clicked_data and clicked_data.get("last_active_drawing"):
        props = clicked_data["last_active_drawing"]["properties"]
        new_zone_id = props.get("ZONE_ID")
        if new_zone_id != st.session_state.analysis_config.clicked_zone_id:
            st.session_state.analysis_config.clicked_zone_id = new_zone_id
            analysis_config.clicked_zone_id = new_zone_id
            st.rerun()
    
    # Display zone information if a zone is clicked
    if analysis_config.clicked_zone_id:
        display_zone_info(analysis_config.clicked_zone_id, zones, analysis_config, analysis_config.time_threshold)
    
    # Show detailed analysis for Time Mapping mode
    if analysis_config.analysis_type == "Time Mapping" and analysis_config.clicked_zone_id:
        result = display_time_mapping_analysis(
            analysis_config.clicked_zone_id, 
            base_skim, 
            zones, 
            analysis_config.time_band
        )
        if result is None:  # User clicked clear button
            st.session_state.analysis_config.clicked_zone_id = None
            analysis_config.clicked_zone_id = None
            st.rerun()
    
    # Display export section
    display_export_section(m, zones, analysis_config, clicked_data)
    
    # Add keyboard shortcuts
    add_keyboard_shortcuts()
    
    # Display statistics
    display_statistics(total_population, total_employment)
    
    # Display accessibility table for Accessibility mode
    display_accessibility_table(zones, analysis_config)

if __name__ == "__main__":
    main()
