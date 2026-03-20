# ⚖️ LexiScan — Legal Document Risk Analyzer

> AI-powered contract review platform that classifies risk, extracts obligations, and flags anomalies — so lawyers and SMEs can review contracts in minutes, not hours.

---

## 🚀 Features

### Core
- **PDF Ingestion & Clause Segmentation** — Parses contracts into logical clauses using spaCy
- **Risk Scoring (0–10 per clause)** — LegalBERT-powered classification across 41 CUAD categories
- **Named Entity Extraction** — Parties, dates, monetary values, obligations, jurisdictions
- **Explainability** — Highlights which tokens drive each risk score

### Advanced
- **Comparative Analysis** — Diff two contract versions, flagging added/removed/changed clauses
- **Streamlit Dashboard** — Color-coded risk zones, filterable clause table, PDF overlay highlights
- **FastAPI Backend** — REST API for programmatic access
- **PostgreSQL Storage** — Persistent contract & analysis history

---

## 🏗️ Architecture

```
lexiscan/
├── backend/
│   ├── api/          # FastAPI routes
│   ├── models/       # LegalBERT, NER, risk scorer
│   ├── services/     # PDF parser, clause segmenter, comparator
│   └── utils/        # DB, config, helpers
├── frontend/
│   ├── pages/        # Streamlit multi-page app
│   ├── components/   # Reusable UI widgets
│   └── utils/        # API client, formatters
├── data/
│   ├── sample_contracts/
│   └── processed/
├── tests/
├── scripts/          # Setup, training, data prep
└── docs/
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| NLP Models | HuggingFace Transformers (`nlpaueb/legal-bert-base-uncased`) |
| NER | spaCy (`en_core_web_trf`) |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Database | PostgreSQL + SQLAlchemy |
| PDF Processing | PyMuPDF (fitz) + pdfplumber |
| Dataset | CUAD (Contract Understanding Atticus Dataset) |
| Containerization | Docker + Docker Compose |

---

## 🛠️ Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Docker (optional)

### 1. Clone & Install
```bash
git clone https://github.com/yourorg/lexiscan.git
cd lexiscan
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your DB credentials and settings
```

### 3. Initialize Database
```bash
python scripts/init_db.py
```

### 4. Download Models (first run)
```bash
python scripts/download_models.py
```

### 5. Start Services

**Option A — Docker Compose (recommended)**
```bash
docker-compose up --build
```

**Option B — Manual**
```bash
# Terminal 1: Backend
uvicorn backend.api.main:app --reload --port 8000

# Terminal 2: Frontend
streamlit run frontend/app.py --server.port 8501
```

### 6. Access
- Streamlit UI: http://localhost:8501
- FastAPI Docs: http://localhost:8000/docs

---

## 📊 Risk Categories (CUAD-based)

LexiScan classifies clauses across 41 legal risk categories including:

| Category | Risk Level |
|----------|-----------|
| Unlimited Liability | 🔴 Critical |
| Auto-Renewal | 🟠 High |
| Termination for Convenience | 🟠 High |
| IP Ownership | 🟠 High |
| Non-Compete | 🟡 Medium |
| Governing Law | 🟡 Medium |
| Payment Terms | 🟡 Medium |
| Confidentiality | 🟢 Low |

---

## 🧪 Running Tests
```bash
pytest tests/ -v --cov=backend --cov-report=html
```

---

## 📡 API Reference

### Upload & Analyze Contract
```bash
POST /api/v1/contracts/analyze
Content-Type: multipart/form-data

curl -X POST http://localhost:8000/api/v1/contracts/analyze \
  -F "file=@contract.pdf" \
  -F "contract_name=Vendor Agreement 2024"
```

### Get Analysis Results
```bash
GET /api/v1/contracts/{contract_id}/analysis
```

### Compare Two Contracts
```bash
POST /api/v1/contracts/compare
Body: { "contract_id_1": "uuid", "contract_id_2": "uuid" }
```

---

## 🤝 Dataset Credit
Built on the [CUAD Dataset](https://www.atticusprojectai.org/cuad) by The Atticus Project — 510 commercial legal contracts with 13,000+ expert annotations across 41 clause types.

---

## 📄 License
MIT License — see [LICENSE](LICENSE)
