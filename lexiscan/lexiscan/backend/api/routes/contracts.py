"""
LexiScan — Contract API Routes
"""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.services.analyzer import get_analyzer
from backend.services.comparator import compare_contracts
from backend.utils.config import settings
from backend.utils.database import Clause, Contract, ContractComparison, Entity, get_db

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────

class ContractSummary(BaseModel):
    id: str
    name: str
    overall_risk_score: float
    status: str
    page_count: Optional[int]
    file_size: Optional[int]
    uploaded_at: Optional[str]
    analyzed_at: Optional[str]


class ClauseResponse(BaseModel):
    id: str
    clause_index: int
    heading: Optional[str]
    text: str
    page_number: Optional[int]
    risk_score: float
    risk_level: str
    risk_categories: list
    confidence: float
    top_risk_tokens: list
    explanation: Optional[str]
    is_flagged: bool
    flag_reason: Optional[str]


class AnalysisResponse(BaseModel):
    contract: dict
    clauses: List[dict]
    entities: List[dict]
    parties: List[str]
    summary: str
    stats: dict


class CompareRequest(BaseModel):
    contract_id_1: str = Field(..., description="UUID of first contract")
    contract_id_2: str = Field(..., description="UUID of second contract")


# ── Helpers ───────────────────────────────────────────────────

