from __future__ import annotations

from hashlib import md5
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Generic, Iterable, Iterator, TypeVar

if TYPE_CHECKING:
    from .client import Client

T = TypeVar('T')


class PaginationContext:
    """
    Contains pagination context data.
    """
    def __init__(
        self,
        instance: Client,
        method: Callable[..., Awaitable[Any]],
        previous_cursor: str | None = None,
        next_cursor: str | None = None,
        **params
    ):
        self.instance = instance
        self.method = method
        self.previous_cursor = previous_cursor
        self.next_cursor = next_cursor
        self.params = params


class PaginatedResult(Generic[T]):
    def __init__(
        self,
        items_iter: Iterable[T],
        context: PaginationContext | None = None
    ):
        self.__items_iter = items_iter
        self.__context = context

    def set_instance(self, instance: Client) -> None:
        if not self.__context:
            return
        if not isinstance(instance, Client):
            raise TypeError(f'Instance must be a `Client`, not {instance.__class__.__name__}.')
        self.__context.instance = instance

    @property
    def previous_cursor(self) -> str | None:
        return self.__context and self.__context.previous_cursor

    @property
    def next_cursor(self) -> str | None:
        return self.__context and self.__context.next_cursor


    async def previous(self, **kwargs) -> PaginatedResult[T]:
        """
        Returns the previous page results.
        """
        context = self.__context
        if not context or not context.previous_cursor:
            return self._empty()

        params = {
            **context.params,
            **kwargs,
            'cursor': context.previous_cursor
        }
        return await context.method(context.instance, **params)

    async def next(self, **kwargs) -> PaginatedResult[T]:
        """
        Returns the next page results.
        """
        context = self.__context
        if not context or not context.next_cursor:
            return self._empty()

        params = {
            **context.params,
            **kwargs,
            'cursor': context.next_cursor
        }
        return await context.method(context.instance, **params)

    @classmethod
    def _empty(cls):
        return cls([])

    def __iter__(self) -> Iterator[T]:
        yield from self.__items_iter

    def __repr__(self) -> str:
        if not self.__context:
            return '<PaginatedResult [empty]>'

        attrs = [f'for `Client.{self.__context.method.__name__}`']

        previous_cursor = self.__context.previous_cursor
        next_cursor = self.__context.next_cursor
        if previous_cursor:
            attrs.append(f'prev="{md5(previous_cursor.encode()).hexdigest()[:8]}"')
        if next_cursor:
            attrs.append(f'next="{md5(next_cursor.encode()).hexdigest()[:8]}"')

        return f'<PaginatedResult {" ".join(attrs)}>'
