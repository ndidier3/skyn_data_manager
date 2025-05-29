# Skyn Data Manager (SDM) Overview

## Software Structure and Data Flow

### 1. Data Processing Pipeline
- **Input Data**: Raw Excel files from `Inputs/Skyn_Data_Raw`
- **Processed Data**: Python objects saved in `Inputs/Skyn_Data_PROCESSED`
- **Main Processing Script**: `workflow.py` orchestrates the complete data processing and analysis pipeline

### 2. Core Components

#### 2.1 Workflow Management (`workflow.py`)
The `Workflow` class manages the entire SDM pipeline with three main stages:
1. **Data Processing**
   - Processes raw Excel files from input folder
   - Creates `skynDataset` instances for each file
   - Handles data preprocessing stages:
     - Gap and non-wear adjustment
     - Smoothing and imputation
     - Curve identification
     - Day-level analysis
2. **Curve Analysis**
   - Runs curve features analysis using `curveFeatures` or `curveFeaturesWithEvents`
   - Generates statistical summaries and visualizations
   - Handles event matching and analysis when needed
3. **Results Export**
   - Combines and exports results from all processing stages
   - Generates comprehensive reports and visualizations

#### 2.2 SkynDataset Class (`skyn_dataset.py`)
Core class handling individual dataset processing with key methods:
- `adjust_for_gaps_and_non_wear()`: Handles device gaps and non-wear periods
- `smooth_and_impute()`: Smooths signals and imputes missing data
- `identify_curves()`: Identifies significant curves in the data
- `run_day_level_analysis()`: Performs day-level analysis
- `make_curve_graphs()`: Generates visualizations
- `set_ema_regions()`: Sets up EMA (Ecological Momentary Assessment) regions

### 3. Analysis Components

#### 3.1 Curve Features Analysis (`curveFeatures.py`)
- Analyzes individual curves and their characteristics
- Key features analyzed:
  - Duration
  - Area Under Curve (AUC)
  - Peak values
  - Rise/fall rates and durations
  - Quality metrics
- Generates statistical summaries and visualizations

#### 3.2 Curve Features with Events (`curveFeaturesWithEvents.py`)
- Extends `curveFeatures` to include event analysis
- Matches curves with self-reported events
- Analyzes event-curve relationships
- Generates event-specific statistics and visualizations

### 4. Output Organization
Results are organized in structured directories:
```
/Results/{output_folder_name}/{date}/
├── /Datasets/      # Processed data files
├── /Plots/         # Generated visualizations
└── /Model_Performance/  # Analysis results
```

### 5. Key Features

#### 5.1 Signal Processing
- Gap filling
- Non-wear detection
- Signal smoothing
- Data imputation
- Curve identification

#### 5.2 Feature Engineering
- Day-level features
- Curve features
- Event-curve matching
- Quality metrics

#### 5.3 Visualization Capabilities
- TAC (Transdermal Alcohol Concentration) plots
- Device non-wear plots
- Signal processing plots
- Event-curve matching visualizations

### 6. Error Handling
- Comprehensive error logging
- Graceful failure handling
- Error logs saved in dedicated directory

### 7. Configuration and Customization
- Flexible processing pipeline
- Configurable parameters for:
  - Signal processing
  - Curve identification
  - Event matching
  - Analysis settings

## Usage Notes
1. Start with raw data in `Inputs/Skyn_Data_Raw`
2. Create a `Workflow` instance with project settings
3. Run processing stages using `process_data()`
4. Run analysis using `analyze_curves()`
5. Export results using `export_results()`
6. Review generated reports in the Results directory

## Output Files
- Excel workbooks with multiple tabs for different analyses
- Python objects (.sdp files) for processed data
- Various plots and visualizations
- Statistical summaries and reports 