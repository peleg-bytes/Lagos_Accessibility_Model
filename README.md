# 🌆 Lagos Accessibility Dashboard

A comprehensive Streamlit application for analyzing and visualizing accessibility metrics and travel times across Lagos transportation zones. This dashboard provides advanced transportation analysis capabilities with interactive mapping, scenario comparison, and data export features.

## ✨ Features

### 🎯 **Analysis Types**
- **Accessibility Analysis**: Calculate jobs reachable within specified time thresholds
- **Time Mapping**: Visualize travel times between zones with interactive click functionality
- **Scenario Comparison**: Compare base vs. proposed transportation changes
- **Real-time Updates**: Dynamic analysis with instant visual feedback

### 🗺️ **Interactive Mapping**
- **Folium-based Maps**: High-performance interactive maps with multiple layers
- **Zone Highlighting**: Click zones to see detailed information and statistics
- **LGA Boundaries**: Optional administrative boundary overlays
- **Customizable Styling**: Adjust colors, opacity, and border weights

### 📊 **Data Visualization**
- **Beautiful Metrics Cards**: Gradient-styled statistics with hover effects
- **Progress Tracking**: Real-time progress bars for long operations
- **Responsive Design**: Mobile-friendly interface with adaptive layouts
- **Export Capabilities**: PNG, HTML, and CSV export options

### 🔧 **Advanced Features**
- **Session State Management**: Persistent user preferences across sessions
- **Data Validation**: Comprehensive input validation and error handling
- **Performance Optimization**: Caching, batch processing, and memory management
- **Security**: File size limits and format validation

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Chrome browser (for PNG export functionality)

### Quick Start
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Accesibility-dashboard
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the dashboard**
   ```bash
   streamlit run app.py
   ```

## 📁 Data Requirements

### Required Files
Place these files in the `Data/` directory:

- **`TAZ.geojson`**: Transportation Analysis Zones with geometry and attributes
- **`Base Scenario.xlsx`**: Base scenario travel time matrix (node-based)
- **`Lagos_Node.xlsx`**: Node-to-TAZ mapping with columns `ID` and `TAZ`
- **`LGAs.geojson`**: Local Government Area boundaries (optional)

### Data Format
- **Travel Time Matrix**: Columns: `origin_node`, `destination_node`, `travel_time`
- **Zone Attributes**: Must include `ZONE_ID`, `POP_2024`, `Emp 2024`
- **Geometry**: Valid GeoJSON geometry for zones

## 🎮 Usage Guide

### 1. **Analysis Setup**
- Select analysis type: Accessibility or Time Mapping
- Choose attribute to analyze (employment, population, facilities)
- Set time threshold for accessibility calculations

### 2. **Scenario Comparison**
- Upload comparison scenario file (Excel format)
- Switch between Base Scenario, Uploaded Scenario, and Difference views
- Analyze changes in accessibility metrics

### 3. **Interactive Mapping**
- Click zones to see detailed information
- Adjust map settings (opacity, borders, labels)
- Toggle LGA boundaries and labels
- Export maps as PNG or HTML

### 4. **Data Export**
- Export current view data as CSV
- Download high-quality map images
- Save analysis results for further processing

## ⚙️ Configuration

### `config.yaml` Settings
```yaml
# Map Configuration
default_center: [6.5244, 3.3792]  # Lagos coordinates
default_zoom: 11
map_height: 750

# Performance
cache_ttl_hours: 1
batch_size: 10000

# Export
max_file_size_mb: 50
export_formats: ["png", "html", "csv"]
```

### Environment Variables
```bash
# Optional: Set custom data directory
DATA_DIR=/path/to/data

# Optional: Set logging level
LOG_LEVEL=INFO
```

## 🔧 Customization

### Adding New Attributes
1. Update `ATTRIBUTE_METADATA` in `app.py`
2. Add new columns to your zone data
3. Include formatting and unit information

### Custom Color Schemes
1. Modify `COLOR_SCHEMES` dictionary
2. Add new color palettes for different analysis types
3. Ensure color accessibility compliance

### New Analysis Types
1. Add new analysis mode to the radio buttons
2. Implement corresponding calculation functions
3. Update visualization logic

## 📊 Performance Tips

### Large Datasets
- Use batch processing for files > 10MB
- Enable geometry simplification for complex shapes
- Adjust cache TTL based on data update frequency

### Memory Management
- Monitor memory usage with large travel time matrices
- Use streaming for very large files
- Implement data pagination if needed

## 🐛 Troubleshooting

### Common Issues

**Data Loading Errors**
- Check file paths and permissions
- Verify Excel file format and column names
- Ensure GeoJSON geometry validity

**Map Export Failures**
- Install Chrome browser for PNG export
- Check Selenium WebDriver installation
- Use HTML export as fallback

**Performance Issues**
- Reduce geometry complexity
- Increase cache TTL for stable data
- Use smaller batch sizes

### Error Logs
Check `lagos_dashboard.log` for detailed error information:
```bash
tail -f lagos_dashboard.log
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Install dev dependencies: `pip install -r requirements-dev.txt`
4. Run tests: `pytest`
5. Submit pull request

### Code Style
- Use Black for code formatting
- Follow PEP 8 guidelines
- Add type hints for functions
- Include docstrings for all functions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Lagos Metropolitan Area Transportation Authority** for data and insights
- **Streamlit Community** for the excellent web app framework
- **Folium Team** for interactive mapping capabilities
- **Open Source Contributors** for various supporting libraries

## 📞 Support

For questions, issues, or feature requests:
- Create an issue on GitHub
- Contact the development team
- Check the documentation wiki

---

**Built with ❤️ for the Lagos Metropolitan Area** 