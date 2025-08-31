"""
Export utilities for Lagos Accessibility Dashboard
"""
import folium
import tempfile
import time
import streamlit as st
import pandas as pd
import geopandas as gpd
from typing import Optional, Dict, Any
import logging
from pathlib import Path

from models import AnalysisConfig

logger = logging.getLogger(__name__)

def export_map_as_png(map_object: folium.Map, filename: str = "exported_map.png", 
                     map_data: Optional[Dict[str, Any]] = None, 
                     include_legend: bool = True, 
                     high_quality: bool = True) -> str:
    """Export a Folium map as a PNG image using Selenium with proper map extent and legend."""
    try:
        # Always use the original map object to preserve all layers and styling
        export_map = map_object
        
        # Save map to a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmpfile:
            export_map.save(tmpfile.name)
            map_path = tmpfile.name

        # Set up headless Chrome with larger window for better quality
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Set window size based on quality setting
        if high_quality:
            chrome_options.add_argument("--window-size=1920,1080")  # High resolution
            chrome_options.add_argument("--force-device-scale-factor=1.5")  # Higher DPI for crisp images
        else:
            chrome_options.add_argument("--window-size=1600,1200")  # Standard resolution
        
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")

        # Initialize Chrome driver properly
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get("file://" + map_path)
        
        # If we have map data, try to set the view using JavaScript
        if map_data and isinstance(map_data, dict):
            current_center = map_data.get('center', [6.5244, 3.3792])
            current_zoom = map_data.get('zoom', 11)
            
            # Use JavaScript to set the map view to the current state
            js_code = f"""
            if (typeof map !== 'undefined') {{
                map.setView([{current_center[0]}, {current_center[1]}], {current_zoom});
            }}
            """
            try:
                driver.execute_script(js_code)
                time.sleep(2)  # Wait for the view to update
            except:
                pass  # If JavaScript fails, continue with default view
        
        # Wait for map to fully load and render all layers
        initial_wait = 8 if not high_quality else 10
        time.sleep(initial_wait)
        
        # Hide unnecessary UI elements and prepare for clean export
        cleanup_js = """
        // Hide scrollbars
        document.body.style.overflow = 'hidden';
        document.documentElement.style.overflow = 'hidden';
        
        // Hide any visible scrollbars in containers
        var containers = document.querySelectorAll('*');
        for (var i = 0; i < containers.length; i++) {
            var elem = containers[i];
            if (elem.scrollHeight > elem.clientHeight || elem.scrollWidth > elem.clientWidth) {
                elem.style.overflow = 'hidden';
            }
        }
        
        // Find and hide the recenter button (bullseye)
        var recenterButtons = document.querySelectorAll('[title*="recenter"], [title*="Recenter"], .leaflet-control-recenter');
        recenterButtons.forEach(function(btn) {
            btn.style.display = 'none';
        });
        
        // Also try to hide any custom control buttons
        var customControls = document.querySelectorAll('.leaflet-control-custom, [id*="recenter"]');
        customControls.forEach(function(ctrl) {
            ctrl.style.display = 'none';
        });
        
        // Add CSS to hide scrollbars but preserve map visibility
        var style = document.createElement('style');
        style.textContent = `
            body { 
                margin: 0; 
                padding: 0; 
                overflow: hidden !important;
            }
            html { 
                overflow: hidden !important;
            }
            ::-webkit-scrollbar { 
                display: none !important; 
            }
            * { 
                scrollbar-width: none !important; 
                -ms-overflow-style: none !important;
            }
            /* Ensure map remains visible and properly sized */
            .folium-map { 
                background: white !important;
            }
            .leaflet-container {
                background: white !important;
            }
        `;
        document.head.appendChild(style);
        
        // Wait for styles to apply
        setTimeout(function() {
            // Force map to refresh and ensure it's visible
            var mapContainer = document.querySelector('.leaflet-container');
            if (mapContainer && window.map) {
                try {
                    window.map.invalidateSize();
                } catch(e) {
                    console.log('Map invalidateSize failed:', e);
                }
            }
        }, 500);
        
        return 'UI cleanup completed';
        """
        
        try:
            cleanup_result = driver.execute_script(cleanup_js)
            logger.info(f"UI cleanup: {cleanup_result}")
            time.sleep(2)  # Extended wait for CSS changes and map refresh
        except Exception as cleanup_e:
            logger.warning(f"UI cleanup failed: {cleanup_e}")
        
        # Additional wait and check for legend if requested
        if include_legend:
            try:
                # Check if legend is present and visible
                legend_check_js = """
                var legends = document.querySelectorAll('[id*="map-legend"]');
                if (legends.length > 0) {
                    var legend = legends[0];
                    var style = window.getComputedStyle(legend);
                    return style.display !== 'none' && style.visibility !== 'hidden' && legend.offsetHeight > 0;
                }
                return false;
                """
                legend_present = driver.execute_script(legend_check_js)
                if legend_present:
                    time.sleep(2)  # Extra time for legend rendering
                    logger.info("Legend detected and rendered for export")
                else:
                    logger.warning("Legend not found in export - may not be visible in current view")
            except Exception as legend_e:
                logger.warning(f"Legend detection failed: {legend_e}")
        
        # Verify map is visible before taking screenshot
        map_visibility_js = """
        var mapContainer = document.querySelector('.leaflet-container');
        if (mapContainer) {
            var style = window.getComputedStyle(mapContainer);
            var rect = mapContainer.getBoundingClientRect();
            return {
                display: style.display,
                visibility: style.visibility,
                opacity: style.opacity,
                width: rect.width,
                height: rect.height,
                hasContent: mapContainer.children.length > 0
            };
        }
        return null;
        """
        
        try:
            map_info = driver.execute_script(map_visibility_js)
            if map_info:
                logger.info(f"Map visibility check: {map_info}")
            else:
                logger.warning("Map container not found for visibility check")
        except Exception as visibility_e:
            logger.warning(f"Map visibility check failed: {visibility_e}")
        
        # Take screenshot with error handling - use full page for reliability
        try:
            png = driver.get_screenshot_as_png()
            logger.info(f"Screenshot captured successfully - size: {len(png)} bytes")
        except Exception as screenshot_e:
            logger.error(f"Screenshot capture failed: {screenshot_e}")
            raise screenshot_e
        finally:
            driver.quit()

        # Save PNG to a temporary file and return its path
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as pngfile:
            pngfile.write(png)
            return pngfile.name
            
    except Exception as e:
        # Fallback method using HTML export with instructions
        logger.warning(f"Selenium export failed: {str(e)}")
        return create_html_export_fallback(map_object, filename)

