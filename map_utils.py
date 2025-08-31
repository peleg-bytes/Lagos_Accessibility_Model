"""
Map creation and styling utilities for Lagos Accessibility Dashboard
"""
import folium
from folium.plugins import Fullscreen
import geopandas as gpd
import pandas as pd
import math
from typing import List, Tuple, Optional, Dict, Any
import logging
from branca.element import Template, MacroElement

from models import AppConfig, AnalysisConfig, MapConfig, ATTRIBUTE_METADATA

logger = logging.getLogger(__name__)

# Default time mapping color scheme fallback
DEFAULT_TIME_MAPPING_SCHEME: Dict[str, str] = {
    "0_15": "#e3f2fd",
    "15_30": "#90caf9",
    "30_45": "#42a5f5",
    "45_60": "#1976d2",
    "60_plus": "#0d47a1",
}

def ensure_time_mapping_keys(color_scheme: Dict[str, str]) -> Dict[str, str]:
    """Ensure the provided color scheme has required keys; fallback to defaults if missing."""
    try:
        if not isinstance(color_scheme, dict):
            return DEFAULT_TIME_MAPPING_SCHEME.copy()
        merged = DEFAULT_TIME_MAPPING_SCHEME.copy()
        for key, value in color_scheme.items():
            if isinstance(key, str) and isinstance(value, str):
                merged[key] = value
        # Guarantee required keys
        for req in ["0_15", "15_30", "30_45", "45_60", "60_plus"]:
            if req not in merged or not merged[req]:
                merged[req] = DEFAULT_TIME_MAPPING_SCHEME[req]
        return merged
    except Exception:
        return DEFAULT_TIME_MAPPING_SCHEME.copy()

def nice_number(x: float, round_to: int = 3) -> int:
    """Round a number to a 'nice' value for display."""
    if x == 0:
        return 0
    magnitude = 10 ** (max(0, int(math.log10(abs(x))) - (round_to - 1)))
    return int(round(x / magnitude) * magnitude)

def get_color_scale(n: int) -> List[str]:
    """Return n hex colors from a built-in palette (YlOrRd-like)."""
    palettes = {
        9: ["#ffffcc","#ffeda0","#fed976","#feb24c","#fd8d3c","#fc4e2a","#e31a1c","#bd0026","#800026"],
        8: ["#ffffcc","#ffeda0","#fed976","#feb24c","#fd8d3c","#fc4e2a","#e31a1c","#bd0026"],
        7: ["#ffffcc","#ffeda0","#fed976","#feb24c","#fd8d3c","#fc4e2a","#e31a1c"],
        6: ["#ffffcc","#ffeda0","#fed976","#feb24c","#fd8d3c","#fc4e2a"],
        5: ["#ffffcc","#ffeda0","#fed976","#feb24c","#fd8d3c"],
        4: ["#ffffcc","#ffeda0","#feb24c","#fd8d3c"],
        3: ["#ffffcc","#feb24c","#fd8d3c"],
        2: ["#ffffcc","#fd8d3c"],
        1: ["#fd8d3c"],
    }
    for k in sorted(palettes.keys(), reverse=True):
        if n >= k:
            # Interpolate if needed
            idxs = [int(round(i * (k-1)/(n-1))) for i in range(n)] if n > 1 else [0]
            return [palettes[k][i] for i in idxs]
    return ["#fd8d3c"] * n

def format_attribute_value(value: Any, attribute: str) -> str:
    """Format value based on attribute metadata or default formatting."""
    if pd.isnull(value):
        return "N/A"
    # Check metadata first
    for category in ATTRIBUTE_METADATA.values():
        if attribute in category:
            return category[attribute]["format"].format(value)
    # Default format based on the value - using only commas
    if isinstance(value, (int, float)):
        if value % 1 == 0:
            return f"{int(value):,}"
        else:
            return f"{value:,.0f}"
    return str(value)

def get_time_color(minutes: float, time_band: int, color_scheme: Dict[str, str]) -> str:
    """Get color for time mapping based on minutes and time band.
    
    Note: This function is kept for backward compatibility but the new dynamic
    coloring system in color_zones_by_origin_travel_time is preferred.
    """
    if pd.isnull(minutes):
        return "#808080"  # Gray for no data
    scheme = ensure_time_mapping_keys(color_scheme)
    # Inverted grading: closer = darker, farther = lighter
    if minutes <= time_band:
        return scheme["60_plus"]
    elif minutes <= time_band * 2:
        return scheme["45_60"]
    elif minutes <= time_band * 3:
        return scheme["30_45"]
    elif minutes <= time_band * 4:
        return scheme["15_30"]
    else:
        return scheme["0_15"]

