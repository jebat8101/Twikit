from __future__ import annotations

from typing import TYPE_CHECKING

from .base import model

if TYPE_CHECKING:
    from ..client import Client


@model(reprs='id')
class User:
    # TODO this
    id: str
    ## core
    name: str
    screen_name: str
    created_at: str

    @classmethod
    def _from_payload(cls, payload: dict, _client: Client):
        core = payload.get('core', {})
        return cls(
            id=payload.get('rest_id'),
            name=core.get('name'),
            screen_name=core.get('screen_name'),
            created_at=core.get('created_at'),
        )
