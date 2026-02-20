"""SSE endpoints for real-time notifications."""

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.logging import get_logger
from app.core.sse.manager import get_sse_manager
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/sse", tags=["sse"])


@router.get("/notifications")
async def sse_notifications(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """Endpoint SSE para notificaciones en tiempo real."""

    async def event_generator():
        sse_manager = get_sse_manager()
        queue = await sse_manager.connect(current_user.id)

        try:
            # Enviar heartbeat inicial
            yield f"event: connected\ndata: {json.dumps({'user_id': str(current_user.id)})}\n\n"

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # Send message to client
                    event_type = message.get("type", "message")
                    data = json.dumps(message.get("data", {}))
                    yield f"event: {event_type}\ndata: {data}\n\n"

                except TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': message.get('timestamp', '')})}\n\n"

        except Exception as e:
            logger.error(f"SSE error for user {current_user.id}: {e}")
        finally:
            sse_manager.disconnect(current_user.id, queue)
            logger.info(f"SSE connection closed for user {current_user.id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
