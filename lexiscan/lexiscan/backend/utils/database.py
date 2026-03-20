"""
LexiScan — Database Models (SQLAlchemy ORM)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

from backend.utils.config import settings

# ── Engine & Session ──────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """FastAPI dependency — yields DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Models ───────────────────────────────────────────────────

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)
    page_count = Column(Integer)
    raw_text = Column(Text)
    overall_risk_score = Column(Float, default=0.0)
    status = Column(String(50), default="pending")  # pending | processing | done | error
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime, nullable=True)

    # Relationships
    clauses = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="contract", cascade="all, delete-orphan")
    comparisons_as_v1 = relationship(
        "ContractComparison", foreign_keys="ContractComparison.contract_id_1", back_populates="contract_v1"
    )
    comparisons_as_v2 = relationship(
        "ContractComparison", foreign_keys="ContractComparison.contract_id_2", back_populates="contract_v2"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "file_size": self.file_size,
            "page_count": self.page_count,
            "overall_risk_score": self.overall_risk_score,
            "status": self.status,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    clause_index = Column(Integer, nullable=False)  # order in document
    text = Column(Text, nullable=False)
    heading = Column(String(500), nullable=True)
    page_number = Column(Integer, nullable=True)

    # Risk analysis
    risk_score = Column(Float, default=0.0)       # 0–10
    risk_level = Column(String(20), default="low") # low | medium | high | critical
    risk_categories = Column(JSON, default=list)   # list of CUAD categories detected
    confidence = Column(Float, default=0.0)

    # Explainability
    top_risk_tokens = Column(JSON, default=list)   # [{"token": "...", "score": 0.9}, ...]
    explanation = Column(Text, nullable=True)

    # Flags
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(Text, nullable=True)

    # Relationships
    contract = relationship("Contract", back_populates="clauses")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "contract_id": str(self.contract_id),
            "clause_index": self.clause_index,
            "text": self.text,
            "heading": self.heading,
            "page_number": self.page_number,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "risk_categories": self.risk_categories or [],
            "confidence": self.confidence,
            "top_risk_tokens": self.top_risk_tokens or [],
            "explanation": self.explanation,
            "is_flagged": self.is_flagged,
            "flag_reason": self.flag_reason,
        }


class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    entity_type = Column(String(100), nullable=False)  # PARTY | DATE | MONEY | ORG | ...
    text = Column(String(500), nullable=False)
    normalized = Column(String(500), nullable=True)    # normalized form
    clause_index = Column(Integer, nullable=True)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    confidence = Column(Float, default=1.0)

    # Relationships
    contract = relationship("Contract", back_populates="entities")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "entity_type": self.entity_type,
            "text": self.text,
            "normalized": self.normalized,
            "clause_index": self.clause_index,
            "confidence": self.confidence,
        }


class ContractComparison(Base):
    __tablename__ = "contract_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id_1 = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    contract_id_2 = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    comparison_result = Column(JSON, default=dict)  # diff result
    risk_delta = Column(Float, default=0.0)         # risk score change
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contract_v1 = relationship("Contract", foreign_keys=[contract_id_1], back_populates="comparisons_as_v1")
    contract_v2 = relationship("Contract", foreign_keys=[contract_id_2], back_populates="comparisons_as_v2")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "contract_id_1": str(self.contract_id_1),
            "contract_id_2": str(self.contract_id_2),
            "comparison_result": self.comparison_result,
            "risk_delta": self.risk_delta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def create_tables():
    """Create all tables. Run once on startup."""
    Base.metadata.create_all(bind=engine)
