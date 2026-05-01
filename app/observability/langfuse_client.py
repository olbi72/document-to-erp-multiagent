import os

from langfuse import get_client, observe, propagate_attributes

from app.config import settings


if settings.langfuse_enabled:
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key or ""
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key or ""
    os.environ["LANGFUSE_BASE_URL"] = settings.langfuse_base_url


langfuse = get_client()


def build_trace_context(
    session_id: str,
    user_id: str = "local-user",
    tags: list[str] | None = None,
    metadata: dict | None = None,
):
    if not settings.langfuse_enabled:
        return None

    return propagate_attributes(
        session_id=session_id,
        user_id=user_id,
        tags=tags or ["document-to-erp", "mvp", "hitl"],
        metadata=metadata or {},
    )


def flush_langfuse() -> None:
    if settings.langfuse_enabled:
        langfuse.flush()

def create_langfuse_score(
    session_id: str,
    name: str,
    value: float,
    comment: str | None = None,
) -> None:
    if not settings.langfuse_enabled:
        return

    langfuse.create_score(
        session_id=session_id,
        name=name,
        value=value,
        data_type="NUMERIC",
        comment=comment,
        score_id=f"{session_id}-{name}",
    )

    langfuse.flush()

def create_current_trace_score(
    name: str,
    value: float,
    comment: str | None = None,
) -> None:
    if not settings.langfuse_enabled:
        return

    trace_id = langfuse.get_current_trace_id()

    if not trace_id:
        return

    langfuse.create_score(
        trace_id=trace_id,
        name=name,
        value=value,
        data_type="NUMERIC",
        comment=comment,
    )