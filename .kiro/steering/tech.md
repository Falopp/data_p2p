# Technology Stack

## Core Technologies
- **Python 3.8+**: Primary language with type hints and modern features
- **Polars**: High-performance DataFrame operations and data processing (preferred over Pandas)
- **Pandas**: Excel export compatibility and legacy library integrations
- **Matplotlib & Seaborn**: Static chart generation and statistical visualizations
- **Plotly**: Interactive visualizations, dashboards, and web-ready charts
- **Jinja2**: HTML report templating with custom filters and macros
- **PyYAML**: Configuration file parsing with schema validation
- **Scikit-learn**: Machine learning features (IsolationForest, clustering, regression)

## Key Libraries
- **NumPy**: Numerical computations and array operations
- **Openpyxl**: Excel file generation with formatting and charts
- **Kaleido**: Static image export for Plotly charts (headless rendering)
- **PyArrow**: Columnar data format support and interoperability
- **Requests**: HTTP client for API integrations and data fetching
- **Watchdog**: File system monitoring for real-time data updates

## Development Tools
- **Black**: Code formatting with line length 88
- **Flake8**: Linting with complexity checks
- **Pre-commit**: Git hooks for code quality and automated checks
- **Pytest**: Testing framework with fixtures and parametrization
- **MyPy**: Static type checking (recommended for new code)

## Data Processing Patterns
- **Lazy Evaluation**: Use Polars lazy frames for memory efficiency
- **Schema Validation**: Enforce data types and column presence
- **Error Handling**: Graceful degradation with informative logging
- **Memory Management**: Process large datasets in chunks when needed

## Architecture Patterns
- **Modular Design**: Separate modules for analysis, plotting, reporting, and transformations
- **Configuration-Driven**: YAML-based configuration with sensible defaults
- **CLI-First**: Command-line interface with extensive argument support
- **Pipeline Architecture**: Sequential data processing through load → transform → analyze → report stages

## Common Commands

### Setup
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Running Analysis
```bash
# Basic analysis
python src/app.py --csv data/transactions.csv

# With filters and custom output
python src/app.py --csv data/p2p.csv --out results/ --fiat_filter USD --year 2023

# Debug mode
python src/app.py --csv data/p2p.csv --log-level DEBUG
```

### Testing
```bash
# Run specific tests
python tests/test_hourly_plot.py
python tests/test_vip_plot.py
```

## Performance Considerations
- **Polars First**: Always prefer Polars over Pandas for data processing
- **Lazy Evaluation**: Use `.lazy()` for complex transformations and filtering
- **Memory Optimization**: Process only required columns, use streaming for large files
- **Caching Strategy**: Cache expensive computations and intermediate results
- **Parallel Processing**: Leverage Polars' built-in parallelization
- **Profiling**: Use `cProfile` and memory profilers for optimization

## Code Quality Standards
- **Type Hints**: All new functions must include comprehensive type annotations
- **Docstrings**: Use Google-style docstrings for all public functions
- **Error Handling**: Specific exception types with descriptive messages
- **Logging**: Structured logging with appropriate levels (DEBUG, INFO, WARNING, ERROR)
- **Testing**: Minimum 80% code coverage for new features
- **Documentation**: Update README and inline docs for user-facing changes

## Security Guidelines
- **Input Validation**: Sanitize all user inputs and file paths
- **File Operations**: Use pathlib.Path for cross-platform compatibility
- **Configuration**: Never hardcode sensitive values, use environment variables
- **Dependencies**: Regular security audits with `pip-audit` or similar tools