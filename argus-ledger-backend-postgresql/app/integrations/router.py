"""HTTP surface for the verification pipeline.

``/text`` and ``/url`` take a JSON body (what the React client sends);
``/image`` is multipart with an optional ``text`` context field.
"""

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from .verification_orchestrator import VerificationOrchestrator

router = APIRouter(prefix="/verification", tags=["verification"])
orchestrator = VerificationOrchestrator()


class TextVerifyRequest(BaseModel):
    text: str


class UrlVerifyRequest(BaseModel):
    url: str


@router.post("/text")
async def verify_text(payload: TextVerifyRequest):
    return (await orchestrator.verify(text=payload.text)).as_dict()


@router.post("/url")
async def verify_url(payload: UrlVerifyRequest):
    return (await orchestrator.verify(url=payload.url)).as_dict()


@router.post("/image")
async def verify_image(file: UploadFile = File(...), text: str = Form("")):
    data = await file.read()
    return (await orchestrator.verify(
        image_bytes=data,
        text=text,
        filename=file.filename or "image",
    )).as_dict()