def assign_colors_to_zones(zones: gpd.GeoDataFrame, col: str, attribute_name: str) -> Tuple[gpd.GeoDataFrame, List[float], List[str]]:
    """Assign colors to zones based on data distribution."""
    values = zones[col].dropna().sort_values()
    # Use Sturges' formula for bin count, min 4, max 7
    n_bins = min(max(4, int(math.ceil(math.log2(len(values) + 1)))), 7) if len(values) > 0 else 5
    
    # Compute bins
    if len(values) == 0:
        bins = [0, 500_000, 2_000_000, 4_500_000, 6_000_000, 10_000_000][:n_bins+1]
    else:
        quantiles = [i / n_bins for i in range(n_bins + 1)]
        bins = list(values.quantile(quantiles))
        # Round bins to nice numbers
        bins = [nice_number(b, 3) for b in bins]
        # Ensure strictly increasing bins
        for i in range(1, len(bins)):
            if bins[i] <= bins[i-1]:
                bins[i] = bins[i-1] + 1
    
    # Generate color scale
    color_list = get_color_scale(n_bins)
    
    # Assign color to each zone for map rendering
    bin_edges = bins
    def assign_color(val):
        # Special handling for zero/no access values
        if pd.isna(val) or val == 0:
            return "#f0f0f0"  # Light gray for no access
        
        for i in range(n_bins):
            if i == n_bins - 1:
                if val >= bin_edges[i]:
                    return color_list[i]
            elif bin_edges[i] <= val < bin_edges[i+1]:
                return color_list[i]
        return color_list[-1]
    
    # Assign colors and labels to zones
    zones["color"] = zones[col].apply(assign_color)
    
    # Create labels with value ranges for tooltips and legend
    def assign_label(val):
        # Special handling for zero/no access values
        if pd.isna(val) or val == 0:
            return "No Access"
        
        for i in range(n_bins):
            if i == n_bins - 1:
                if val >= bin_edges[i]:
                    return f"{format_attribute_value(bin_edges[i], attribute_name)}+"
            elif bin_edges[i] <= val < bin_edges[i+1]:
                return f"{format_attribute_value(bin_edges[i], attribute_name)} - {format_attribute_value(bin_edges[i+1], attribute_name)}"
        return f"0 - {format_attribute_value(bin_edges[1], attribute_name)}"
    
    zones["label"] = zones[col].apply(assign_label)
    
    return zones, bins, color_list

def assign_time_mapping_colors(zones_df: gpd.GeoDataFrame, total_col: str, color_scheme: Dict[str, str]) -> Tuple[gpd.GeoDataFrame, List[float], List[str]]:
    """Assign colors based on total accessibility using time mapping color scheme."""
    values = zones_df[total_col].dropna().sort_values()
    bins: List[float] = []
    colors: List[str] = []
    scheme = ensure_time_mapping_keys(color_scheme)
    
    # Create 5 color classes based on accessibility
    if len(values) > 0:
        # Use quantiles for better distribution
        quantiles = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
        bins = list(values.quantile(quantiles))
        
        # Ensure unique bins
        for i in range(1, len(bins)):
            if bins[i] <= bins[i-1]:
                bins[i] = bins[i-1] + 1
        
        # Use inverted time mapping color scheme (closer = darker)
        colors = [
            scheme["60_plus"],   # Darkest for closest
            scheme["45_60"],
            scheme["30_45"],
            scheme["15_30"],
            scheme["0_15"]      # Lightest for farthest
        ]
        
        def assign_color(val):
            # Special handling for zero/no access values
            if pd.isna(val) or val == 0:
                return "#f0f0f0"  # Light gray for no access
                
            for i in range(5):
                if i == 4:  # Last bin
                    if val >= bins[i]:
                        return colors[i]
                elif bins[i] <= val < bins[i+1]:
                    return colors[i]
            return colors[0]  # Default to first color
        
        def assign_label(val):
            # Special handling for zero/no access values
            if pd.isna(val) or val == 0:
                return "No Access"
                
            for i in range(5):
                if i == 4:  # Last bin
                    if val >= bins[i]:
                        return f"Class {i+1}"
                elif bins[i] <= val < bins[i+1]:
                    return f"Class {i+1}"
            return "Class 1"
        
        zones_df["color"] = zones_df[total_col].apply(assign_color)
        zones_df["label"] = zones_df[total_col].apply(assign_label)
        
    return zones_df, bins, colors

