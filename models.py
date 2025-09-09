"""
Data models and configuration classes for Lagos Accessibility Dashboard
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)

@dataclass
class AnalysisConfig:
    """Configuration for analysis parameters."""
    analysis_type: str = "Accessibility"
    time_threshold: int = 45
    time_band: int = 15
    selected_attribute: str = "Emp 2024"
    view: str = "Base Scenario"
    scenario_name: Optional[str] = None
    clicked_zone_id: Optional[int] = None

@dataclass
class MapConfig:
    """Configuration for map display settings."""
    center: List[float] = field(default_factory=lambda: [6.5244, 3.3792])
    zoom: int = 11
    height: int = 750
    fill_opacity: float = 0.7
    line_weight: float = 0.5
    show_labels: bool = False
    show_lga_layer: bool = False
    lga_border_color: str = "#333399"
    lga_border_weight: float = 2.0
    show_lga_labels: bool = False

@dataclass
class DataPaths:
    """Paths to data files."""
    zones: str = "data/TAZ.geojson"
    base_scenario: str = "data/Base Scenario.xlsx"
    node_mapping: str = "data/Lagos_Node.xlsx"
    lgas: str = "data/LGAs.geojson"

@dataclass
class AppConfig:
    """Main application configuration."""
    data_paths: DataPaths = field(default_factory=DataPaths)
    map_config: MapConfig = field(default_factory=MapConfig)
    analysis_config: AnalysisConfig = field(default_factory=AnalysisConfig)
    
    # Performance settings
    cache_ttl_hours: int = 1
    max_file_size_mb: int = 50
    batch_size: int = 10000
    geometry_simplification: float = 0.0001
    
    # Color schemes
    color_schemes: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "time_mapping": {
            "0_15": "#00ff00",      # Bright green - very short travel time
            "15_30": "#ffff00",     # Bright yellow - short travel time
            "30_45": "#ff8000",     # Orange - medium travel time
            "45_60": "#ff0000",     # Red - long travel time
            "60_plus": "#800080"    # Purple - very long travel time
        },
        "accessibility": {
            "low": "#fee5d9",
            "medium_low": "#fcae91",
            "medium": "#fb6a4a",
            "medium_high": "#de2d26",
            "high": "#a50f15"
        },
        "time_diff": {
            "significant_improvement": "#1a9850",
            "minor_improvement": "#91cf60",
            "no_change": "#ffffbf",
            "minor_increase": "#fc8d59",
            "significant_increase": "#d73027"
        }
    })
    
    # Export settings
    export_formats: List[str] = field(default_factory=lambda: ["png", "html", "csv"])
    
    @classmethod
    def load_from_yaml(cls, config_path: str = "config.yaml") -> 'AppConfig':
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"Config file {config_path} not found, using defaults")
            return cls()
        
        try:
            with open(config_file, 'r') as f:
                yaml_config = yaml.safe_load(f)
            
            # Create configuration with validation
            config = cls()
            
            # Update data paths
            if 'data_files' in yaml_config:
                for key, value in yaml_config['data_files'].items():
                    if hasattr(config.data_paths, key):
                        setattr(config.data_paths, key, value)
            
            # Update map config
            if 'default_center' in yaml_config:
                config.map_config.center = yaml_config['default_center']
            if 'default_zoom' in yaml_config:
                config.map_config.zoom = yaml_config['default_zoom']
            if 'map_height' in yaml_config:
                config.map_config.height = yaml_config['map_height']
            
            # Update other settings
            if 'cache_ttl_hours' in yaml_config:
                config.cache_ttl_hours = yaml_config['cache_ttl_hours']
            if 'max_file_size_mb' in yaml_config:
                config.max_file_size_mb = yaml_config['max_file_size_mb']
            
            # Update color schemes if provided
            if 'colors' in yaml_config:
                config.color_schemes.update(yaml_config['colors'])
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return cls()
    
    def save_to_yaml(self, config_path: str = "config.yaml"):
        """Save current configuration to YAML file."""
        config_dict = {
            'default_center': self.map_config.center,
            'default_zoom': self.map_config.zoom,
            'map_height': self.map_config.height,
            'cache_ttl_hours': self.cache_ttl_hours,
            'max_file_size_mb': self.max_file_size_mb,
            'batch_size': self.batch_size,
            'geometry_simplification': self.geometry_simplification,
            'export_formats': self.export_formats,
            'colors': self.color_schemes,
            'data_files': {
                'zones': self.data_paths.zones,
                'base_scenario': self.data_paths.base_scenario,
                'node_mapping': self.data_paths.node_mapping,
                'lgas': self.data_paths.lgas
            }
        }
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")

# Attribute metadata for display and formatting
ATTRIBUTE_METADATA = {
    "demographic": {
        "Emp 2024": {"name": "Jobs", "unit": "jobs", "format": "{:,.0f}"}
    },
    "facilities": {
        "HEALTH_BLDG": {"name": "Healthcare Facilities", "unit": "facilities", "format": "{:,.0f}"},
        "EDU_PRIM24": {"name": "Primary Schools 2024", "unit": "schools", "format": "{:,.0f}"},
        "EDU_SEC24": {"name": "Secondary Schools 2024", "unit": "schools", "format": "{:,.0f}"},
        "EDU_UNI24": {"name": "Universities 2024", "unit": "schools", "format": "{:,.0f}"},
        "EDU_PRIM48": {"name": "Primary Schools 2048", "unit": "schools", "format": "{:,.0f}"},
        "EDU_SEC48": {"name": "Secondary Schools 2048", "unit": "schools", "format": "{:,.0f}"},
        "EDU_UNI48": {"name": "Universities 2048", "unit": "schools", "format": "{:,.0f}"},
        "edu_agg_24": {"name": "Education Facilities 2024", "unit": "facilities", "format": "{:,.0f}"},
        "HLT_BLDG": {"name": "Healthcare Buildings", "unit": "facilities", "format": "{:,.0f}"}
    }
}
