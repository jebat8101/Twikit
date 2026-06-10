from __future__ import annotations

from typing import TYPE_CHECKING

from .base import model

if TYPE_CHECKING:
    from ..client import Client


@model(reprs='id')
class User:
    id: str
    name: str
    screen_name: str
    created_at: str
    followers_count: int | None
    following_count: int | None

    @classmethod
    def _from_payload(cls, payload: dict, client: Client):
        core = payload.get('core', {})
        legacy = payload.get('legacy', {})
        return cls(
            id=payload.get('rest_id'),
            name=core.get('name'),
            screen_name=core.get('screen_name'),
            created_at=core.get('created_at'),
            followers_count=legacy.get('followers_count'),
            following_count=legacy.get('friends_count'),
        )