def create_html_export_fallback(map_object: folium.Map, filename: str) -> str:
    """Create HTML export as fallback when PNG export fails."""
    map_html = map_object._repr_html_()
    complete_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Lagos Accessibility Map</title>
        <style>
            body {{
                margin: 0;
                padding: 20px;
                background: white;
                font-family: Arial, sans-serif;
            }}
            .map-container {{
                width: 100%;
                height: 600px;
                border: 2px solid #333;
                border-radius: 8px;
                overflow: hidden;
                position: relative;
            }}
            .title {{
                text-align: center;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
                color: #333;
            }}
            .export-info {{
                text-align: center;
                font-size: 14px;
                color: #666;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="title">Lagos Accessibility Analysis</div>
        <div class="map-container">
            {map_html}
        </div>
        <div class="export-info">
            <p>To save as PNG: Right-click on the map and select "Save image as..." or use your browser's print function (Ctrl+P) and save as PDF/PNG</p>
        </div>
    </body>
    </html>
    """
    return complete_html

def create_data_export(zones: gpd.GeoDataFrame, analysis_config: AnalysisConfig) -> pd.DataFrame:
    """Create data export based on current analysis configuration."""
    if analysis_config.analysis_type == "Accessibility":
        if analysis_config.view == "Base Scenario" and "access_A" in zones.columns:
            export_df = zones[["ZONE_ID", "access_A"]].copy()
            export_df.columns = ["Zone ID", f"Jobs Accessible within {analysis_config.time_threshold} min"]
        elif analysis_config.view != "Base Scenario" and analysis_config.view != "Difference" and "access_B" in zones.columns:
            export_df = zones[["ZONE_ID", "access_B"]].copy()
            export_df.columns = ["Zone ID", f"Jobs Accessible within {analysis_config.time_threshold} min"]
        elif analysis_config.view == "Difference" and "delta" in zones.columns:
            export_df = zones[["ZONE_ID", "delta"]].copy()
            export_df.columns = ["Zone ID", f"Change in Jobs Accessible within {analysis_config.time_threshold} min"]
        else:
            export_df = zones[["ZONE_ID"]].copy()
    else:
        # For Time Mapping, export basic zone data
        export_df = zones[["ZONE_ID", "POP_2024", "Emp 2024"]].copy()
        export_df.columns = ["Zone ID", "Population 2024", "Employment 2024"]
    
    return export_df

def display_export_section(map_object: folium.Map, zones: gpd.GeoDataFrame, 
                         analysis_config: AnalysisConfig, map_data: Optional[Dict[str, Any]] = None):
    """Display export section in sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
        <div class="sidebar-section">
            <h4>📸 Export & Download</h4>
        </div>
    """, unsafe_allow_html=True)

    export_filename = st.sidebar.text_input(
        "Export filename", 
        value=f"lagos_{analysis_config.analysis_type.lower().replace(' ', '_')}_{analysis_config.view.lower().replace(' ', '_')}.png",
        help="Choose a filename for your export"
    )
    
    # Export options
    st.sidebar.markdown("**🎛️ Export Options**")
    include_legend = st.sidebar.checkbox("Include legend", value=True, help="Include the map legend in the export")
    high_quality = st.sidebar.checkbox("High quality", value=True, help="Use higher resolution for better image quality")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("🖼️ Export PNG", type="primary"):
            with st.spinner("Generating PNG export..."):
                try:
                    # Create a more detailed map data object with current state
                    export_map_data = {
                        'center': map_data.get('center', [6.5244, 3.3792]) if map_data else [6.5244, 3.3792],
                        'zoom': map_data.get('zoom', 11) if map_data else 11,
                        'map_object': map_object
                    }
                    
                    result = export_map_as_png(
                        map_object, 
                        export_filename, 
                        export_map_data, 
                        include_legend=include_legend, 
                        high_quality=high_quality
                    )
                    
                    # Check if result is a file path (PNG) or HTML content
                    if isinstance(result, str) and result.endswith('.png'):
                        # PNG export successful
                        with open(result, "rb") as f:
                            st.sidebar.download_button(
                                label="📥 Download PNG",
                                data=f.read(),
                                file_name=export_filename,
                                mime="image/png"
                            )
                        quality_msg = "high quality" if high_quality else "standard quality"
                        legend_msg = "with legend" if include_legend else "without legend"
                        st.sidebar.success(f"✅ Map PNG exported successfully! ({quality_msg}, {legend_msg})")
                    else:
                        # HTML fallback
                        html_filename = export_filename.replace('.png', '.html')
                        st.sidebar.download_button(
                            label="📥 Download HTML",
                            data=result.encode('utf-8'),
                            file_name=html_filename,
                            mime="text/html"
                        )
                        st.sidebar.success("✅ Map HTML exported successfully!")
                        st.sidebar.info("💡 **To save as PNG:** Open the downloaded HTML file in your browser, then right-click on the map and select 'Save image as...' or use Ctrl+P to print as PDF/PNG.")
                        
                except Exception as e:
                    st.sidebar.error(f"❌ Failed to export map: {str(e)}")

    with col2:
        if st.button("📊 Export Data"):
            with st.spinner("Preparing data export..."):
                try:
                    export_df = create_data_export(zones, analysis_config)
                    csv_data = export_df.to_csv(index=False)
                    st.sidebar.success("✅ Data exported successfully!")
                    st.sidebar.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name="lagos_data.csv",
                        mime="text/csv"
                    )
                except Exception as e:
                    st.sidebar.error(f"❌ Failed to export data: {str(e)}")



def add_keyboard_shortcuts():
    """Add keyboard shortcuts to the application."""
    st.markdown("""
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'r') {
                // Ctrl+R for refresh
                window.location.reload();
            }
        });
        </script>
    """, unsafe_allow_html=True)
