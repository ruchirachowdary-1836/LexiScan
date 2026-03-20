"""LexiScan — About Page"""
import streamlit as st


def render():
    st.title("ℹ️ About LexiScan")

    st.markdown("""
## ⚖️ What is LexiScan?

**LexiScan** is an AI-powered legal document risk analyzer that helps lawyers and SMEs 
review contracts in minutes instead of hours.

---

## 🧠 How It Works

### 1. PDF Ingestion
Your contract PDF is parsed using **PyMuPDF** and **pdfplumber**, extracting clean text 
while preserving structure. The text is then split into logical clauses using a combination 
of heading detection and spaCy sentence segmentation.

### 2. Clause-Level Risk Classification
Each clause is analyzed by a **LegalBERT** model (`nlpaueb/legal-bert-base-uncased`), 
fine-tuned on the **CUAD dataset** — 510 commercial contracts with 13,000+ expert annotations 
across 41 clause types.

The model outputs:
- A **risk score** (0–10) per clause  
- Detected **CUAD categories** (e.g. Non-Compete, Uncapped Liability, Indemnification)
- **Token-level attribution** showing which words drive the risk score

### 3. Named Entity Extraction
Using **spaCy** + custom rule-based patterns, LexiScan extracts:
- 👤 Parties and organizations  
- 📅 Dates and durations  
- 💰 Monetary values  
- ⚖️ Obligations and jurisdictions

### 4. Risk Aggregation
The overall contract risk score is computed as a **weighted average** of clause scores, 
with critical/high clauses given 2× weight.

### 5. Comparative Analysis
Upload two versions of a contract for **clause-level diff** — identifying added, removed, 
and modified provisions with per-change risk deltas.

---

## 📊 Risk Categories (CUAD-based)

| Risk Level | Score Range | Examples |
|-----------|-------------|---------|
| 🔴 Critical | 8.5–10 | Uncapped Liability, Non-Compete |
| 🟠 High | 6.0–8.5 | Indemnification, IP Ownership, Change of Control |
| 🟡 Medium | 3.0–6.0 | Governing Law, Confidentiality, Audit Rights |
| 🟢 Low | 0–3.0 | Force Majeure, Cap on Liability |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| NLP Model | HuggingFace Transformers (LegalBERT) |
| NER | spaCy |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Database | PostgreSQL + SQLAlchemy |
| PDF | PyMuPDF + pdfplumber |
| Dataset | CUAD (Atticus Project) |

---

## ⚠️ Disclaimer

LexiScan is an **AI-assisted** tool and does not constitute legal advice. 
Always have contracts reviewed by a qualified attorney before signing.

---

## 📄 Dataset Credit

Built using the [CUAD Dataset](https://www.atticusprojectai.org/cuad) by The Atticus Project.  
Licensed under CC BY 4.0.
""")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Version:** 1.0.0")
        st.markdown("**Model:** nlpaueb/legal-bert-base-uncased")
    with col2:
        st.markdown("**License:** MIT")
        st.markdown("**Dataset:** CUAD (41 categories)")
