from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, UploadFile, Form
from fastapi.responses import StreamingResponse

from backend.services.docx_rewrite_service import resolve_llm_config, rewrite_docx_mvp


router = APIRouter()


@router.post("/api/docx/rewrite")
async def rewrite_docx_endpoint(
    raw_request: Request,
    reference_file: UploadFile,
    instruction_text: str = Form(...),
):
    filename = (reference_file.filename or "").strip()
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="MVP 仅支持 .docx 模板")

    content = await reference_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    llm_cfg = resolve_llm_config(
        api_key=(raw_request.headers.get("x-llm-api-key") or "").strip() or None,
        base_url=(raw_request.headers.get("x-llm-base-url") or "").strip() or None,
        model=(raw_request.headers.get("x-llm-model") or "").strip() or None,
    )
    if llm_cfg is None:
        raise HTTPException(status_code=400, detail="未配置 LLM：请设置 x-llm-api-key 或环境变量 DEEPSEEK_API_KEY/OPENAI_API_KEY")

    try:
        out_bytes = rewrite_docx_mvp(
            reference_docx_bytes=content,
            instruction_text=instruction_text,
            llm_config=llm_cfg,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {type(e).__name__}: {e}")

    out_name = f"rewritten_{filename}" if filename else "rewritten.docx"
    headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
    return StreamingResponse(
        iter([out_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )

