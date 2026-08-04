from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal
from uuid import UUID

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row


class DuplicateResourceError(Exception):
    pass


class ForbiddenResourceError(Exception):
    pass


class InvalidReferenceError(Exception):
    def __init__(self, field: Literal["category_id", "account_id"]):
        self.field = field
        super().__init__(field)


@contextmanager
def database_session(
    database_url: str,
    user_id: UUID,
    *,
    repeatable_read: bool = False,
) -> Iterator[Connection]:
    with psycopg.connect(database_url, row_factory=dict_row) as connection, connection.transaction():
        if repeatable_read:
            connection.execute("set transaction isolation level repeatable read")
        connection.execute(
            "select set_config('app.user_id', %s, true)",
            (str(user_id),),
        )
        yield connection
