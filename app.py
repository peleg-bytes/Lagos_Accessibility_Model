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

# Configure page first for better performance - MUST be the very first Streamlit command
st.set_page_config(
    page_title="Lagos Accessibility Dashboard", 
    page_icon="🗺️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    add_zone_labels,
    assign_colors_to_zones,
    assign_time_mapping_colors,
    color_zones_by_origin_travel_time,
    add_recenter_control,
    add_map_bounds,
    add_streamlit_safe_legend,
    add_compatibility_fixes
)
from ui_components import (
    setup_page_config,
    load_custom_css,
    display_main_header,
    display_combined_header,
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
    zones["access_A_pct"] = (zones["access_A"] / total_attribute * 100).round(0)
    zones["access_A_pct_fmt"] = zones["access_A_pct"].apply(lambda x: f"{x:.0f}%" if pd.notnull(x) else "N/A")

    # Process scenario if available
    if scenario_skim is not None:
        access_b = calculate_accessibility(scenario_skim, zones, analysis_config.time_threshold, analysis_config.selected_attribute)
        zones = zones.merge(access_b, on="ZONE_ID", how="left").rename(columns={"accessible_value": "access_B"})
        zones["access_B"] = zones["access_B"].fillna(0)
        zones["access_B_pct"] = (zones["access_B"] / total_attribute * 100).round(0)
        zones["access_B_pct_fmt"] = zones["access_B_pct"].apply(lambda x: f"{x:.0f}%" if pd.notnull(x) else "N/A")
        zones["delta"] = zones["access_B"] - zones["access_A"]

    return zones

def create_map_layers(zones, analysis_config, map_config, lga_gdf, base_skim=None):
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
        # If a zone is selected, color by travel time from that origin
        if analysis_config.clicked_zone_id and base_skim is not None:
            logger.info(f"Applying dynamic coloring for origin zone {analysis_config.clicked_zone_id}")
            zones = color_zones_by_origin_travel_time(
                zones,
                base_skim,
                analysis_config.clicked_zone_id,
                analysis_config.time_band,
                st.session_state.app_config.color_schemes["time_mapping"]
            )
            # Debug: Check if colors were applied
            if 'color' in zones.columns:
                unique_colors = zones['color'].value_counts()
                logger.info(f"Applied colors to zones: {len(unique_colors)} unique colors")
            else:
                logger.warning("No color column found in zones after dynamic coloring")
        else:
            # Calculate total accessibility for generic coloring
            time_band_cols = [col for col in zones.columns if col.startswith("zones_") and "scenario" not in col]
            if time_band_cols:
                total_accessibility_col = f"total_zones_{analysis_config.time_band}"
                zones[total_accessibility_col] = zones[time_band_cols].sum(axis=1)
                zones["total_accessible"] = zones[total_accessibility_col]
                
                zones, bins, color_list = assign_time_mapping_colors(
                    zones,
                    total_accessibility_col,
                    st.session_state.app_config.color_schemes["time_mapping"]
                )
            else:
                zones, bins, color_list = assign_colors_to_zones(zones, "POP_2024", "Population")
        
        # Create time mapping layer
        zones_layer = create_time_mapping_layer(zones, map_config, analysis_config.clicked_zone_id)
    
    zones_layer.add_to(m)
    
    # Add enhanced controls with streamlit-folium compatibility fixes
    add_recenter_control(m, map_config.center, map_config.zoom, zones)
    add_map_bounds(m, sw=[3.0, -5.0], ne=[15.0, 16.0], viscosity=0.8)
    add_compatibility_fixes(m)
    
    # Add legends based on analysis type
    if analysis_config.analysis_type == "Time Mapping" and analysis_config.clicked_zone_id:
        # Create legend based on dynamic color classes for time mapping
        legend_items = []
        if hasattr(zones, 'label') and hasattr(zones, 'color'):
            # Get unique label-color pairs from the zones
            unique_labels = zones.dropna(subset=['label', 'color']).drop_duplicates(['label', 'color'])
            
            # Convert to list and sort by time ranges
            legend_data_list = []
            for _, row in unique_labels.iterrows():
                label = row['label']
                color = row['color']
                
                # Extract the starting time for sorting
                if 'No data' in label:
                    sort_key = 9999  # Put "No data" at the end
                elif '+' in label:
                    # Extract number before '+'
                    sort_key = float(label.split('+')[0])
                else:
                    # Extract first number from range like "0-15 min"
                    sort_key = float(label.split('-')[0])
                
                legend_data_list.append({
                    'color': color,
                    'label': label,
                    'sort_key': sort_key
                })
                
                logger.info(f"Legend item: {label} -> {color} (sort_key: {sort_key})")
            
            # Sort by time (ascending order: shortest to longest)
            legend_data_list.sort(key=lambda x: x['sort_key'])
            logger.info(f"Legend sorted order: {[item['label'] for item in legend_data_list]}")
            
            # Create final legend items
            legend_items = [{'color': item['color'], 'label': item['label']} for item in legend_data_list]
        
        if legend_items:
            legend_data = {
                'title': f'Travel Time from Zone {analysis_config.clicked_zone_id}',
                'items': legend_items
            }
            add_streamlit_safe_legend(m, legend_data, map_config.fill_opacity)
            
    elif analysis_config.analysis_type == "Accessibility":
        # Create legend for accessibility analysis
        legend_items = []
        if hasattr(zones, 'label') and hasattr(zones, 'color'):
            # Get unique label-color pairs from the zones
            unique_labels = zones.dropna(subset=['label', 'color']).drop_duplicates(['label', 'color'])
            
            # Convert to list and sort by value range
            legend_data_list = []
            for _, row in unique_labels.iterrows():
                label = row['label']
                color = row['color']
                
                # Extract starting value for sorting (e.g., "1,000 - 2,000" -> 1000)
                try:
                    if '+' in label:
                        # Handle "10,000+" format
                        sort_key = float(label.split('+')[0].replace(',', ''))
                    elif ' - ' in label:
                        # Handle "1,000 - 2,000" format
                        sort_key = float(label.split(' - ')[0].replace(',', ''))
                    else:
                        sort_key = 0  # Fallback for unexpected formats
                except (ValueError, IndexError):
                    sort_key = 0
                
                legend_data_list.append({
                    'color': color,
                    'label': label,
                    'sort_key': sort_key
                })
                
                logger.info(f"Accessibility legend item: {label} -> {color} (sort_key: {sort_key})")
            
            # Sort by value (ascending order: lowest to highest)
            legend_data_list.sort(key=lambda x: x['sort_key'])
            logger.info(f"Accessibility legend sorted order: {[item['label'] for item in legend_data_list]}")
            
            # Create final legend items
            legend_items = [{'color': item['color'], 'label': item['label']} for item in legend_data_list]
        
        if legend_items:
            # Determine legend title based on view
            if analysis_config.view == "Base Scenario":
                title = f'{analysis_config.selected_attribute} Accessibility'
            elif analysis_config.view == "Difference":
                title = f'{analysis_config.selected_attribute} Accessibility Change'
            else:
                title = f'{analysis_config.selected_attribute} Accessibility ({analysis_config.view})'
                
            legend_data = {
                'title': title,
                'items': legend_items
            }
            add_streamlit_safe_legend(m, legend_data, map_config.fill_opacity)

    # Add zone labels if enabled
    add_zone_labels(m, zones, map_config)
    
    # Add LGA layer if enabled
    if map_config.show_lga_layer and lga_gdf is not None:
        add_lga_layer(m, lga_gdf, map_config)
    
    return m, zones

def display_debug_report():
    """Display the debug report in the main area."""
    from datetime import datetime
    import json
    
    report = st.session_state.debug_report
    
    st.markdown("---")
    st.subheader("🔍 Developer Debug Report")
    
    # Add clear button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("❌ Clear Report"):
            del st.session_state.debug_report
            st.rerun()
    
    # System Information
    st.markdown("### 💻 System Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Platform", report["system"]["platform"])
        st.metric("Memory Usage", report["system"]["memory_usage"])
    with col2:
        st.metric("Python", report["system"]["python_version"].split()[0])
        st.metric("Streamlit", report["system"]["streamlit_version"])
    with col3:
        st.metric("Load Time", report["system"]["load_time"])
        st.metric("CPU Cores", report["system"]["cpu_count"])
    
    # Data Analysis
    st.markdown("### 📊 Data Analysis")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Zones Count", f"{report['data']['zones_count']:,}")
        st.metric("Zones Memory", report["data"]["zones_memory"])
    with col2:
        st.metric("Base Skim Count", f"{report['data']['base_skim_count']:,}")
        st.metric("Base Skim Memory", report["data"]["base_skim_memory"])
    
    st.write("**Zone Columns:**", ", ".join(report["data"]["zones_columns"][:10]) + ("..." if len(report["data"]["zones_columns"]) > 10 else ""))
    
    # Analysis Configuration
    st.markdown("### ⚙️ Analysis Configuration")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Type:** {report['analysis']['type']}")
        st.write(f"**View:** {report['analysis']['view']}")
        st.write(f"**Attribute:** {report['analysis']['selected_attribute']}")
    with col2:
        st.write(f"**Time Threshold:** {report['analysis']['time_threshold']} min")
        st.write(f"**Clicked Zone:** {report['analysis']['clicked_zone']}")
    
    # App Configuration
    with st.expander("⚙️ App Configuration Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Cache TTL:** {report['config']['cache_ttl_hours']} hours")
            st.write(f"**Batch Size:** {report['config']['batch_size']:,}")
            st.write(f"**Max File Size:** {report['config']['max_file_size_mb']} MB")
            st.write(f"**Geometry Simplification:** {report['config']['geometry_simplification']}")
        with col2:
            st.write(f"**Map Center:** {report['config']['map_center']}")
            st.write(f"**Map Zoom:** {report['config']['map_zoom']}")
            st.write(f"**Map Height:** {report['config']['map_height']} px")
            st.write(f"**Export Formats:** {', '.join(report['config']['export_formats'])}")
    
    # Session State
    with st.expander("🔄 Session State Details"):
        st.write(f"**Session Keys ({len(report['session_state']['keys'])}):**")
        st.write(report["session_state"]["keys"])
        st.write(f"**App Loaded:** {report['session_state']['app_fully_loaded']}")
        st.write(f"**Data Cached:** {report['session_state']['data_loaded']}")
    
    # Export report as JSON
    report_json = json.dumps(report, indent=2, default=str)
    st.download_button(
        "📥 Download Debug Report (JSON)",
        report_json,
        file_name=f"lagos_dashboard_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

def generate_debug_report(zones, base_skim, analysis_config, load_time, config):
    """Generate comprehensive debug report for developer."""
    import sys
    import platform
    import streamlit as st
    from datetime import datetime
    import pandas as pd
    
    # Try to import psutil for system metrics (optional dependency)
    try:
        import psutil  # type: ignore
        memory_usage = f"{psutil.virtual_memory().percent}%"
        cpu_count = psutil.cpu_count()
    except ImportError:
        memory_usage = "N/A (psutil not installed)"
        cpu_count = "N/A (psutil not installed)"
    
    # System Information
    report = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "platform": platform.platform(),
            "python_version": sys.version,
            "streamlit_version": st.__version__,
            "memory_usage": memory_usage,
            "cpu_count": cpu_count,
            "load_time": f"{load_time:.3f} seconds"
        },
        "data": {
            "zones_count": len(zones) if zones is not None else 0,
            "zones_columns": list(zones.columns) if zones is not None else [],
            "zones_memory": f"{zones.memory_usage(deep=True).sum() / 1024**2:.2f} MB" if zones is not None else "N/A",
            "base_skim_count": len(base_skim) if base_skim is not None else 0,
            "base_skim_memory": f"{base_skim.memory_usage(deep=True).sum() / 1024**2:.2f} MB" if base_skim is not None else "N/A"
        },
        "analysis": {
            "type": analysis_config.analysis_type,
            "view": analysis_config.view,
            "selected_attribute": analysis_config.selected_attribute,
            "time_threshold": analysis_config.time_threshold,
            "clicked_zone": analysis_config.clicked_zone_id
        },
        "session_state": {
            "keys": list(st.session_state.keys()),
            "app_fully_loaded": st.session_state.get('app_fully_loaded', False),
            "data_loaded": st.session_state.get('data_loaded', False)
        },
        "config": {
            "cache_ttl_hours": config.cache_ttl_hours,
            "batch_size": config.batch_size,
            "geometry_simplification": config.geometry_simplification,
            "max_file_size_mb": config.max_file_size_mb,
            "export_formats": config.export_formats,
            "map_center": config.map_config.center,
            "map_zoom": config.map_config.zoom,
            "map_height": config.map_config.height
        }
    }
    
    # Store report in session state for display
    st.session_state.debug_report = report
    
    # Show success message and rerun to display report in main area
    st.sidebar.success("🔍 Debug report generated! Check main area below.")
    st.rerun()