def _save_upload(upload_file: UploadFile) -> str:
    """Save uploaded file to disk, return path."""
    upload_dir = settings.upload_path
    ext = Path(upload_file.filename).suffix.lower()
    if ext not in (".pdf",):
        raise HTTPException(400, "Only PDF files are supported")

    file_id = str(uuid.uuid4())
    dest = upload_dir / f"{file_id}{ext}"

    with open(dest, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)

    size = dest.stat().st_size
    if size > settings.max_file_size_bytes:
        dest.unlink()
        raise HTTPException(413, f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB")

    return str(dest)


def _get_contract_or_404(db: Session, contract_id: str) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(404, f"Contract '{contract_id}' not found")
    return contract


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/analyze", response_model=dict, status_code=201)
async def analyze_contract(
    file: UploadFile = File(..., description="PDF contract to analyze"),
    contract_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload and analyze a contract PDF.
    Returns full analysis with risk scores, entities, and summary.
    """
    name = contract_name or Path(file.filename).stem
    file_path = _save_upload(file)

    # Create DB record
    contract = Contract(
        name=name,
        file_path=file_path,
        status="processing",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    try:
        # Run analysis
        analyzer = get_analyzer()
        result = analyzer.analyze(file_path, name)

        # Update contract record
        c_data = result["contract"]
        contract.file_size = c_data["file_size"]
        contract.page_count = c_data["page_count"]
        contract.raw_text = c_data["raw_text"]
        contract.overall_risk_score = c_data["overall_risk_score"]
        contract.status = "done"
        contract.analyzed_at = datetime.utcnow()
        db.commit()

        # Save clauses
        for clause_data in result["clauses"]:
            clause = Clause(
                contract_id=contract.id,
                clause_index=clause_data["clause_index"],
                text=clause_data["text"],
                heading=clause_data.get("heading"),
                page_number=clause_data.get("page_number"),
                risk_score=clause_data["risk_score"],
                risk_level=clause_data["risk_level"],
                risk_categories=clause_data["risk_categories"],
                confidence=clause_data["confidence"],
                top_risk_tokens=clause_data["top_risk_tokens"],
                explanation=clause_data.get("explanation"),
                is_flagged=clause_data["is_flagged"],
                flag_reason=clause_data.get("flag_reason"),
            )
            db.add(clause)

        # Save entities
        for ent_data in result["entities"]:
            entity = Entity(
                contract_id=contract.id,
                entity_type=ent_data["entity_type"],
                text=ent_data["text"],
                normalized=ent_data.get("normalized"),
                clause_index=ent_data.get("clause_index"),
                start_char=ent_data.get("start_char"),
                end_char=ent_data.get("end_char"),
                confidence=ent_data.get("confidence", 1.0),
            )
            db.add(entity)

        db.commit()

        return {
            "contract_id": str(contract.id),
            "status": "done",
            "overall_risk_score": contract.overall_risk_score,
            "summary": result["summary"],
            "stats": result["stats"],
            "parties": result["parties"],
        }

    except Exception as e:
        logger.error(f"Analysis failed for contract {contract.id}: {e}")
        contract.status = "error"
        contract.error_message = str(e)
        db.commit()
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.get("/", response_model=List[dict])
def list_contracts(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List all contracts with summary info."""
    contracts = (
        db.query(Contract)
        .order_by(Contract.uploaded_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [c.to_dict() for c in contracts]


@router.get("/{contract_id}", response_model=dict)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    """Get contract metadata."""
    contract = _get_contract_or_404(db, contract_id)
    return contract.to_dict()


@router.get("/{contract_id}/analysis", response_model=dict)
def get_analysis(
    contract_id: str,
    risk_level: Optional[str] = None,  # filter: low|medium|high|critical
    db: Session = Depends(get_db),
):
    """
    Get full analysis for a contract.
    Optionally filter clauses by risk level.
    """
    contract = _get_contract_or_404(db, contract_id)

    clause_query = db.query(Clause).filter(Clause.contract_id == contract.id)
    if risk_level:
        clause_query = clause_query.filter(Clause.risk_level == risk_level)
    clauses = clause_query.order_by(Clause.clause_index).all()

    entities = db.query(Entity).filter(Entity.contract_id == contract.id).all()

    return {
        "contract": contract.to_dict(),
        "clauses": [c.to_dict() for c in clauses],
        "entities": [e.to_dict() for e in entities],
        "total_clauses": db.query(Clause).filter(Clause.contract_id == contract.id).count(),
        "flagged_clauses": db.query(Clause).filter(
            Clause.contract_id == contract.id,
            Clause.is_flagged == True
        ).count(),
    }


@router.get("/{contract_id}/clauses", response_model=List[dict])
def get_clauses(
    contract_id: str,
    risk_level: Optional[str] = None,
    flagged_only: bool = False,
    db: Session = Depends(get_db),
):
    """Get clauses for a contract, with optional filters."""
    _get_contract_or_404(db, contract_id)

    query = db.query(Clause).filter(Clause.contract_id == contract_id)
    if risk_level:
        query = query.filter(Clause.risk_level == risk_level)
    if flagged_only:
        query = query.filter(Clause.is_flagged == True)

    clauses = query.order_by(Clause.clause_index).all()
    return [c.to_dict() for c in clauses]


@router.post("/compare", response_model=dict)
def compare_two_contracts(
    request: CompareRequest,
    db: Session = Depends(get_db),
):
    """
    Compare two contracts side by side.
    Returns clause-level diff with risk score changes.
    """
    contract1 = _get_contract_or_404(db, request.contract_id_1)
    contract2 = _get_contract_or_404(db, request.contract_id_2)

    if contract1.status != "done" or contract2.status != "done":
        raise HTTPException(400, "Both contracts must have completed analysis")

    clauses1 = (
        db.query(Clause)
        .filter(Clause.contract_id == contract1.id)
        .order_by(Clause.clause_index)
        .all()
    )
    clauses2 = (
        db.query(Clause)
        .filter(Clause.contract_id == contract2.id)
        .order_by(Clause.clause_index)
        .all()
    )

    result = compare_contracts(
        [c.to_dict() for c in clauses1],
        [c.to_dict() for c in clauses2],
        contract1.name,
        contract2.name,
    )

    # Store comparison
    comparison = ContractComparison(
        contract_id_1=contract1.id,
        contract_id_2=contract2.id,
        comparison_result={
            "stats": result["stats"],
            "summary": result["summary"],
        },
        risk_delta=result["stats"]["risk_delta"],
    )
    db.add(comparison)
    db.commit()

    return result


@router.delete("/{contract_id}", status_code=204)
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    """Delete a contract and all associated data."""
    contract = _get_contract_or_404(db, contract_id)

    # Delete file
    if os.path.exists(contract.file_path):
        os.unlink(contract.file_path)

    db.delete(contract)
    db.commit()
    return None
