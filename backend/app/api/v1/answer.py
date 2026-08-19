from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.ollama_client import OllamaConnectionError, OllamaTimeoutError
from app.llm.external_llm_client import ExternalLLMNotConfiguredError, ExternalLLMError, ExternalLLMTimeoutError
from app.llm.answer_service import answer_investigator_question, InvestigatorAnswer

router = APIRouter(tags=["answer"])


class AnswerRequest(BaseModel):
    question: str = Field(..., example="Who did Inspector Vikram contact on 12 March 2024?")
    llm_provider: Optional[str] = Field("external", description="LLM provider choice: 'external' (Groq), 'local' (Ollama), or 'auto' (Groq + Local Fallback)")
    use_external_llm: Optional[bool] = Field(None, description="Legacy opt-in flag for backward compatibility")


@router.post("/reports/{report_id}/answer")
def get_answer(
    report_id: str,
    payload: AnswerRequest,
    db: Session = Depends(get_db),
):
    """
    Submits an investigator question for grounded natural-language answer generation.
    Defaults to fast hosted Groq LLM ('external'), with option for local Ollama ('local') or auto-fallback ('auto').
    Privacy Gateway enforces pseudonymization and payload minimization on all prompts before external dispatch.
    """
    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question string cannot be empty or whitespace only."
        )

    try:
        answer: InvestigatorAnswer = answer_investigator_question(
            report_id=report_id,
            question=payload.question,
            use_external_llm=payload.use_external_llm,
            llm_provider=payload.llm_provider or "external",
            db=db,
        )
        return answer.model_dump()
    except ExternalLLMNotConfiguredError as ece:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{str(ece)} Tip: Pass llm_provider='local' or llm_provider='auto' to use local inference."
        )
    except ExternalLLMError as ele:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(ele)
        )
    except ExternalLLMTimeoutError as elt:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(elt)
        )
    except OllamaConnectionError as oce:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(oce)
        )
    except OllamaTimeoutError as ote:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(ote)
        )
    except ValueError as ve:
        err_msg = str(ve)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM answer generation failed: {str(e)}"
        )
