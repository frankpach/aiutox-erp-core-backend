"""Pub-Sub administrative router for event bus management."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.core.auth.dependencies import require_permission
from app.core.config_file import get_settings
from app.core.exceptions import APIException
from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.errors import PubSubError
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse

router = APIRouter()
settings = get_settings()


def get_redis_client() -> RedisStreamsClient:
    """Dependency to get Redis client."""
    return RedisStreamsClient(redis_url=settings.REDIS_URL, password=settings.REDIS_PASSWORD)


@router.get(
    "/stats",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get Pub-Sub statistics",
    description="Get statistics about streams, groups, and pending messages. Requires pubsub.view permission.",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_stats(
    current_user: Annotated[User, Depends(require_permission("pubsub.view"))],
    redis_client: Annotated[RedisStreamsClient, Depends(get_redis_client)],
) -> StandardResponse[dict[str, Any]]:
    """Get statistics about all streams."""
    try:
        stats = {
            "streams": {},
            "total_pending": 0,
        }

        # Get stats for each stream
        for stream_name in [
            settings.REDIS_STREAM_DOMAIN,
            settings.REDIS_STREAM_TECHNICAL,
            settings.REDIS_STREAM_FAILED,
        ]:
            try:
                stream_info = await redis_client.get_stream_info(stream_name)
                groups_info = []

                # Get groups for this stream
                try:
                    async with redis_client.connection() as client:
                        groups = await client.xinfo_groups(stream_name)
                        for group in groups:
                            group_name = group.get("name", "unknown")
                            try:
                                group_info = await redis_client.get_group_info(stream_name, group_name)
                                pending = await redis_client.get_pending_messages(
                                    stream_name, group_name, count=100
                                )
                                groups_info.append(
                                    {
                                        "name": group_name,
                                        "consumers": group_info.get("consumers", 0),
                                        "pending": group_info.get("pending", 0),
                                        "last_delivered_id": group_info.get("last-delivered-id", "0-0"),
                                        "pending_messages_count": len(pending),
                                    }
                                )
                                stats["total_pending"] += len(pending)
                            except PubSubError:
                                # Group might not exist, skip
                                pass
                except PubSubError:
                    # No groups or stream doesn't exist
                    pass

                stats["streams"][stream_name] = {
                    "length": stream_info.get("length", 0),
                    "groups": groups_info,
                    "first_entry_id": stream_info.get("first-entry", "0-0"),
                    "last_entry_id": stream_info.get("last-entry", "0-0"),
                }
            except PubSubError:
                # Stream doesn't exist yet
                stats["streams"][stream_name] = {
                    "length": 0,
                    "groups": [],
                    "first_entry_id": None,
                    "last_entry_id": None,
                }

        return StandardResponse(
            data=stats,
            meta={"message": "Statistics retrieved successfully"},
        )
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="PUBSUB_STATS_ERROR",
            message=f"Failed to retrieve statistics: {str(e)}",
        ) from e


@router.get(
    "/failed",
    response_model=StandardListResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List failed events",
    description="List events that failed processing and were moved to the failed stream. Requires pubsub.view permission.",
    responses={
        200: {"description": "Failed events retrieved successfully"},
        403: {"description": "Insufficient permissions"},
    },
)
async def list_failed_events(
    current_user: Annotated[User, Depends(require_permission("pubsub.view"))],
    redis_client: Annotated[RedisStreamsClient, Depends(get_redis_client)],
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of events to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> StandardListResponse[dict[str, Any]]:
    """List failed events from the failed stream."""
    try:
        async with redis_client.connection() as client:
            # Read from failed stream (most recent first)
            messages = await client.xrevrange(
                settings.REDIS_STREAM_FAILED,
                max="+",
                min="-",
                count=limit + offset,
            )

            # Apply offset
            if offset > 0:
                messages = messages[offset:]

            # Limit results
            messages = messages[:limit]

            failed_events = []
            for message_id, data in messages:
                event_data = dict(data)
                event_data["message_id"] = message_id
                failed_events.append(event_data)

            return StandardListResponse(
                data=failed_events,
                meta={
                    "total": len(failed_events),
                    "page": 1,
                    "page_size": max(len(failed_events), 1),  # Minimum page_size is 1
                    "total_pages": 1,
                },
            )
    except PubSubError:
        # Stream might not exist yet
        return StandardListResponse(
            data=[],
            meta={
                "total": 0,
                "page": 1,
                "page_size": 1,  # Minimum page_size is 1
                "total_pages": 1,
            },
        )
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="PUBSUB_FAILED_EVENTS_ERROR",
            message=f"Failed to retrieve failed events: {str(e)}",
        ) from e


@router.post(
    "/failed/{message_id}/reprocess",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Reprocess failed event",
    description="Reprocess a failed event by moving it back to its original stream. Requires pubsub.manage permission.",
    responses={
        200: {"description": "Event reprocessed successfully"},
        404: {"description": "Event not found"},
        403: {"description": "Insufficient permissions"},
    },
)
async def reprocess_failed_event(
    message_id: str,
    current_user: Annotated[User, Depends(require_permission("pubsub.manage"))],
    redis_client: Annotated[RedisStreamsClient, Depends(get_redis_client)],
) -> StandardResponse[dict[str, Any]]:
    """Reprocess a failed event."""
    try:
        async with redis_client.connection() as client:
            # Read the failed event
            messages = await client.xrange(
                settings.REDIS_STREAM_FAILED,
                min=message_id,
                max=message_id,
                count=1,
            )

            if not messages:
                raise APIException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code="PUBSUB_EVENT_NOT_FOUND",
                    message=f"Failed event with ID {message_id} not found",
                )

            _, event_data = messages[0]
            original_stream = event_data.get("original_stream")
            if not original_stream:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="PUBSUB_INVALID_EVENT",
                    message="Event does not have original_stream information",
                )

            # Remove error fields and restore original event data
            reprocess_data = {
                k: v
                for k, v in event_data.items()
                if k not in ["original_stream", "original_message_id", "error_info", "failed_at"]
            }

            # Add back to original stream
            new_message_id = await client.xadd(original_stream, reprocess_data)

            # Remove from failed stream
            await client.xdel(settings.REDIS_STREAM_FAILED, message_id)

            return StandardResponse(
                data={
                    "original_message_id": message_id,
                    "new_message_id": new_message_id,
                    "original_stream": original_stream,
                },
                message="Event reprocessed successfully",
            )
    except APIException:
        raise
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="PUBSUB_REPROCESS_ERROR",
            message=f"Failed to reprocess event: {str(e)}",
        ) from e


@router.get(
    "/streams/{stream_name}/info",
    response_model=StandardResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get stream information",
    description="Get detailed information about a specific stream. Requires pubsub.view permission.",
    responses={
        200: {"description": "Stream information retrieved successfully"},
        404: {"description": "Stream not found"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_stream_info(
    stream_name: str,
    current_user: Annotated[User, Depends(require_permission("pubsub.view"))],
    redis_client: Annotated[RedisStreamsClient, Depends(get_redis_client)],
) -> StandardResponse[dict[str, Any]]:
    """Get detailed information about a stream."""
    try:
        stream_info = await redis_client.get_stream_info(stream_name)

        # Get groups
        groups = []
        try:
            async with redis_client.connection() as client:
                groups_data = await client.xinfo_groups(stream_name)
                for group in groups_data:
                    group_name = group.get("name", "unknown")
                    try:
                        group_info = await redis_client.get_group_info(stream_name, group_name)
                        groups.append(dict(group_info))
                    except PubSubError:
                        pass
        except PubSubError:
            pass

        return StandardResponse(
            data={
                "stream_name": stream_name,
                "length": stream_info.get("length", 0),
                "groups": groups,
                "first_entry_id": stream_info.get("first-entry", "0-0"),
                "last_entry_id": stream_info.get("last-entry", "0-0"),
            },
            meta={"message": "Stream information retrieved successfully"},
        )
    except PubSubError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PUBSUB_STREAM_NOT_FOUND",
            message=f"Stream '{stream_name}' not found: {str(e)}",
        ) from e
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="PUBSUB_STREAM_INFO_ERROR",
            message=f"Failed to retrieve stream information: {str(e)}",
        ) from e


@router.get(
    "/streams/{stream_name}/groups/{group_name}/pending",
    response_model=StandardListResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get pending messages for a group",
    description="Get pending messages for a specific consumer group. Requires pubsub.view permission.",
    responses={
        200: {"description": "Pending messages retrieved successfully"},
        404: {"description": "Stream or group not found"},
        403: {"description": "Insufficient permissions"},
    },
)
async def get_pending_messages(
    stream_name: str,
    group_name: str,
    current_user: Annotated[User, Depends(require_permission("pubsub.view"))],
    redis_client: Annotated[RedisStreamsClient, Depends(get_redis_client)],
    count: int = Query(default=10, ge=1, le=100, description="Maximum number of messages to return"),
) -> StandardListResponse[dict[str, Any]]:
    """Get pending messages for a consumer group."""
    try:
        pending = await redis_client.get_pending_messages(stream_name, group_name, count=count)

        return StandardListResponse(
            data=pending,
            meta={
                "total": len(pending),
                "page": 1,
                "page_size": len(pending),
                "total_pages": 1,
            },
            message="Pending messages retrieved successfully",
        )
    except PubSubError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PUBSUB_GROUP_NOT_FOUND",
            message=f"Stream or group not found: {str(e)}",
        ) from e
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="PUBSUB_PENDING_ERROR",
            message=f"Failed to retrieve pending messages: {str(e)}",
        ) from e







