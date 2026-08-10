# Big Data Pipeline for Ocean Buoy Forecast

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a full pipeline that ingests NDBC buoy data, engineers features, trains an ML model to predict wave height/wind speed 3-6 hours ahead, and displays results on an interactive world map.

**Architecture:** 
- Data Layer: NDBC NOAA (historical + realtime) → HDFS → Hive
- Processing: Spark for compaction + feature engineering (Parquet format)
- ML: Azure ML with XGBoost + Random Forest regression (HyperDrive tuning)
- Serving: Azure Function (timer-triggered batch scoring) → Cosmos DB
- Frontend: Streamlit + Folium interactive map

**Tech Stack:** Python, PySpark, Hive, Azure ML, Azure Functions, Cosmos DB, Streamlit

---

## Data Sources

### Historical Archive (multi-year)
- URL: `https://www.ndbc.noaa.gov/data/historical/stdmet/{station_id}h{year}.txt.gz`
- Format: gzipped text, space-separated, 2 header lines (#YY MM... + units)
- Columns: YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
- Missing values encoded as `MM` (must convert to NaN)
- 17,050+ files available (multiple stations × years)

### Realtime (last 45 days)
- URL: `https://www.ndbc.noaa.gov/data/realtime2/{station_id}.txt`
- Same format as historical but without gzip
- 943 active stations available

### Station Metadata (NEW - needed for map coordinates)
- URL: `https://www.ndbc.noaa.gov/data/stations/station_table.txt`
- Format: pipe-delimited (`STATION_ID | OWNER | TTYPE | HULL | NAME | PAYLOAD | LOCATION | TIMEZONE | FORECAST | NOTE`)
- Contains lat/lon in format `44.794 N 87.313 W (44°47'39" N 87°18'48" W)`
- 1,936 stations with metadata

---

## Pipeline Stages

### Stage 0-2: Ingestion + HDFS + Compaction
- Download from both sources
- Upload to HDFS
- Spark job to compact small files into larger partitions

### Stage 3: Hive Tables
Two tables required:

**buoy_observations:**
- station_id, timestamp, wind_speed, wind_dir, wave_height, pressure, air_temp, water_temp
- Partitioned by date

**buoy_stations (new):**
- station_id, lat, lon, name, region
- Parsed from station_table.txt (need to convert DMS to decimal degrees)

JOIN between these two tables enables the map visualization.

### Stage 4: Feature Engineering
- Replace `MM` with NaN
- Calculate pressure drop rate (meteorologically meaningful storm signal)
- Create lag features (1h, 3h, 6h prior values)
- Additional: wind direction encoding (sin/cos), rolling statistics

### Stage 5-7: Azure ML
- Target: wave_height or wind_speed 3-6 hours ahead
- Train ONE model for all stations (include station_id as feature)
- HyperDrive for hyperparameter tuning
- Register to Model Registry

### Stage 8: Batch Scoring (Azure Function)
- Timer trigger every 30 minutes
- Wake up Managed Online Endpoint
- Fetch latest data for all stations from Hive
- Single batch inference call (all stations at once)
- Write results to Cosmos DB (station_id, lat, lon, predicted_wave_height, timestamp)
- Scale endpoint to 0 immediately after scoring completes

### Stage 9: Frontend (Streamlit + Map)
- Read from Cosmos DB directly (fast, no ML endpoint needed)
- Display all buoy points on world map
- Color by risk level: green=normal, yellow=moderate, red=high
- Click point → popup showing actual vs predicted comparison
- Search box for station_id

---

## File Structure
See `01-project-structure.md` for detailed file layout.

## Implementation Tasks
See `02-implementation-tasks.md` for bite-sized tasks.

## Data Flow Diagram
See `03-data-flow.md` for visual representation.

## Key Technical Decisions
See `04-decisions.md` for rationale behind choices.

---

## Next Steps
1. Review all plan files
2. Execute using subagent-driven-development
3. Start with Stage 0 (data ingestion scripts)