def color_zones_by_origin_travel_time(
    zones_df: gpd.GeoDataFrame,
    skim_df: pd.DataFrame,
    origin_zone: int,
    time_band: int,
    color_scheme: Dict[str, str]
) -> gpd.GeoDataFrame:
    """Color zones by dynamic travel time classes from a specific origin zone.
    
    Creates dynamic color classes based on actual maximum travel time from origin.
    """
    try:
        scheme = ensure_time_mapping_keys(color_scheme)
        origin_zone = int(origin_zone)
        times = skim_df[skim_df["origin_zone"] == origin_zone][["destination_zone", "travel_time"]]
        merged = zones_df.merge(
            times, left_on="ZONE_ID", right_on="destination_zone", how="left"
        )
        
        # Find actual min and max travel times (excluding nulls)
        valid_times = merged["travel_time"].dropna()
        if valid_times.empty:
            logger.warning(f"No valid travel times found for origin zone {origin_zone}")
            merged["color"] = "#808080"
            merged["label"] = "No data"
            return merged
        
        min_time = valid_times.min()
        max_time = valid_times.max()
        
        # Create dynamic classes - aim for 6-8 classes based on time range
        time_range = max_time - min_time
        if time_range <= 0:
            # All destinations have same travel time
            merged["color"] = scheme["60_plus"]  # Darkest color
            merged["label"] = f"{min_time:.0f} min"
            return merged
        
        # Create classes based on time_band intervals (e.g., 5-minute intervals)
        # Calculate how many time_band intervals we need to cover the range
        max_intervals = int(max_time / time_band) + 1
        
        # Create time band boundaries
        time_boundaries = []
        for i in range(max_intervals + 1):
            boundary = i * time_band
            time_boundaries.append(boundary)
            if boundary >= max_time:
                break
        
        # Ensure we have the final boundary
        if time_boundaries[-1] < max_time:
            time_boundaries.append(time_boundaries[-1] + time_band)
        
        num_classes = len(time_boundaries) - 1
        
        # Generate color palette (inverted: short=dark, long=light)
        colors = generate_dynamic_color_palette(scheme, num_classes)
        
        def get_time_band_color_and_label(t: float) -> tuple:
            if pd.isnull(t):
                return "#808080", "No data"
            
            # Find which time band this falls into
            class_idx = 0
            for i in range(len(time_boundaries) - 1):
                if t <= time_boundaries[i + 1]:
                    class_idx = i
                    break
            else:
                class_idx = len(time_boundaries) - 2  # Last class
            
            # Create proper time band label
            start_time = time_boundaries[class_idx]
            end_time = time_boundaries[class_idx + 1]
            
            if class_idx == len(time_boundaries) - 2:  # Last class
                label = f"{start_time:.0f}+ min"
            else:
                label = f"{start_time:.0f}-{end_time:.0f} min"
            
            return colors[class_idx], label
        
        # Apply time band coloring
        color_label_pairs = merged["travel_time"].apply(get_time_band_color_and_label)
        merged["color"] = [pair[0] for pair in color_label_pairs]
        merged["label"] = [pair[1] for pair in color_label_pairs]
        
        # Debug: Log color assignments for verification
        color_counts = merged.groupby(['color', 'label']).size().reset_index(name='count')
        logger.info(f"Created {num_classes} time band classes for origin {origin_zone} "
                   f"(range: {min_time:.0f}-{max_time:.0f} min, intervals: {time_band}min)")
        for _, row in color_counts.iterrows():
            logger.info(f"  {row['label']}: {row['count']} zones, color: {row['color']}")
        
        return merged
    except Exception as e:
        logger.error(f"Failed to color zones by origin travel time: {e}")
        return zones_df

def generate_dynamic_color_palette(base_scheme: Dict[str, str], num_classes: int) -> List[str]:
    """Generate a smooth color palette with the specified number of classes.
    
    Uses the base color scheme to create a gradient from dark (short times) to light (long times).
    """
    import colorsys
    
    # Extract colors from scheme (dark to light for inverted grading)
    # Make sure we have good contrast between colors
    base_colors = [
        base_scheme["60_plus"],   # Darkest (shortest time) - #0d47a1
        base_scheme["45_60"],     # #1976d2
        base_scheme["30_45"],     # #42a5f5 
        base_scheme["15_30"],     # #90caf9
        base_scheme["0_15"]       # Lightest (longest time) - #e3f2fd
    ]
    
    # Convert hex colors to RGB
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_to_hex(rgb):
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    # If we need fewer or equal classes than base colors, just use subset
    if num_classes <= len(base_colors):
        step = len(base_colors) / num_classes
        indices = [int(i * step) for i in range(num_classes)]
        return [base_colors[i] for i in indices]
    
    # For more classes, interpolate between base colors
    rgb_colors = [hex_to_rgb(color) for color in base_colors]
    
    # Create smooth gradient
    result_colors = []
    for i in range(num_classes):
        # Map class index to position in base color array
        pos = i * (len(rgb_colors) - 1) / (num_classes - 1)
        
        # Find surrounding colors for interpolation
        lower_idx = int(pos)
        upper_idx = min(lower_idx + 1, len(rgb_colors) - 1)
        
        if lower_idx == upper_idx:
            result_colors.append(rgb_to_hex(rgb_colors[lower_idx]))
        else:
            # Interpolate between colors
            t = pos - lower_idx
            lower_rgb = rgb_colors[lower_idx]
            upper_rgb = rgb_colors[upper_idx]
            
            interpolated_rgb = tuple(
                int(lower_rgb[j] + t * (upper_rgb[j] - lower_rgb[j]))
                for j in range(3)
            )
            result_colors.append(rgb_to_hex(interpolated_rgb))
    
    return result_colors