def main():
    """Main application function."""
    import time
    start_time = time.time()
    
    # Single consolidated loading process
    if 'app_fully_loaded' not in st.session_state:
        with st.spinner("🚀 Loading Lagos Accessibility Dashboard..."):
            # Setup configuration and styling
            setup_page_config()
            load_custom_css()
            
            # Load configuration
            config = AppConfig.load_from_yaml()
            
            # Initialize session state
            initialize_session_state(config)
            
            # Store config in session state
            st.session_state.app_config = config
            
            # Load all data
            zones, base_skim, node_to_taz = safe_load_data(config)
            if zones is None or base_skim is None:
                st.error("❌ Failed to load required data. Please check your data files.")
                st.info("💡 **Tip**: Ensure all data files are in the correct directory and try refreshing the page.")
                st.stop()
            
            # Cache everything in session state
            st.session_state.zones = zones
            st.session_state.base_skim = base_skim
            st.session_state.node_to_taz = node_to_taz
            st.session_state.app_fully_loaded = True
    else:
        # Use cached data for instant subsequent loads
        config = st.session_state.app_config
        zones = st.session_state.zones
        base_skim = st.session_state.base_skim
        node_to_taz = st.session_state.node_to_taz
        # Still need to call these for UI setup
        setup_page_config()
        load_custom_css()
    
    # Display combined header box
    display_combined_header(st.session_state.analysis_config)
    
    # Show data validation status
    total_zones = len(zones)
    total_population = zones["POP_2024"].sum()
    total_employment = zones["Emp 2024"].sum()
    
    # Data loaded summary removed per request
    
    # Get organized attributes
    available_attributes, attribute_display_names = organize_available_attributes(zones)
    
    if not available_attributes:
        st.error("No valid attributes found in the data")
        st.stop()
    
    # Format population and employment for tooltips
    zones["POP_2024_fmt"] = zones["POP_2024"].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "N/A")
    zones["Emp_2024_fmt"] = zones["Emp 2024"].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "N/A")
    
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
    
    # Load LGA data only if needed (lazy loading)
    lga_gdf = None
    if map_config.show_lga_layer:
        if 'lga_gdf' not in st.session_state:
            st.session_state.lga_gdf = load_lga_gdf(config)
        lga_gdf = st.session_state.lga_gdf
    
    # Combined header already includes analysis and instructions
    
    # Create and display map
    m, zones = create_map_layers(zones, analysis_config, map_config, lga_gdf, base_skim)
    
    # Display the map with enhanced key management to prevent element loss
    # Include time_band in key to force refresh when time band changes
    map_key = f"main_map_{analysis_config.analysis_type}_{analysis_config.clicked_zone_id}_{analysis_config.time_band}_{hash(str(analysis_config.view))}"
    logger.info(f"Using map key: {map_key}")
    clicked_data = st_folium(
        m,
        width=None,
        height=map_config.height,
        returned_objects=["last_active_drawing"],
        key=map_key,
        # Force re-render to ensure custom elements are preserved
        use_container_width=True
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
    
    # Display debug report if generated
    if st.session_state.get('debug_report'):
        display_debug_report()
    
    # Developer debug mode (hidden from end users)
    debug_mode = st.session_state.get('debug_mode', False)
    
    # Hidden debug mode toggle (developer only - use query params or session state)
    if st.query_params.get("debug") == "true" or debug_mode:
        st.session_state.debug_mode = True
        debug_mode = True
    
    if debug_mode:
        end_time = time.time()
        load_time = end_time - start_time
        
        with st.sidebar.expander("🔧 Developer Debug Tools", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 Generate Debug Report"):
                    generate_debug_report(zones, base_skim, analysis_config, load_time, config)
            with col2:
                if st.button("🧹 Clear All Cache"):
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    st.success("Cache cleared!")
                    
            st.metric("Page Load Time", f"{load_time:.2f} seconds")
            if 'data_loaded' in st.session_state:
                st.info("✅ Data cached")
            else:
                st.warning("⚠️ First load")

if __name__ == "__main__":
    main()