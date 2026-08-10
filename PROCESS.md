# Process Log

## Stage 0: Ingestion (Done)

### What we built
- `src/ingestion/download_ndbc.py` — download historical (.txt.gz) + realtime (.txt) + station list with retry
- `src/ingestion/parse_ndbc.py` — parse gzip/text → DataFrame, MM → NaN, timestamp build, column selection

### Selected Stations (9 total)

| Region | Station | Location |
|--------|---------|----------|
| Atlantic | 41001 | Edisto, SC |
| Atlantic | 41004 | Cape Hatteras, NC |
| Atlantic | 41009 | Cape Canaveral, FL |
| Atlantic | 41040 | Caribbean Sea |
| Atlantic | 44013 | Boston, MA |
| Pacific | 46012 | Monterey Bay, CA |
| Pacific | 46042 | Farallon Islands, CA |
| Gulf | 42001 | Mid Gulf |
| Gulf | 42002 | South Gulf |

62029 (Canary Islands) originally planned but no data → replaced with 41004 + 41009

### Problem: 46012/46042 missing 2024
- **Symptom**: `46012h2024.txt.gz` and `46042h2024.txt.gz` returned 404
- **Cause**: NDBC hasn't uploaded 2024 data for these stations yet
- **Fix**: Only downloaded 2020-2023, realtime covers the gap

---

## Stage 4: Feature Engineering (Done)

### What we built
- `src/spark/features.py` — lag, rolling stats, pressure drop, wind encoding, target

### Features Created (32 cols total)

| Feature | Description |
|---------|-------------|
| wave_height_1h/3h/6h | Lag features |
| wind_speed_1h/3h/6h | Lag features |
| pressure_1h/3h/6h | Lag features |
| wave_height_roll_mean/std_3h/6h | Rolling statistics |
| wind_speed_roll_mean/std_3h/6h | Rolling statistics |
| pressure_drop_3h/6h | Storm signal |
| wind_dir_sin/cos | Cyclical encoding |
| hour_sin/cos | Cyclical encoding |
| target_wave_height_3h | Wave height 3h ahead |
| target_wind_speed_3h | Wind speed 3h ahead |

### Problem: 41009 got 0 rows after features
- **Symptom**: `41009_features.csv` → 0 rows, 32 cols
- **Cause**: water_temp = NaN 100% of rows + wave_height missing 52% (3407/6525)
- **Root cause**: `dropna()` without subset — ANY NaN column drops the row. water_temp NaN → entire row dropped
- **Fix**: Changed to `dropna(subset=essential)` — only drop if target/core features are missing, ignore non-essential cols like water_temp

```
Before: df.dropna()
After:  df.dropna(subset=["target_wave_height_3h", "wave_height", "wind_speed",
                          "pressure", "wave_height_1h", "wave_height_6h",
                          "wind_speed_1h", "wind_speed_6h"])
```

Result: 41009 recovered from 0 → 869 rows

### Final Output

| Station | Rows | Cols |
|---------|------|------|
| 41001 | 1129 | 32 |
| 41004 | 959 | 32 |
| 41009 | 869 | 32 |
| 41040 | 1104 | 32 |
| 42001 | 1088 | 32 |
| 42002 | 1096 | 32 |
| 44013 | 1114 | 32 |
| 46012 | 1069 | 32 |
| 46042 | 1057 | 32 |
| **Total** | **9485** | **32** |

---

## Testing

```
tests/test_ingestion.py::test_download_success PASSED
tests/test_ingestion.py::test_download_retry PASSED
tests/test_ingestion.py::test_download_historical_path PASSED
tests/test_ingestion.py::test_download_realtime_path PASSED
tests/test_features.py::test_add_lag_features PASSED
tests/test_features.py::test_add_rolling_stats PASSED
tests/test_features.py::test_add_pressure_drop_rate PASSED
tests/test_features.py::test_encode_wind_direction PASSED
tests/test_features.py::test_add_hour_of_day PASSED
tests/test_features.py::test_build_features PASSED

10 passed in 8.13s
```

### Test fix
- `test_download_retry` originally used `Exception` but code catches `RequestException` → test failed
- Fixed by importing `RequestException` in test

---

## Next Stage: ML Training (Stage 5-7) — Done

### What we built
- `src/ml/train.py` — Random Forest regressor (baseline)
- `src/ml/train_xgb.py` — XGBoost regressor (comparison)
- Time-based split (70/15/15), station_id label encoded

### Results

| Model | Target | MAE | RMSE | R² |
|-------|--------|-----|------|-----|
| Random Forest | wave_height_3h | 0.071 | 0.114 | 0.974 |
| Random Forest | wind_speed_3h | 0.625 | 0.885 | 0.897 |
| XGBoost | wave_height_3h | 0.072 | 0.114 | — |
| XGBoost | wind_speed_3h | 0.667 | 0.920 | — |

### Key findings
- RF ดีกว่า XGBoost เล็กน้อย → ใช่ RF เป็นหลัก
- Wave height ทำนายได้แม่นยม R²=0.97
- Feature importance: wave_height ตัวเอง 81%, wave_height_1h 9% = 90% คำนวณจากค่าปัจจุบัน
- 9 stations รวม 9,485 rows, 32 cols

### Problem: wave_height data สำคัญมาก
- wave_height ตั้งเป็น feature #1 importance 81%
- แปลว่า model ใช้ค่าปัจจุบันทำนาย 3h ข้างหน้าได้ดีเพราะ time series มี autocorrelation สูง
- ถ้อยากให้ model จับ pattern ซับซ้อนขึ้น → ต้องเพิ่ม features ที่มี predictive power มากขึ้น

---

## Next Stage: Azure ML (Cloud Training)
