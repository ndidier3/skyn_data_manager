# Time Handling Standardization Analysis

## Status: ✅ File Ready for Use

The `time_handling_BE.py` file has been updated for Python 3.8 compatibility:
- Fixed type hints (`int | None` → `Optional[int]`, etc.)
- Added `Optional` and `Tuple` to imports
- Imports successfully tested

## Key Functions Available

### Core Timestamp Utilities
- `to_naive_timestamp(value)` - Convert any value to timezone-naive pandas Timestamp
- `parse_request_timestamp(value)` - Parse with error handling
- `normalize_df_datetime(df, column_name)` - Normalize DataFrame datetime column in-place
- `find_datetime_column(df)` - Find datetime column by name (case-insensitive)

### Formatting Utilities
- `format_naive_iso(value)` - Format to 'YYYY-MM-DDTHH:MM:SS'
- `to_epoch_seconds(value)` - Convert to epoch seconds
- `format_value_iso_and_seconds(value)` - Return (iso_string, epoch_seconds) tuple

## Standardization Opportunities

### 1. `configure_timestamp_column()` in `configuration.py`

**Current Implementation:**
```python
def configure_timestamp_column(df):
    df['datetime_with_timezone'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d %H:%M:%S %z', errors='coerce')
    df['datetime_without_timezone'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    # ... complex logic to check which worked ...
```

**Recommended Refactor:**
```python
from App.SDM.Configuration.time_handling_BE import normalize_df_datetime

def configure_timestamp_column(df):
    """Standardize datetime column using centralized time handling."""
    return normalize_df_datetime(df, 'datetime')['datetime']
```

**Benefits:**
- Simpler, cleaner code
- Consistent timezone handling across codebase
- Removes intermediate column creation
- Better error handling

---

### 2. `configure_dataset_timestamps()` in `configuration.py`

**Current Implementation:**
```python
def configure_dataset_timestamps(dataset):
  try:
    dataset["datetime"] = pd.to_datetime(dataset["datetime"], unit='s')
  except:
    dataset["datetime"] = pd.to_datetime(dataset["datetime"])
  dataset["datetime"] = dataset["datetime"].dt.tz_localize(None)
  dataset = dataset.sort_values(by="datetime", ignore_index=True)
  dataset.reset_index(inplace=True, drop=True)
  return dataset
```

**Recommended Refactor:**
```python
from App.SDM.Configuration.time_handling_BE import normalize_df_datetime

def configure_dataset_timestamps(dataset):
    """Configure dataset timestamps using standardized time handling."""
    # Try epoch seconds first, then fall back to general parsing
    try:
        dataset["datetime"] = pd.to_datetime(dataset["datetime"], unit='s', errors='coerce')
    except:
        pass
    
    # Normalize using centralized function (handles timezone removal)
    dataset = normalize_df_datetime(dataset, "datetime")
    
    # Sort and reset index
    dataset = dataset.sort_values(by="datetime", ignore_index=True)
    dataset.reset_index(inplace=True, drop=True)
    return dataset
```

**Benefits:**
- Consistent timezone handling
- Reuses tested normalization logic
- Maintains existing behavior (epoch seconds support)

---

### 3. `get_closest_index_with_timestamp()` and `get_closest_index_after_timestamp()`

**Current Implementation:**
```python
def get_closest_index_with_timestamp(data, timestamp, datetime_column='datetime', time_diff_limit_hours=None):
  try:
    time_diff = (data[datetime_column] - timestamp).abs()
    # ...
```

**Recommended Enhancement:**
```python
from App.SDM.Configuration.time_handling_BE import to_naive_timestamp, find_datetime_column

def get_closest_index_with_timestamp(data, timestamp, datetime_column='datetime', time_diff_limit_hours=None):
    """Find closest index using standardized timestamp parsing."""
    # Auto-detect datetime column if not specified
    if datetime_column is None:
        datetime_column = find_datetime_column(data)
        if datetime_column is None:
            raise ValueError("No datetime column found in data")
    
    # Normalize timestamp input
    timestamp = to_naive_timestamp(timestamp)
    if pd.isna(timestamp):
        raise ValueError(f"Invalid timestamp: {timestamp}")
    
    # Ensure data datetime column is normalized
    data = normalize_df_datetime(data.copy(), datetime_column)
    
    # Rest of existing logic...
```

**Benefits:**
- Robust timestamp parsing from various input types
- Auto-detection of datetime columns
- Consistent normalization

---

### 4. `get_event_timestamps()` in `configuration.py`

**Current Implementation:**
```python
def get_event_timestamps(self, metadata_path):
    timestamps[timestamp_columns] = timestamps[timestamp_columns].apply(
        pd.to_datetime, format='%Y-%m-%d %H:%M', errors='coerce'
    )
```

**Recommended Refactor:**
```python
from App.SDM.Configuration.time_handling_BE import normalize_df_datetime

def get_event_timestamps(self, metadata_path):
    # ... existing code ...
    for col in timestamp_columns:
        if col in timestamps.columns:
            timestamps = normalize_df_datetime(timestamps, col)
```

**Benefits:**
- More flexible parsing (not limited to specific format)
- Consistent timezone handling
- Better error handling

---

### 5. `configure_event_data()` in `skyn_dataset.py`

**Current Implementation:**
```python
# Convert timestamp columns to datetime
for col in event_timestamp_columns:
    if col in self.events.columns:
        self.events[col] = pd.to_datetime(self.events[col], errors='coerce')
```

**Recommended Refactor:**
```python
from App.SDM.Configuration.time_handling_BE import normalize_df_datetime

# Convert timestamp columns to datetime
for col in event_timestamp_columns:
    if col in self.events.columns:
        self.events = normalize_df_datetime(self.events, col)
```

**Benefits:**
- Consistent timestamp normalization
- Automatic timezone handling
- Cleaner code

---

## Implementation Priority

### High Priority (Immediate Benefits)
1. ✅ **File is ready** - Type hints fixed, imports work
2. **`configure_dataset_timestamps()`** - Used frequently, easy refactor
3. **`configure_event_data()`** - Critical path, affects event matching

### Medium Priority (Code Quality)
4. **`configure_timestamp_column()`** - Can simplify complex logic
5. **`get_closest_index_with_timestamp()`** - Add robustness

### Low Priority (Nice to Have)
6. **`get_event_timestamps()`** - Less frequently used
7. **Other timestamp parsing locations** - As discovered

## Testing Recommendations

1. **Unit Tests**: Test each refactored function with:
   - Timezone-aware timestamps
   - Timezone-naive timestamps
   - Epoch seconds
   - String formats
   - Invalid inputs

2. **Integration Tests**: Verify:
   - Event matching still works correctly
   - Curve identification timestamps are correct
   - Day-level analysis date calculations

3. **Regression Tests**: Compare outputs before/after refactoring

## Migration Strategy

1. **Phase 1**: Update `time_handling_BE.py` imports in target files
2. **Phase 2**: Refactor one function at a time, test thoroughly
3. **Phase 3**: Update all timestamp parsing to use centralized functions
4. **Phase 4**: Remove duplicate timestamp handling code

## Notes

- The `time_handling_BE.py` file enforces a **timezone-naive policy**, which aligns with the existing codebase behavior
- All functions handle errors gracefully (return `NaT` or `None` rather than raising)
- The file is well-documented and follows the project's coding patterns