def create_base_map(config: MapConfig) -> folium.Map:
    """Create base map with enhanced features, proper bounds, and precise zoom control."""
    m = folium.Map(
        location=config.center, 
        zoom_start=config.zoom,
        min_zoom=8,  # Prevent zooming out too much
        max_zoom=18,  # Allow more detailed zoom levels
        world_copy_jump=False,  # Disable world wrapping
        no_wrap=True,  # Prevent horizontal wrapping
        zoom_delta=0.5,  # Smaller zoom increments (default is 1)
        wheel_debounce_time=40,  # Reduce wheel sensitivity (default is 40ms)
        zoom_animation_threshold=4  # Smoother zoom animations
    )
    
    # Add map controls
    Fullscreen().add_to(m)
    
    # Add custom zoom control with finer increments
    add_precise_zoom_control(m)
    
    return m

def create_accessibility_layer(zones: gpd.GeoDataFrame, view: str, config: MapConfig, 
                             clicked_zone_id: Optional[int] = None) -> folium.GeoJson:
    """Create accessibility zones layer."""
    zones_layer = folium.GeoJson(
        zones,
        name="Jobs Accessibility",
        style_function=lambda f: {
            "fillColor": "#FF9933" if str(f["properties"]["ZONE_ID"]) == str(clicked_zone_id) 
                        else f["properties"].get("color", "#808080"),
            "color": "red" if str(f["properties"]["ZONE_ID"]) == str(clicked_zone_id) 
                    else "black",
            "weight": 3 if str(f["properties"]["ZONE_ID"]) == str(clicked_zone_id) 
                    else config.line_weight,
            "fillOpacity": 0.9 if str(f["properties"]["ZONE_ID"]) == str(clicked_zone_id) 
                        else config.fill_opacity
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["ZONE_ID", "POP_2024_fmt", "Emp_2024_fmt"],
            aliases=["Zone", "Population", "Employment"],
            localize=True,
            sticky=True,
            labels=True,
            style="""
                background-color: #F0EFEF;
                border: 2px solid black;
                border-radius: 3px;
                box-shadow: 3px;
                padding: 5px;
            """
        )
    )
    return zones_layer

def create_time_mapping_layer(zones: gpd.GeoDataFrame, config: MapConfig, 
                            clicked_zone_id: Optional[int] = None) -> folium.GeoJson:
    """Create time mapping zones layer."""
    # Create tooltip fields and aliases
    tooltip_fields = ["ZONE_ID", "POP_2024_fmt", "Emp_2024_fmt"]
    tooltip_aliases = ["Zone", "Population", "Employment"]
    
    # If we have travel time data from a selected origin, show that instead of time bands
    if clicked_zone_id and "travel_time" in zones.columns:
        # Format travel time for display
        if "travel_time_fmt" not in zones.columns:
            import pandas as pd
            zones["travel_time_fmt"] = zones["travel_time"].apply(
                lambda x: f"{x:.0f} min" if pd.notnull(x) else "No data"
            )
        tooltip_fields.append("travel_time_fmt")
        tooltip_aliases.append(f"Travel Time from Zone {clicked_zone_id}")
    elif "total_accessible" in zones.columns:
        tooltip_fields.append("total_accessible")
        tooltip_aliases.append("Total Accessible")
    
    zones_layer = folium.GeoJson(
        zones,
        name="Transportation Zones",
        style_function=lambda f: {
            "fillColor": "#FF9933" if str(f["properties"]["ZONE_ID"]) == str(clicked_zone_id) 
                        else f["properties"].get("color", "#808080"),
            "color": "red" if str(f["properties"]["ZONE_ID"]) == str(clicked_zone_id) 
                    else "#333333",  # Darker border for better contrast
            "weight": 3 if str(f["properties"]["ZONE_ID"]) == str(clicked_zone_id) 
                    else config.line_weight,
            "fillOpacity": 0.9 if str(f["properties"]["ZONE_ID"]) == str(clicked_zone_id) 
                        else config.fill_opacity
        },
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True,
            sticky=True,
            labels=True,
            style="""
                background-color: #F0EFEF;
                border: 2px solid black;
                border-radius: 3px;
                box-shadow: 3px;
                padding: 5px;
            """
        )
    )
    return zones_layer

