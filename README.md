# Big Data Pipeline for Ocean Buoy Forecast

Predicts wave height and wind speed 3-6 hours ahead for NDBC ocean buoys.

## Pipeline Flow

```
NDBC Data → Python Ingestion → HDFS (raw) → Spark (clean/compact) → Parquet → Hive
                                                                    ↓
                                                        Spark Feature Engineering
                                                                    ↓
                                              Azure ML (XGBoost / Random Forest)
                                                                    ↓
                                              Azure Function (batch every 30 min)
                                                                    ↓
                                                        Cosmos DB → Streamlit Map
```

## Tech Stack

| Layer | Tool |
|-------|------|
| Data Source | NDBC (historical + realtime) |
| Ingestion | Python |
| Storage | HDFS (raw) + Parquet (processed) |
| Processing | Apache Spark |
| Data Warehouse | Apache Hive |
| ML | Python + XGBoost / Random Forest |
| Cloud ML | Azure Machine Learning |
| Scheduling | Azure Functions |
| Database | Azure Cosmos DB |
| Frontend | Streamlit |

## Quick Start

```bash
# Start Hadoop + Spark stack
docker compose up -d

# Download NDBC data
python src/ingestion/download_ndbc.py --station 46012 --years 2020-2024

# Upload to HDFS
docker exec -it namenode hdfs dfs -mkdir -p /dataset/buoy
docker exec -it namenode hdfs dfs -put /data/ndbc/*.csv /dataset/buoy/

# Run Spark compaction + feature engineering
python src/spark/run_etl.py

# Train model (Azure ML)
python src/ml/train.py

# Run dashboard
streamlit run src/dashboard/app.py
```

## Project Structure

```
├── data/               # Raw NDBC data
├── src/
│   ├── ingestion/      # Download from NDBC
│   ├── spark/          # Compaction + feature engineering
│   ├── hive/           # DDL scripts
│   ├── ml/             # Azure ML training
│   ├── function/       # Azure Function batch scoring
│   └── dashboard/      # Streamlit frontend
├── tests/              # Unit + integration tests
├── docker-compose.yml
└── requirements.txt
```

## Data Sources

- [NDBC Historical](https://www.ndbc.noaa.gov/historical_data.shtml) — multi-year archive
- [NDBC Realtime](https://www.ndbc.noaa.gov/data/realtime2/) — last 45 days
- [Station Metadata](https://www.ndbc.noaa.gov/data/stations/station_table.txt) — lat/lon coordinates
