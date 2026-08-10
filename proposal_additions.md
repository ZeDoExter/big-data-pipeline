เพิ่มเติมสำหรับ Project Proposal

---

## 1. CI/CD Pipeline รายละเอียด (เพิ่มเติมจากข้อ 4)

เมื่อมีการ Push หรือ Merge เข้าสู่ branch `main` ระบบ GitHub Actions จะทำงานอัตโนมัติ:

### Workflow 1: ML Pipeline (เปลี่ยนแปลงใน src/ml/)
1. Trigger: push ไปที่ `src/ml/**` หรือ `src/spark/**`
2. Jobs:
   - test:รัน unit test ของ ingestion script และ Spark job
   - lint: ตรวจสอบ code quality (flake8, black)
   - train: ส่ง training job ไป Azure ML (ถ้ามีการเปลี่ยนแปลง model)
   - register: register model ใหม่ใน Azure Model Registry
   - deploy: deploy model ไป Managed Online Endpoint (staging → production)

### Workflow 2: Azure Function (เปลี่ยนแปลงใน src/function/)
1. Trigger: push ไปที่ `src/function/**`
2. Jobs:
   - test: รัน unit test ของ function
   - deploy: deploy function ไป Azure Functions ด้วย `func azure functionapp publish`

### Workflow 3: Dashboard (เปลี่ยนแปลงใน src/dashboard/)
1. Trigger: push ไปที่ `src/dashboard/**`
2. Jobs:
   - test: รัน test streamlit
   - deploy: deploy ไป Azure App Service หรือ Streamlit Cloud

---

## 2. Azure Monitor รายละเอียด (เพิ่มเติมจากข้อ 3)

### Metrics ที่ติดตาม
- Azure Function: execution count, success rate, duration, error rate
- Managed Online Endpoint: request latency, requests per minute, 5xx errors
- Cosmos DB: request units consumed, latency, availability
- Blob Storage: ingress/egress, availability

### Alerts
- Function error rate > 5% → แจ้งเตือน email
- Endpoint 5xx errors > 10 ครั้ง/ชั่วโมง → แจ้งเตือน
- Cosmos DB RU consumption > 80% → แจ้งเตือน
- ML prediction latency > 5 วินาที → แจ้งเตือน

### Logs
- Application Insights: trace request flow จาก Function → Endpoint → Cosmos DB
- Log Analytics: query log เพื่อ debug issue
- Retention: 30 วัน (ประหยัดค่าใช้จ่าย)

---

## 3. Azure Key Vault รายละเอียด (เพิ่มเติมจากข้อ 5)

### Secrets ที่เก็บ
- NDBC API key (ถ้ามีในอนาคต)
- Azure Storage connection string
- Cosmos DB connection string
- Azure ML workspace connection string
- Azure Function app settings
- Service Principal credentials

### การเข้าถึง
- Function App: ใช้ Managed Identity เข้าถึง Key Vault (ไม่ต้องเขียน credential)
- Azure ML: ใช้ Managed Identity ในการอ่าน training data จาก Blob
- Local dev: ใช้ Azure CLI login แล้วอ่านจาก Key Vault ผ่าน environment variables

### Rotation
- Secrets rotate ทุก 90 วัน (ตาม best practice)
- ถ้ามี service account สำหรับ NDBC (ถ้ามี) ก็ rotate ด้วย

---

## 4. Azure Blob Storage รายละเอียด (เพิ่มเติมจากข้อ 3)

### Container Structure
```
├── raw/                    # ข้อมูลดิบจาก NDBC
│   ├── historical/         # ไฟล์ .txt.gz ดิบ
│   └── realtime/           # ไฟล์ .txt ดิบ
├── processed/              # ข้อมูลหลา Spark (Parquet)
│   ├── observations/       # ตาราง observations
│   └── features/           # feature engineering output
├── training/               # training dataset
│   ├── train.csv
│   ├── validation.csv
│   └── test.csv
└── models/                 # model artifacts
    ├── random_forest.pkl
    ├── xgboost.pkl
    └── best_model.pkl
```

### Lifecycle Management
- raw/hot: เก็บ 30 วัน แล้ว move เป็น cool tier
- processed/cool: เก็บ 90 วัน
- training/Archive: เก็บ 1 ปี
- ลบไฟล์ที่เก่ากว่า 2 ปีอัตโนมัติ

### Access
- Azure ML: read access ไปที่ training/ และ processed/
- Azure Function: read access ไปที่ processed/realtime/
- ไม่มี public access ทุก container

---

## 5. Security รายละเอียด (เพิ่มเติมจากข้อ 5)

### Network
- Azure Function: ไม่ต้อง VNet เพราะไม่มี inbound traffic (timer trigger)
- Managed Online Endpoint: ปิด public inbound, ใช้ private endpoint ถ้าจำเป็น
- Cosmos DB: เปิด selected networks เฉพาะ Azure Function outbound IP
- Blob Storage: เปิดเฉพาะจาก Azure Function และ Azure ML

### Identity
- ใช้ Managed Identity ทุก service ที่รองรับ (Function, ML, Cosmos DB)
- ไม่เขียน credential ลง source code เด็ดขาด
- Service Principal สำหรับ CI/CD (GitHub Actions) — เก็บใน GitHub Secrets

### RBAC Roles
| Service | Role | Identity |
|---------|------|----------|
| Function App | Contributor | Function Managed Identity |
| Cosmos DB | Cosmos DB Account Reader | Function Managed Identity |
| Blob Storage | Storage Blob Data Reader | Function + ML |
| Key Vault | Secrets User | Function + ML |
| Azure ML | ML Contributor | CI/CD Service Principal |

### Data Protection
- Data at rest: Azure default encryption (Microsoft-managed keys)
- Data in transit: TLS 1.2+
- PII: ไม่มีข้อมูลส่วนบุคคลในระบบ (เป็นข้อมูลอุตุนิยมวิทยา)

---

## 6. Cost Estimate (เพิ่มเติมจากข้อ 5)

| Service | Tier | Estimated Cost |
|---------|------|----------------|
| Azure ML | Student ($100/yr) | ฟรีใน credit |
| Azure Functions | Consumption | < $1/เดือน (1440 runs/เดือน) |
| Cosmos DB | Serverless | < $5/เดือน |
| Blob Storage | Cool tier | < $1/เดือน |
| Managed Online Endpoint | Scale to 0 | < $5/เดือน (compute เฉพาะตอน batch) |
| Key Vault | Standard | < $1/เดือน |
| Monitor | Free tier | ฟรี 5GB/เดือน |
| **รวม** | | **< $15/เดือน** (หรือใน Student Credit ครอบคลุม) |

หมายเหตุ: ถ้าใช้ Student Credit $100/ปี ครอบคลุมทั้งหมดโดยไม่มีค่าใช้จ่ายเพิ่ม

---

## 7. Risk & Mitigation (เพิ่มเติม)

| Risk | Impact | Mitigation |
|------|--------|------------|
| NDBC API down | ไม่ได้ข้อมูล realtime | Retry 3 ครั้ง, fallback ใช้ historical ล่าสุด |
| Azure ML quota exceeded | train ไม่ได้ | ใช้ spot instance หรือลด training data |
| Cosmos DB latency สูง | dashboard โหลดช้า | ใช้ Cosmos DB serverless + cache |
| Model drift | prediction ไม่แม่นยำ | retrain ทุกสัปดาว (automated) |
| Blob Storage cost สูง | เกิงงบ | lifecycle policy ลบข้อมูลเก่า |
