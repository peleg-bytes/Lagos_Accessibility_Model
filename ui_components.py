"""
UI components and styling utilities for Lagos Accessibility Dashboard
"""
import streamlit as st
import pandas as pd
import geopandas as gpd
from typing import Optional, Dict, Any
import logging
from pathlib import Path

from models import AnalysisConfig, ATTRIBUTE_METADATA
from map_utils import format_attribute_value

logger = logging.getLogger(__name__)

def setup_page_config():
    """Setup Streamlit page configuration (page config is now handled in main app)."""
    # Page config is now handled in app.py to avoid duplicate calls
    pass

def load_custom_css():
    """Load custom CSS styling for the dashboard."""
    st.markdown("""
        <style>
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .metric-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border-radius: 12px;
            padding: 1.5rem;
            color: white;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .sidebar-section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            border-left: 4px solid #667eea;
        }
        .info-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .info-text {
            font-size: 1.1em;
            color: white;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        .zone-info-container {
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            padding: 20px;
            margin-bottom: 15px;
            color: white;
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
            max-width: 100%;
            backdrop-filter: blur(10px);
            animation: fadeInUp 0.3s ease-out;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .zone-info-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(8px);
        }
        .zone-title {
            font-size: 1.4em;
            font-weight: 600;
            margin-bottom: 15px;
            text-align: center;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
            position: relative;
            z-index: 1;
            color: #ecf0f1;
            letter-spacing: 0.5px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 10px;
            position: relative;
            margin-top: 5px;
        }
        .metric-card-inner {
            background: rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.2s ease;
        }
        .metric-card-inner:hover {
            transform: translateY(-2px);
            background: rgba(255,255,255,0.12);
            border-color: rgba(255,255,255,0.2);
        }
        .metric-label {
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 6px;
            opacity: 0.85;
            color: #bdc3c7;
        }
        .metric-value {
            font-size: 1.4em;
            font-weight: 700;
            margin-bottom: 4px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            color: #ecf0f1;
        }
        .metric-subtext {
            font-size: 0.7em;
            opacity: 0.75;
            font-weight: 500;
            color: #95a5a6;
        }
        .metric-icon {
            font-size: 1.5em;
            margin-bottom: 8px;
            opacity: 0.9;
            color: #3498db;
        }
        .metric-card {
            background: rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.2s ease;
            position: relative;
        }
        
        .metric-card::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            border-radius: 8px;
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 100%);
            opacity: 0;
            transition: opacity 0.2s ease;
        }
        
        .metric-card:hover::after {
            opacity: 1;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            background: rgba(255,255,255,0.12);
            border-color: rgba(255,255,255,0.2);
        }
        .lga-label {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            font-size: 12px !important;
            font-weight: bold !important;
            color: #333399 !important;
            text-shadow: 1px 1px 1px #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)

def display_main_header():
    """Display the main application header."""
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown("""
            <div class="main-header">
                <h1>🌆 Lagos Accessibility Dashboard</h1>
                <p>Advanced transportation analysis and accessibility modeling for Lagos Metropolitan Area</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🔄 Refresh Data", type="secondary", help="Reload all data files"):
            st.cache_data.clear()
            st.rerun()

def display_combined_header(analysis_config: AnalysisConfig):
    """Render a single combined box with header, analysis and instructions."""
    analysis_text = (
        "Set a time threshold and see how many jobs are accessible within that time."
        if analysis_config.analysis_type == "Accessibility"
        else f"Time Mapping Mode — Using {analysis_config.time_band}-minute time bands. Click zones to color by travel time from the selected origin."
    )
    instructions_text = (
        "Interact with the map to explore accessibility and travel times across Lagos. Use the sidebar to adjust settings and compare scenarios."
    )
    st.markdown(
        f"""
        <div class="main-header" style="text-align:left;">
            <h1>🌆 Lagos Accessibility Dashboard</h1>
            <p>Advanced transportation analysis and accessibility modeling for Lagos Metropolitan Area</p>
            <div style="background: rgba(255,255,255,0.12); padding: 10px 12px; border-radius: 10px; margin-top: 8px;">
                <p style="margin:0 0 6px 0;"><strong>📊 Analysis:</strong> {analysis_text}</p>
                <p style="margin:0;"><strong>💡 Instructions:</strong> {instructions_text}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def display_sidebar_settings(analysis_config: AnalysisConfig, available_attributes, attribute_display_names):
    """Display sidebar settings and return updated configuration."""

    st.sidebar.subheader("📈 Analysis Type")

    analysis_type = st.sidebar.radio(
        "Select Analysis Type",
        ["Accessibility", "Time Mapping"],
        index=0 if analysis_config.analysis_type == "Accessibility" else 1,
        key="analysis_type_radio"
    )
    
    analysis_config.analysis_type = analysis_type

    # Mode-specific settings
    if analysis_type == "Accessibility":
        # Filter out unwanted attributes
        unwanted_attributes = ['area', 'macrozone', 'lga_id', 'density lv', 'socio_eco', 'socio_eco(', 'external', 'lusep_2024', 'luses_2024', 'lusep_2048', 'luses_2048']
        filtered_attributes = [attr for attr in available_attributes if attr.lower() not in [unwanted.lower() for unwanted in unwanted_attributes]]
        
        # Show only filtered original column names
        options = filtered_attributes.copy()
        
        # Find current selection index
        current_index = 0
        for i, option in enumerate(options):
            if option == analysis_config.selected_attribute:
                current_index = i
                break
        
        # Create the selectbox
        selected_option = st.sidebar.selectbox(
            "Select attribute to analyze",
            options=options,
            index=current_index
        )
        
        # Direct assignment - no translation needed
        analysis_config.selected_attribute = selected_option
        
        # Clean time threshold slider with simple snap points
        st.sidebar.markdown("---")
        st.sidebar.subheader("⏱️ Time Settings")
        
        # Main time threshold slider - primary control
        time_threshold_temp = st.sidebar.slider(
            "Max travel time", 
            1, 120, 
            analysis_config.time_threshold,
            step=1,
            key="time_threshold_slider"
        )
        
        # Quick selection dropdown - convenience feature positioned below slider
        col1, col2 = st.sidebar.columns([2, 1])
        
        with col1:
            st.write("Quick presets:")
        
        with col2:
            common_times = [15, 30, 45, 60]
            selected_quick = st.selectbox(
                "⚡",
                ["Custom"] + common_times,
                index=0 if time_threshold_temp not in common_times else common_times.index(time_threshold_temp) + 1,
                key="quick_time_select",
                label_visibility="collapsed"
            )
        
        # Apply quick selection if chosen (this will trigger rerun and update slider)
        if selected_quick != "Custom" and selected_quick != time_threshold_temp:
            # Update the analysis config immediately so slider reflects the change on rerun
            analysis_config.time_threshold = selected_quick
            st.rerun()
        
        # Simple debouncing - only apply if value is stable
        if 'last_threshold' not in st.session_state:
            st.session_state.last_threshold = analysis_config.time_threshold
            st.session_state.threshold_counter = 0
        
        if time_threshold_temp == st.session_state.last_threshold:
            st.session_state.threshold_counter += 1
        else:
            st.session_state.threshold_counter = 0
            st.session_state.last_threshold = time_threshold_temp
        
        # Apply after 2 stable runs (user released slider)
        if st.session_state.threshold_counter >= 2:
            analysis_config.time_threshold = time_threshold_temp
    else:  # Time Mapping mode
        analysis_config.time_threshold = 45
        analysis_config.time_band = st.sidebar.selectbox(
            "Time bands (minutes)",
            options=[5, 10, 15],
            index=[5, 10, 15].index(analysis_config.time_band) if analysis_config.time_band in [5, 10, 15] else 2
        )
    
    return analysis_config

def display_file_upload_section():
    """Display file upload section and return uploaded file info."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("📂 Compare Scenarios")

    uploaded_file = st.sidebar.file_uploader(
        "Upload comparison scenario (node-based)", 
        type=["xlsx", "xls", "parquet"],
        help="Upload Excel (.xlsx, .xls) or Parquet (.parquet) file with origin_node, destination_node, and travel_time columns"
    )
    
    
    scenario_name = None
    view = "Base Scenario"
    
    if uploaded_file:
        # Handle both Excel and Parquet file extensions
        file_extension = Path(uploaded_file.name).suffix.lower()
        scenario_name = uploaded_file.name.replace(file_extension, "")
        
        view = st.sidebar.radio(
            "Show:",
            ["Base Scenario", scenario_name, "Difference"],
            key="view_radio"
        )
        
        # Show different success messages based on file type
        if file_extension == '.parquet':
            st.sidebar.success(f"🚀 Parquet file '{scenario_name}' loaded successfully!")
            st.sidebar.info("⚡ Fast loading enabled!")
        else:
            st.sidebar.success(f"✅ Excel file '{scenario_name}' loaded successfully!")
            st.sidebar.info("💡 Consider converting to Parquet for faster loading")
    
    return uploaded_file, scenario_name, view

def display_map_settings():
    """Display clean map settings and return configuration."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🗺️ Map Settings")
    
    # Zone styling
    st.sidebar.markdown("**Zone Styling**")
    fill_opacity = st.sidebar.slider("Fill opacity", 0.0, 1.0, 0.7, step=0.05)
    line_weight = st.sidebar.slider("Border weight", 0.0, 3.0, 0.5, step=0.1)
    show_labels = st.sidebar.checkbox("Show zone IDs", value=False)

    # LGA Layer Controls
    st.sidebar.markdown("**Administrative Boundaries**")
    show_lga_layer = st.sidebar.checkbox("Show LGA boundaries", value=False)
    
    if show_lga_layer:
        col1, col2 = st.sidebar.columns([2, 1])
        with col1:
            lga_border_color = st.sidebar.color_picker("Border color", "#333399")
        with col2:
            lga_border_weight = st.sidebar.slider("Weight", 0.5, 5.0, 2.0, step=0.1)
        show_lga_labels = st.sidebar.checkbox("Show LGA names", value=False)
    else:
        lga_border_color = "#333399"
        lga_border_weight = 2.0
        show_lga_labels = False
    
    return {
        'fill_opacity': fill_opacity,
        'line_weight': line_weight,
        'show_labels': show_labels,
        'show_lga_layer': show_lga_layer,
        'lga_border_color': lga_border_color,
        'lga_border_weight': lga_border_weight,
        'show_lga_labels': show_lga_labels
    }

def get_access_level_from_value(value: float, zones_df: gpd.GeoDataFrame, col: str) -> str:
    """Convert accessibility value to meaningful Low/Medium/High classification."""
    if pd.isna(value) or value == 0:
        return "No Access"
    
    # Get all non-zero values for comparison
    values = zones_df[col].dropna()
    values = values[values > 0]
    
    if len(values) == 0:
        return "No Data"
    
    # Calculate quantiles for classification
    q33 = values.quantile(0.33)
    q67 = values.quantile(0.67)
    
    if value <= q33:
        return "Low"
    elif value <= q67:
        return "Medium"
    else:
        return "High"

def display_zone_info(zone_id: Optional[int], zones_df: gpd.GeoDataFrame, 
                     analysis_config: AnalysisConfig, threshold: int = 45):
    """Display zone information in a beautiful panel above the map."""
    if zone_id is None:
        return
    
    # Ensure the zone exists
    zone_rows = zones_df[zones_df["ZONE_ID"] == int(zone_id)]
    if zone_rows.empty:
        return
    zone = zone_rows.iloc[0]
    
    # Get attribute display name
    attr_display_name = analysis_config.selected_attribute
    for category in ATTRIBUTE_METADATA.values():
        if analysis_config.selected_attribute in category:
            attr_display_name = category[analysis_config.selected_attribute]["name"]
            break
    
    # Format values based on view and analysis type
    if analysis_config.analysis_type == "Accessibility":
        if analysis_config.view == "Base Scenario":
            access_value = format_attribute_value(zone.get("access_A", 0), analysis_config.selected_attribute)
            # Calculate percentage of total jobs
            total_jobs = zones_df["Emp 2024"].sum()
            pct_value = f"{(zone.get('access_A', 0) / total_jobs * 100):.0f}%" if total_jobs > 0 else "N/A"
            time_period = "Base Scenario"
            icon = "🎯"
            # Get meaningful access level
            label = get_access_level_from_value(zone.get("access_A", 0), zones_df, "access_A")
        elif analysis_config.view != "Base Scenario" and analysis_config.view != "Difference" and "access_B" in zones_df.columns:
            access_value = format_attribute_value(zone.get("access_B", 0), analysis_config.selected_attribute)
            # Calculate percentage of total jobs
            total_jobs = zones_df["Emp 2024"].sum()
            pct_value = f"{(zone.get('access_B', 0) / total_jobs * 100):.0f}%" if total_jobs > 0 else "N/A"
            time_period = analysis_config.view
            icon = "📊"
            # Get meaningful access level
            label = get_access_level_from_value(zone.get("access_B", 0), zones_df, "access_B")
        elif analysis_config.view == "Difference":
            diff = zone.get("delta", 0)
            formatted_diff = f"+{format_attribute_value(diff, analysis_config.selected_attribute)}" if diff > 0 else format_attribute_value(diff, analysis_config.selected_attribute)
            access_value = formatted_diff
            total_jobs = zones_df["Emp 2024"].sum()
            pct_value = f"{(diff/total_jobs*100):+.0f}%" if total_jobs > 0 else "N/A"
            time_period = "Change"
            icon = "📈"
            # Get meaningful impact level
            if abs(diff) == 0:
                label = "No Change"
            elif diff > 0:
                delta_values = zones_df["delta"].dropna()
                delta_values = delta_values[delta_values > 0]
                if len(delta_values) > 0:
                    q67 = delta_values.quantile(0.67)
                    label = "High Improvement" if diff >= q67 else "Moderate Improvement"
                else:
                    label = "Improvement"
            else:
                delta_values = zones_df["delta"].dropna()
                delta_values = delta_values[delta_values < 0]
                if len(delta_values) > 0:
                    q33 = delta_values.quantile(0.33)
                    label = "High Decrease" if diff <= q33 else "Moderate Decrease"
                else:
                    label = "Decrease"
        else:
            access_value = "N/A"
            pct_value = "N/A"
            time_period = "N/A"
            icon = "❓"
            label = "No Data"
            
    else:  # Time Mapping mode
        icon = "⏱️"
        time_period = "Time Mapping"
        access_value = "Time Mapping"
        pct_value = "Click zone to see"
        label = "time bands"
    
    # Calculate additional metrics
    population = zone.get("POP_2024", 0)
    employment = zone.get("Emp 2024", 0)
    
    # Generate beautiful HTML with more professional styling
    metrics_html = f"""
    <div class="zone-info-container">
        <div class="zone-title">{icon} Zone {zone_id} • {time_period}</div>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-icon">👥</div>
                <div class="metric-label">Population</div>
                <div class="metric-value">{zone.get("POP_2024_fmt", "N/A")}</div>
                <div class="metric-subtext">Residents 2024</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">💼</div>
                <div class="metric-label">Employment</div>
                <div class="metric-value">{format_attribute_value(employment, "Emp 2024")}</div>
                <div class="metric-subtext">Jobs 2024</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">📊</div>
                <div class="metric-label">{"Change in " + analysis_config.selected_attribute + " Accessible" if analysis_config.view=="Difference" else f"{analysis_config.selected_attribute} Accessible within {threshold} min"}</div>
                <div class="metric-value">{access_value}</div>
                <div class="metric-subtext">{pct_value}</div>
            </div>
            <div class="metric-card">
                <div class="metric-icon">🎯</div>
                <div class="metric-label">{"Impact" if analysis_config.view=="Difference" else "Access Level"}</div>
                <div class="metric-value">{label}</div>
                <div class="metric-subtext">Classification</div>
            </div>
        </div>
    </div>
    """
    st.markdown(metrics_html, unsafe_allow_html=True)

def display_analysis_info(analysis_config: AnalysisConfig):
    """Display analysis information and instructions."""
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("📊 Analysis:")
        if analysis_config.analysis_type == "Accessibility":
            st.markdown('<div class="info-container"><div class="info-text">Set a time threshold and see how many jobs are accessible within that time.</div></div>', unsafe_allow_html=True)
        else:  # Time Mapping mode
            st.markdown('<div class="info-container"><div class="info-text">Click any zone on the map to see time band accessibility analysis.</div></div>', unsafe_allow_html=True)

    with col2:
        st.subheader("💡 Instructions:")
        st.markdown('<div class="info-container"><div class="info-text">Interact with the map to explore accessibility and travel times across Lagos. Use the sidebar to adjust settings and compare scenarios.</div></div>', unsafe_allow_html=True)

    # Clean Time Mapping mode info
    if analysis_config.analysis_type == "Time Mapping":
        st.info(f"🕐 **Time Mapping Mode** - Using {analysis_config.time_band}-minute time bands. Click zones to see which zones you can reach within each time interval.")

def display_time_mapping_analysis(clicked_zone_id: int, base_skim: pd.DataFrame, 
                                zones: gpd.GeoDataFrame, time_band: int):
    """Display detailed zone-to-zone analysis for Time Mapping mode."""
    st.markdown("---")
    st.subheader(f"🚗 **Zone {clicked_zone_id} Travel Analysis**")
    
    # Get travel times from the clicked zone to all other zones
    zone_travel_times = base_skim[base_skim["origin_zone"] == int(clicked_zone_id)].copy()
    
    if not zone_travel_times.empty:
        # Add destination zone information
        zone_travel_times = zone_travel_times.merge(
            zones[["ZONE_ID", "POP_2024_fmt", "Emp 2024"]], 
            left_on="destination_zone", 
            right_on="ZONE_ID", 
            how="left"
        )
        # Tables removed per request – keep compact summary only
        
        # Summary statistics
        total_accessible = len(zone_travel_times)
        total_population = zone_travel_times["POP_2024_fmt"].str.replace(",", "").astype(float).sum()
        total_employment = zone_travel_times["Emp 2024"].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Zones Accessible", f"{total_accessible:,}")
        with col2:
            st.metric("Total Population Reachable", f"{total_population:,.0f}")
        with col3:
            st.metric("Total Employment Reachable", f"{total_employment:,.0f}")
            
    else:
        st.warning(f"No travel time data found for Zone {clicked_zone_id}")
    
    # Clear button
    if st.button("✕ Clear Zone Selection", type="secondary"):
        return None  # Signal to clear the selection
    
    return clicked_zone_id  # Keep the selection

def display_statistics(total_population: int, total_employment: int):
    """Display comprehensive Lagos Metropolitan Statistics with enhanced design."""
    st.markdown("---")
    
    # Calculate additional metrics
    population_millions = total_population / 1_000_000
    employment_millions = total_employment / 1_000_000
    
    # Enhanced statistics container
    st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; padding: 30px; margin: 20px 0; color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.2); position: relative; overflow: hidden;">
            <div style="position: absolute; top: -50px; right: -50px; width: 150px; height: 150px; background: rgba(255,255,255,0.1); border-radius: 50%; opacity: 0.3;"></div>
            <div style="position: absolute; bottom: -30px; left: -30px; width: 100px; height: 100px; background: rgba(255,255,255,0.05); border-radius: 50%;"></div>
            <div style="text-align: center; margin-bottom: 30px; position: relative; z-index: 2;"><h2 style="margin: 0; font-size: 2.2em; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); letter-spacing: 1px;">🌆 Lagos Metropolitan Area</h2><p style="margin: 10px 0 0 0; font-size: 1.1em; opacity: 0.9; font-weight: 300;">Transportation Analysis Zone Statistics • 2024</p></div>
        </div>
    """, unsafe_allow_html=True)
    
    # Enhanced metrics grid
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); border-radius: 16px; padding: 25px; text-align: center; color: white; box-shadow: 0 8px 25px rgba(79, 172, 254, 0.3); transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: pointer; position: relative; overflow: hidden;" onmouseover="this.style.transform='translateY(-8px) scale(1.02)'; this.style.boxShadow='0 15px 35px rgba(79, 172, 254, 0.4)'" onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 8px 25px rgba(79, 172, 254, 0.3)'">
                <div style="font-size: 3em; margin-bottom: 10px; opacity: 0.9;">👥</div>
                <div style="font-size: 2.2em; font-weight: 700; margin-bottom: 5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">{population_millions:.1f}M</div>
                <div style="font-size: 0.9em; opacity: 0.85; font-weight: 500; margin-bottom: 8px;">Total Population</div>
                <div style="font-size: 0.75em; opacity: 0.7; background: rgba(255,255,255,0.2); padding: 4px 8px; border-radius: 12px; display: inline-block;">{total_population:,} residents</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); border-radius: 16px; padding: 25px; text-align: center; color: white; box-shadow: 0 8px 25px rgba(250, 112, 154, 0.3); transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: pointer; position: relative; overflow: hidden;" onmouseover="this.style.transform='translateY(-8px) scale(1.02)'; this.style.boxShadow='0 15px 35px rgba(250, 112, 154, 0.4)'" onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 8px 25px rgba(250, 112, 154, 0.3)'">
                <div style="font-size: 3em; margin-bottom: 10px; opacity: 0.9;">💼</div>
                <div style="font-size: 2.2em; font-weight: 700; margin-bottom: 5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">{employment_millions:.1f}M</div>
                <div style="font-size: 0.9em; opacity: 0.85; font-weight: 500; margin-bottom: 8px;">Total Employment</div>
                <div style="font-size: 0.75em; opacity: 0.7; background: rgba(255,255,255,0.2); padding: 4px 8px; border-radius: 12px; display: inline-block;">{total_employment:,} jobs</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        employment_ratio = (total_employment / total_population * 100) if total_population > 0 else 0
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); border-radius: 16px; padding: 25px; text-align: center; color: #2c3e50; box-shadow: 0 8px 25px rgba(255, 236, 210, 0.3); transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: pointer; position: relative; overflow: hidden;" onmouseover="this.style.transform='translateY(-8px) scale(1.02)'; this.style.boxShadow='0 15px 35px rgba(255, 236, 210, 0.4)'" onmouseout="this.style.transform='translateY(0) scale(1)'; this.style.boxShadow='0 8px 25px rgba(255, 236, 210, 0.3)'">
                <div style="font-size: 3em; margin-bottom: 10px; opacity: 0.8;">📊</div>
                <div style="font-size: 2.2em; font-weight: 700; margin-bottom: 5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">{employment_ratio:.0f}%</div>
                <div style="font-size: 0.9em; opacity: 0.8; font-weight: 500; margin-bottom: 8px;">Employment Ratio</div>
                <div style="font-size: 0.75em; opacity: 0.7; background: rgba(44, 62, 80, 0.15); padding: 4px 8px; border-radius: 12px; display: inline-block;">jobs to population</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Additional insights section
    st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; padding: 20px; margin: 20px 0; color: white; box-shadow: 0 6px 20px rgba(0,0,0,0.15);">
            <h4 style="margin: 0 0 15px 0; font-size: 1.3em; opacity: 0.9;">💡 Key Insights</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; backdrop-filter: blur(10px);">
                    <div style="font-size: 1.1em; font-weight: 600; margin-bottom: 5px;">🌍 Metropolitan Scale</div>
                    <div style="font-size: 0.9em; opacity: 0.8;">One of Africa's largest urban areas</div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; backdrop-filter: blur(10px);">
                    <div style="font-size: 1.1em; font-weight: 600; margin-bottom: 5px;">🚗 Transportation Focus</div>
                    <div style="font-size: 0.9em; opacity: 0.8;">Analyzing accessibility patterns</div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; backdrop-filter: blur(10px);">
                    <div style="font-size: 1.1em; font-weight: 600; margin-bottom: 5px;">📈 Economic Hub</div>
                    <div style="font-size: 0.9em; opacity: 0.8;">Major employment center</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def display_accessibility_table(zones: gpd.GeoDataFrame, analysis_config: AnalysisConfig):
    """Display accessibility results table for Accessibility mode."""
    if analysis_config.analysis_type != "Accessibility":
        return
    
    st.subheader(f"Accessibility Table — {analysis_config.view}")
    
    # Ensure we have the necessary columns for the table
    available_columns = zones.columns.tolist()
    
    if analysis_config.view == "Base Scenario" and "access_A" in available_columns:
        # Create a copy of the data for display
        display_df = zones[["ZONE_ID", "access_A"]].copy()
        # Add percentage column
        total_jobs = zones["Emp 2024"].sum()
        display_df["Percentage"] = (display_df["access_A"] / total_jobs * 100).round(0)
        display_df = display_df.rename(columns={
            "access_A": f"Jobs Accessible within {analysis_config.time_threshold} min",
            "Percentage": f"% of Total Jobs"
        })
        df = display_df
    elif analysis_config.view != "Base Scenario" and analysis_config.view != "Difference" and "access_B" in available_columns:
        # Create a copy of the data for display
        display_df = zones[["ZONE_ID", "access_B"]].copy()
        # Add percentage column
        total_jobs = zones["Emp 2024"].sum()
        display_df["Percentage"] = (display_df["access_B"] / total_jobs * 100).round(0)
        display_df = display_df.rename(columns={
            "access_B": f"Jobs Accessible within {analysis_config.time_threshold} min",
            "Percentage": f"% of Total Jobs"
        })
        df = display_df
    elif analysis_config.view == "Difference" and "delta" in available_columns:
        # Create a copy of the data for display
        display_df = zones[["ZONE_ID", "delta"]].copy()
        # Add percentage column
        total_jobs = zones["Emp 2024"].sum()
        display_df["Percentage"] = (display_df["delta"] / total_jobs * 100).round(0)
        display_df = display_df.rename(columns={
            "delta": f"Change in Jobs Accessible within {analysis_config.time_threshold} min",
            "Percentage": f"% Change of Total Jobs"
        })
        df = display_df
    else:
        df = pd.DataFrame()

    if not df.empty:
        df_display = df.copy()
        for col in df_display.columns:
            if df_display[col].dtype in [int, float]:
                if "Percentage" in col or "%" in col:
                    df_display[col] = df_display[col].apply(lambda x: f"{x:.0f}%" if pd.notnull(x) else x)
                else:
                    df_display[col] = df_display[col].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else x)
        st.dataframe(df_display)
        st.download_button("Download CSV", df.to_csv(index=False), file_name="accessibility_results.csv")
    else:
        st.info("No data available for the selected view.")
