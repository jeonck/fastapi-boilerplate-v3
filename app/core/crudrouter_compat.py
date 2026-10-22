"""
FastAPI-CrudRouter Pydantic v2 Compatibility Patch

fastapi-crudrouter 0.8.6 (latest release) was written for Pydantic v1 and reads
`ModelField.type_`, which no longer exists in Pydantic v2. This module patches
the two helpers that rely on it. Import it before creating any CRUD router.
"""

from typing import Any, Type

from pydantic import BaseModel, create_model
from fastapi_crudrouter.core import _base, _utils


def get_pk_type(schema: Type[BaseModel], pk_field: str) -> Any:
    """Return the annotation of the primary key field (defaults to int)."""
    field = schema.model_fields.get(pk_field)
    return field.annotation if field is not None else int


def schema_factory(
    schema_cls: Type[BaseModel], pk_field_name: str = "id", name: str = "Create"
) -> Type[BaseModel]:
    """Create a schema without the primary key (used for create/update)."""
    fields = {
        field_name: (field.annotation, field)
        for field_name, field in schema_cls.model_fields.items()
        if field_name != pk_field_name
    }
    return create_model(schema_cls.__name__ + name, **fields)  # type: ignore


_utils.get_pk_type = get_pk_type
_utils.schema_factory = schema_factory
_base.schema_factory = schema_factory
