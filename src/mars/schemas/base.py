from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

IdType = TypeVar("IdType", bound=str)


class SchemaBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class IdRefSchema(SchemaBase, Generic[IdType]):
    id: IdType
