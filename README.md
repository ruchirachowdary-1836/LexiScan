## LexiScan — Legal Document Risk Analyzer

## Overview
LexiScan is an AI-powered tool that analyzes legal contracts and detects risky clauses using NLP.

## Problem
Manual contract review is time-consuming and expensive.

## Solution
- Clause segmentation
- Risk scoring (0–10)
- Named entity recognition
- Explainable AI outputs

## Tech Stack
- Transformers (LegalBERT)
- spaCy
- FastAPI
- Streamlit
- PostgreSQL

## Features
- PDF upload & analysis
- Clause-level risk detection
- Contract comparison

##  Run
```bash
streamlit run app.py
