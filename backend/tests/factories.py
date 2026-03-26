from __future__ import annotations

import uuid

import factory
from factory import LazyFunction

from app.core.security import hash_password
from app.models.document import Document, VisibilityEnum
from app.models.user import User


class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    hashed_password = LazyFunction(lambda: hash_password("password123"))
    is_active = True


class DocumentFactory(factory.Factory):
    class Meta:
        model = Document

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    filename = factory.Sequence(lambda n: f"document_{n}.pdf")
    file_path = factory.LazyAttribute(lambda o: f"/app/uploads/{o.user_id}/{o.filename}")
    visibility = VisibilityEnum.private
    chunk_count = 10