def add_lga_layer(m: folium.Map, lga_gdf: gpd.GeoDataFrame, config: MapConfig):
    """Add LGA boundaries layer to map."""
    # Debug: Print available columns
    logger.info(f"LGA GeoDataFrame columns: {list(lga_gdf.columns)}")
    logger.info(f"LGA GeoDataFrame sample data: {lga_gdf.head(2).to_dict('records') if len(lga_gdf) > 0 else 'No data'}")
    
    def lga_style_fn(feature):
        return {
            "fillOpacity": 0,
            "color": config.lga_border_color,
            "weight": config.lga_border_weight,
        }
    
    # Add LGA boundaries
    lga_layer = folium.GeoJson(
        lga_gdf,
        name="LGA Boundaries",
        style_function=lga_style_fn,
        control=False,
        show=True,
        overlay=False,
        interactive=False
    )
    
    # Add LGA labels if enabled
    if config.show_lga_labels:
        for idx, row in lga_gdf.iterrows():
            centroid = row.geometry.centroid
            # Create circular marker for label placement
            circle = folium.CircleMarker(
                location=[centroid.y, centroid.x],
                radius=0,
                fill=False,
                opacity=0
            )
            # Add label to marker - try multiple possible name columns
            lga_name = None
            for name_col in ['LGA_NAME', 'NAME', 'name', 'LGA', 'lga_name', 'LGANAME']:
                if name_col in lga_gdf.columns and pd.notnull(row.get(name_col)):
                    lga_name = str(row[name_col])
                    break
            
            if not lga_name:
                lga_name = f"LGA {idx}"
            circle.add_child(folium.Tooltip(
                lga_name,
                permanent=True,
                direction='center',
                sticky=False,
                opacity=0.9,
                className='lga-label'
            ))
            circle.add_to(m)  # Add directly to map instead of lga_layer
    
    lga_layer.add_to(m)

def add_zone_labels(m: folium.Map, zones_gdf: gpd.GeoDataFrame, config: MapConfig):
    """Add zone ID labels to the map."""
    if not config.show_labels:
        return
        
    try:
        logger.info(f"Adding zone labels for {len(zones_gdf)} zones")
        
        for idx, row in zones_gdf.iterrows():
            try:
                # Get zone centroid for label placement
                centroid = row.geometry.centroid
                zone_id = row.get('ZONE_ID', idx)
                
                # Create invisible marker for label placement
                circle = folium.CircleMarker(
                    location=[centroid.y, centroid.x],
                    radius=0,
                    fill=False,
                    opacity=0
                )
                
                # Add permanent label showing zone ID
                circle.add_child(folium.Tooltip(
                    f"Zone {zone_id}",
                    permanent=True,
                    direction='center',
                    sticky=False,
                    opacity=0.8,
                    className='zone-label'
                ))
                
                circle.add_to(m)
                
            except Exception as e:
                logger.warning(f"Failed to add label for zone {idx}: {e}")
                
        logger.info("Successfully added zone labels to map")
        
    except Exception as e:
        logger.error(f"Failed to add zone labels: {e}")

    # Add CSS for zone and LGA labels styling
    m.get_root().html.add_child(folium.Element("""
        <style>
        .zone-label {
            background-color: rgba(255, 255, 255, 0.9) !important;
            border: 1px solid #333 !important;
            border-radius: 3px !important;
            padding: 2px 6px !important;
            font-size: 11px !important;
            font-weight: bold !important;
            color: #333 !important;
            box-shadow: 1px 1px 3px rgba(0,0,0,0.3) !important;
        }
        .lga-label {
            background-color: rgba(255, 255, 255, 0.8) !important;
            border: 1px solid #666 !important;
            border-radius: 3px !important;
            padding: 2px 6px !important;
            font-size: 10px !important;
            font-weight: normal !important;
            color: #666 !important;
            box-shadow: 1px 1px 2px rgba(0,0,0,0.2) !important;
        }
        </style>
    """))

# ---------- Legend Utilities ----------
# HTML legend helper removed - ready for custom implementation

# Time bands legend removed - ready for custom implementation

# Quantile legend removed - ready for custom implementation

# Time bands colormap removed - ready for custom implementation

# Quantile colormap removed - ready for custom implementation

# Simple legend control removed - ready for custom implementation

# Folium colormap legend removed - ready for custom implementation

