import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.report import Report
from app.models.audit_log import AuditLog
from app.query.retriever import retrieve_for_query, RetrievalResult

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(..., example="Who did Inspector Vikram contact on 12 March 2024?")


@router.post("/reports/{report_id}/query")
def submit_query(
    report_id: str,
    payload: QueryRequest,
    db: Session = Depends(get_db),
):
    """
    Submits an investigator question. Executes deterministic Query Pipeline (Intent -> Entity Resolution -> Ground-Truth Retrieval).
    Returns structured RetrievalResult with complete provenance. Zero LLM calls.
    """
    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string cannot be empty or whitespace only."
        )

    try:
        result: RetrievalResult = retrieve_for_query(
            report_id=report_id,
            question=payload.question,
            db=db,
        )
        return result.model_dump()
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query retrieval service failure: {str(e)}"
        )


@router.get("/reports/{report_id}/query/history")
def get_query_history(report_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the audit trail of past investigator queries for a report.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.report_id == report_id, AuditLog.action == "INVESTIGATOR_QUERY")
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    history = []
    for log in audit_logs:
        try:
            dtls = json.loads(log.details)
        except Exception:
            dtls = {}

        history.append({
            "log_id": log.id,
            "query_id": dtls.get("query_id", "N/A"),
            "question": dtls.get("question", "N/A"),
            "intent": dtls.get("intent", "UNKNOWN"),
            "status": dtls.get("status", "UNKNOWN"),
            "evidence_count": dtls.get("evidence_count", 0),
            "timestamp": log.timestamp.isoformat(),
        })

    return {
        "report_id": report_id,
        "total_queries": len(history),
        "history": history,
    }
