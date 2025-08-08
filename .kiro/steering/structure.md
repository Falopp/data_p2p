# Project Structure

## Directory Organization

```
├── src/                      # Main source code
│   ├── app.py               # CLI entry point and data loading
│   ├── main_logic.py        # Analysis pipeline orchestration
│   ├── analyzer.py          # Core metrics calculation
│   ├── counterparty_analyzer.py  # Counterparty-specific analysis
│   ├── session_analyzer.py # Trading session analysis
│   ├── plotting.py          # General chart generation
│   ├── counterparty_plotting.py  # Counterparty charts
│   ├── reporter.py          # Individual report generation
│   ├── unified_reporter.py  # Consolidated reporting
│   ├── config_loader.py     # Configuration management
│   ├── finance_utils.py     # Financial calculations
│   ├── filters.py           # Data filtering utilities
│   ├── utils.py             # General utilities
│   ├── logging_config.py    # Logging setup
│   └── transformations/     # Data transformation modules
│       ├── time_features.py # Time-based feature engineering
│       ├── numeric.py       # Numeric transformations
│       └── patches.py       # Data patches/fixes
├── templates/               # HTML report templates
├── tests/                   # Test files
│   └── unit/               # Unit tests
├── data/                   # Input CSV files (user-created)
└── output/                 # Generated reports and charts
```

## Code Organization Patterns

### Module Responsibilities
- **app.py**: Entry point, argument parsing, initial data loading and filtering
- **main_logic.py**: Orchestrates analysis pipeline, manages year/status iterations
- **analyzer.py**: Core business logic for metrics calculation
- **plotting.py**: Visualization generation using matplotlib/seaborn/plotly
- **reporter.py**: Output file generation (CSV, HTML, PNG)
- **transformations/**: Modular data processing (time features, numeric conversions)

### Configuration Management
- **config_loader.py**: Centralized configuration with YAML override support
- **config.yaml**: Optional user configuration file (column mapping, analysis parameters)
- Default configuration embedded in code with external override capability

### Data Flow Architecture
1. **Load**: CSV reading with schema validation
2. **Transform**: Column mapping, time feature extraction, filtering
3. **Analyze**: Metrics calculation, counterparty analysis, session detection
4. **Report**: Multi-format output generation (CSV, PNG, HTML, Excel)

### Output Structure
```
output/
├── [Category]/              # Analysis category (e.g., "General")
│   ├── 2023/               # Year-specific analysis
│   │   ├── completadas/    # Completed orders only
│   │   │   ├── figures/    # PNG charts
│   │   │   ├── reports/    # HTML reports
│   │   │   └── tables/     # CSV metrics
│   │   ├── canceladas/     # Cancelled orders
│   │   └── todas/          # All orders
│   ├── total/              # All-time analysis
│   └── consolidated/       # Cross-period reports
```

### Naming Conventions
- **Files**: snake_case for Python modules (e.g., `counterparty_analyzer.py`)
- **Functions**: snake_case with descriptive verbs (e.g., `calculate_metrics`, `generate_report`)
- **Classes**: PascalCase with clear purpose (e.g., `AnalysisRunner`, `UnifiedReporter`)
- **Constants**: UPPER_SNAKE_CASE with module prefix (e.g., `DEFAULT_CONFIG`, `MONTH_NAMES_MAP`)
- **Variables**: snake_case with context (e.g., `df_filtered`, `metrics_dict`)
- **Internal columns**: snake_case (e.g., `match_time_utc`, `total_price`, `fiat_type`)
- **Output files**: descriptive names with category/period/status identifiers
- **Test files**: `test_` prefix matching module name (e.g., `test_analyzer.py`)

### Error Handling Patterns
- **Graceful Degradation**: Continue processing when non-critical errors occur
- **Specific Exceptions**: Use appropriate exception types (FileNotFoundError, ValueError, etc.)
- **Logging Context**: Include relevant data in error messages for debugging
- **User-Friendly Messages**: Provide actionable error messages for CLI users
- **Validation Early**: Validate inputs at module boundaries

### Testing Structure
- **Unit Tests**: `tests/unit/` for individual module testing
- **Integration Tests**: `tests/integration/` for end-to-end workflows
- **Test Data**: `tests/fixtures/` for sample CSV files and expected outputs
- **Mocking**: Mock external dependencies and file I/O operations
- **Parametrized Tests**: Use pytest.mark.parametrize for multiple test cases