def add_recenter_control(m: folium.Map, center: List[float], zoom: int, zones_gdf=None):
    """Add a streamlit-safe recenter control using direct HTML/CSS approach like the legend."""
    try:
        lat, lng = float(center[0]), float(center[1])
    except Exception:
        lat, lng = 6.5244, 3.3792

    # Calculate TAZ layer bounds if zones data is provided
    bounds_js = f"map.setView([{lat}, {lng}], {zoom});"
    if zones_gdf is not None and len(zones_gdf) > 0:
        try:
            bounds = zones_gdf.total_bounds  # [minx, miny, maxx, maxy]
            sw_lat, sw_lng = bounds[1], bounds[0]  # southwest corner
            ne_lat, ne_lng = bounds[3], bounds[2]  # northeast corner
            bounds_js = f"map.fitBounds([[{sw_lat}, {sw_lng}], [{ne_lat}, {ne_lng}]], {{padding: [20, 20]}});"
        except Exception as e:
            logger.warning(f"Could not calculate TAZ bounds, using default center: {e}")
            bounds_js = f"map.setView([{lat}, {lng}], {zoom});"

    # Direct HTML approach - bypass Leaflet Control system entirely
    recenter_html = f"""
    <div id="recenter-control" style="
        position: absolute;
        top: 140px;
        left: 10px;
        z-index: 1000;
        background: white;
        width: 34px;
        height: 34px;
        border: 2px solid rgba(0,0,0,0.2);
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.4);
        transition: background-color 0.2s;
        user-select: none;
    " 
    title="Recenter to TAZ Layer"
    onmouseover="this.style.backgroundColor='#f0f0f0'"
    onmouseout="this.style.backgroundColor='white'"
    onclick="
        try {{
            // Find the map instance
            var mapContainer = document.querySelector('.folium-map');
            if (!mapContainer) return;
            
            var mapId = mapContainer.id;
            var map = window[mapId];
            
            if (map && map.fitBounds) {{
                {bounds_js}
                
                // Visual feedback
                this.style.backgroundColor = '#e0e0e0';
                setTimeout(() => {{
                    this.style.backgroundColor = 'white';
                }}, 150);
                
                console.log('Recenter button clicked successfully');
            }} else {{
                console.error('Map instance not found for recenter');
            }}
        }} catch (error) {{
            console.error('Error in recenter button:', error);
        }}
    ">
        🎯
    </div>
    
    <script>
    // Ensure recenter button appears after map loads
    setTimeout(function() {{
        try {{
            var mapContainer = document.querySelector('.folium-map');
            var recenterBtn = document.getElementById('recenter-control');
            
            if (mapContainer && recenterBtn) {{
                // Make sure button is properly positioned relative to map
                mapContainer.style.position = 'relative';
                console.log('Recenter control positioned successfully');
            }}
        }} catch (error) {{
            console.error('Error positioning recenter control:', error);
        }}
    }}, 500);
    </script>
    """
    
    # Add the HTML directly to the map
    m.get_root().html.add_child(folium.Element(recenter_html))
    logger.info(f"Added streamlit-safe recenter control using direct HTML approach")

def add_precise_zoom_control(m: folium.Map):
    """Add streamlit-safe zoom control using direct HTML approach like recenter button."""
    try:
        # Direct HTML approach - bypass Leaflet Control system entirely
        zoom_html = f"""
        <div id="precise-zoom-control" style="
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: white;
            border-radius: 4px;
            box-shadow: 0 1px 5px rgba(0,0,0,0.4);
            overflow: hidden;
        ">
            <div id="zoom-in-btn" style="
                width: 30px;
                height: 30px;
                line-height: 30px;
                text-align: center;
                cursor: pointer;
                border-bottom: 1px solid #ccc;
                font-size: 18px;
                font-weight: bold;
                user-select: none;
                background: white;
                color: #333;
            " 
            title="Zoom in (+0.5)"
            onmouseover="this.style.backgroundColor='#f0f0f0'"
            onmouseout="this.style.backgroundColor='white'"
            onclick="
                try {{
                    var mapContainer = document.querySelector('.folium-map');
                    if (!mapContainer) return;
                    var mapId = mapContainer.id;
                    var map = window[mapId];
                    if (map && map.setZoom) {{
                        var currentZoom = map.getZoom();
                        var newZoom = Math.min(currentZoom + 0.5, map.getMaxZoom());
                        map.setZoom(newZoom, {{animate: true}});
                        console.log('Zoom in clicked, new zoom:', newZoom);
                        
                        // Visual feedback
                        this.style.backgroundColor = '#e0e0e0';
                        setTimeout(() => {{ this.style.backgroundColor = 'white'; }}, 100);
                    }}
                }} catch (error) {{
                    console.error('Error in zoom in:', error);
                }}
            ">+</div>
            
            <div id="zoom-out-btn" style="
                width: 30px;
                height: 30px;
                line-height: 30px;
                text-align: center;
                cursor: pointer;
                font-size: 18px;
                font-weight: bold;
                user-select: none;
                background: white;
                color: #333;
            " 
            title="Zoom out (-0.5)"
            onmouseover="this.style.backgroundColor='#f0f0f0'"
            onmouseout="this.style.backgroundColor='white'"
            onclick="
                try {{
                    var mapContainer = document.querySelector('.folium-map');
                    if (!mapContainer) return;
                    var mapId = mapContainer.id;
                    var map = window[mapId];
                    if (map && map.setZoom) {{
                        var currentZoom = map.getZoom();
                        var newZoom = Math.max(currentZoom - 0.5, map.getMinZoom());
                        map.setZoom(newZoom, {{animate: true}});
                        console.log('Zoom out clicked, new zoom:', newZoom);
                        
                        // Visual feedback
                        this.style.backgroundColor = '#e0e0e0';
                        setTimeout(() => {{ this.style.backgroundColor = 'white'; }}, 100);
                    }}
                }} catch (error) {{
                    console.error('Error in zoom out:', error);
                }}
            ">−</div>
        </div>
        
        <script>
        // Enhanced wheel zoom with reduced sensitivity
        setTimeout(function() {{
            try {{
                var mapContainer = document.querySelector('.folium-map');
                if (!mapContainer) return;
                
                var mapId = mapContainer.id;
                var map = window[mapId];
                
                if (map) {{
                    // Disable default wheel zoom
                    if (map.scrollWheelZoom) {{
                        map.scrollWheelZoom.disable();
                    }}
                    
                    // Add custom wheel zoom with reduced sensitivity
                    mapContainer.addEventListener('wheel', function(e) {{
                        e.preventDefault();
                        e.stopPropagation();
                        
                        var delta = e.deltaY;
                        var currentZoom = map.getZoom();
                        var zoomIncrement = 0.25;
                        
                        if (delta < 0) {{
                            // Zoom in
                            var newZoom = Math.min(currentZoom + zoomIncrement, map.getMaxZoom());
                            map.setZoom(newZoom, {{animate: true}});
                        }} else if (delta > 0) {{
                            // Zoom out
                            var newZoom = Math.max(currentZoom - zoomIncrement, map.getMinZoom());
                            map.setZoom(newZoom, {{animate: true}});
                        }}
                    }}, {{passive: false}});
                    
                    console.log('Enhanced wheel zoom with 0.25 increments enabled');
                }}
            }} catch (error) {{
                console.error('Error setting up wheel zoom:', error);
            }}
        }}, 500);
        </script>
        """
        
        # Add the HTML directly to the map
        m.get_root().html.add_child(folium.Element(zoom_html))
        logger.info("Added streamlit-safe zoom control using direct HTML approach")
        
    except Exception as e:
        logger.error(f"Failed to add precise zoom control: {e}")

def add_map_bounds(m: folium.Map, sw: List[float], ne: List[float], viscosity: float = 0.8):
    """Restrict map panning to a bounding box and prevent endless horizontal scrolling.

    sw: [lat, lng] southwest corner
    ne: [lat, lng] northeast corner
    viscosity: 0..1 how strong the bounds snapping is
    """
    try:
        sw_lat, sw_lng = float(sw[0]), float(sw[1])
        ne_lat, ne_lng = float(ne[0]), float(ne[1])
    except Exception:
        # Fallback bounds roughly covering West/Central Africa
        sw_lat, sw_lng, ne_lat, ne_lng = 0.0, -5.0, 18.0, 16.0

    template_str = f"""
    {{% macro script(this, kwargs) %}}
    function applyMapBounds() {{
        try {{
            var mapName = '{{this._parent.get_name()}}';
            var map = window[mapName];
            
            if (!map || !map._container) {{
                setTimeout(applyMapBounds, 50);
                return;
            }}
            
            // Set bounds with enhanced compatibility
            var bounds = L.latLngBounds(
                L.latLng({sw_lat}, {sw_lng}), 
                L.latLng({ne_lat}, {ne_lng})
            );
            
            map.setMaxBounds(bounds);
            map.options.maxBoundsViscosity = {viscosity};
            map.options.worldCopyJump = false;
            map.options.continuousWorld = false;
            
            // Apply noWrap to all tile layers
            map.eachLayer(function(layer) {{
                if (layer instanceof L.TileLayer) {{
                    layer.options.noWrap = true;
                    if (layer.redraw) {{
                        layer.redraw();
                    }}
                }}
            }});
            
            // Force map update
            map.invalidateSize();
            
            console.log('Enhanced map bounds applied successfully');
            
        }} catch (error) {{
            console.error('Error applying map bounds:', error);
            setTimeout(applyMapBounds, 100);
        }}
    }}
    
    setTimeout(applyMapBounds, 50);
    {{% endmacro %}}
    """
    
    el = MacroElement()
    el._template = Template(template_str)
    m.get_root().add_child(el)
    logger.info(f"Added enhanced map bounds: SW({sw_lat}, {sw_lng}) to NE({ne_lat}, {ne_lng})")

def add_streamlit_safe_legend(m: folium.Map, legend_data: dict, opacity: float = 1.0):
    """Add a legend that works reliably in streamlit-folium."""
    try:
        legend_items = legend_data.get('items', [])
        if not legend_items:
            logger.warning("No legend items provided")
            return
        
        # Create legend HTML with enhanced positioning and opacity matching
        legend_html_parts = []
        for item in legend_items:
            # Convert hex color to rgba with the specified opacity
            hex_color = item['color'].lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16) 
                b = int(hex_color[4:6], 16)
                rgba_color = f"rgba({r}, {g}, {b}, {opacity})"
            else:
                rgba_color = item['color']  # Fallback for non-hex colors
                
            legend_html_parts.append(f"""
                <div style='display: flex; align-items: center; margin-bottom: 4px;'>
                    <span style='
                        display: inline-block;
                        width: 16px;
                        height: 16px;
                        background: {rgba_color};
                        border: 1px solid #333;
                        margin-right: 8px;
                        border-radius: 2px;
                        flex-shrink: 0;
                    '></span>
                    <span style='color: #222; font-size: 12px;'>{item['label']}</span>
                </div>
            """)
        
        legend_items_html = ''.join(legend_html_parts)
        
        template_str = f"""
        {{% macro html(this, kwargs) %}}
                        <div id='map-legend-{m._id}' style='
                    position: fixed;
                    bottom: 40px;
                    left: 20px;
            min-width: 180px;
            max-width: 250px;
            background: rgba(255,255,255,0.95);
            border: 2px solid #666;
            border-radius: 8px;
            padding: 12px;
            font-family: Arial, sans-serif;
            z-index: 9999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            backdrop-filter: blur(2px);
        '>
            <div style='
                font-weight: bold; 
                margin-bottom: 8px; 
                text-align: center;
                font-size: 13px;
                color: #333;
                border-bottom: 1px solid #ddd;
                padding-bottom: 6px;
            '>
                {legend_data.get('title', 'Legend')}
            </div>
            <div>
                {legend_items_html}
            </div>
        </div>
        
        <script>
            setTimeout(function() {{
                var legend = document.getElementById('map-legend-{m._id}');
                if (legend) {{
                    // Ensure legend is always on top and visible
                    legend.style.zIndex = '9999';
                    legend.style.pointerEvents = 'auto';
                    legend.style.display = 'block';
                    
                    // Add hover effects
                    legend.onmouseenter = function() {{
                        this.style.backgroundColor = 'rgba(255,255,255,0.98)';
                    }};
                    legend.onmouseleave = function() {{
                        this.style.backgroundColor = 'rgba(255,255,255,0.95)';
                    }};
                    
                    console.log('Streamlit-safe legend positioned successfully');
                }}
            }}, 200);
        </script>
        {{% endmacro %}}
        """
        
        legend_element = MacroElement()
        legend_element._template = Template(template_str)
        m.get_root().add_child(legend_element)
        logger.info(f"Added streamlit-safe legend with {len(legend_items)} items")
        
    except Exception as e:
        logger.error(f"Failed to add streamlit-safe legend: {e}")

def add_compatibility_fixes(m: folium.Map):
    """Add general compatibility fixes for streamlit-folium."""
    try:
        template_str = f"""
        {{% macro script(this, kwargs) %}}
        function applyCompatibilityFixes() {{
            try {{
                var mapName = '{{this._parent.get_name()}}';
                var map = window[mapName];
                
                if (!map || !map._container) {{
                    setTimeout(applyCompatibilityFixes, 100);
                    return;
                }}
                
                // Fix control positioning and z-index issues
                setTimeout(function() {{
                    var controls = document.querySelectorAll('.leaflet-control');
                    controls.forEach(function(control) {{
                        if (control.style.zIndex < 1000) {{
                            control.style.zIndex = '1000';
                        }}
                    }});
                    
                    // Ensure map responds to interactions
                    map.invalidateSize();
                    
                    console.log('Compatibility fixes applied');
                }}, 300);
                
            }} catch (error) {{
                console.error('Error applying compatibility fixes:', error);
                setTimeout(applyCompatibilityFixes, 200);
            }}
        }}
        
        setTimeout(applyCompatibilityFixes, 150);
        {{% endmacro %}}
        """
        
        fix_element = MacroElement()
        fix_element._template = Template(template_str)
        m.get_root().add_child(fix_element)
        logger.info("Added streamlit-folium compatibility fixes")
        
    except Exception as e:
        logger.error(f"Failed to add compatibility fixes: {e}")
