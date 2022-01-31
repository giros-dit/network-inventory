# generated by datamodel-codegen:
#   filename:  Entity.json
#   timestamp: 2020-10-29T15:53:47+00:00

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, Extra, Field, constr


class CreatedAt(BaseModel):
    __root__: datetime


class DatasetId(BaseModel):
    __root__: str


class InstanceId(BaseModel):
    __root__: AnyUrl


class ObservedAt(BaseModel):
    __root__: datetime


class ModifiedAt(BaseModel):
    __root__: datetime


class Units(BaseModel):
    __root__: str


class GeometrySchema(BaseModel):
    pass


class LdContextItem(BaseModel):
    pass


class LdContext(BaseModel):
    __root__: Union[Dict[str, Any], LdContextItem, LdContextItem]


class Name(BaseModel):
    __root__: constr(
        regex='^((\d|[a-zA-Z]|_)+(:(\d|[a-zA-Z]|_)+)?(#\d+)?)$', min_length=1
    ) = Field(..., description='NGSI-LD Name')


class Entity(BaseModel):
    class Config:
        extra = Extra.allow

    _context: Optional[LdContext] = Field(None, alias='@context')
    location: Optional[GeoProperty] = None
    observationSpace: Optional[GeoProperty] = None
    operationSpace: Optional[GeoProperty] = None
    id: str
    type: Name
    createdAt: Optional[CreatedAt] = None
    modifiedAt: Optional[ModifiedAt] = None


class Property(BaseModel):
    class Config:
        extra = Extra.allow

    type: Literal["Property"] = "Property"
    value: Union[str, float, bool, List[Any], Dict[str, Any]]
    observedAt: Optional[ObservedAt] = None
    unitCode: Optional[str] = None
    createdAt: Optional[CreatedAt] = None
    modifiedAt: Optional[ModifiedAt] = None
    datasetId: Optional[DatasetId] = None
    instanceId: Optional[InstanceId] = None


class Relationship(BaseModel):
    class Config:
        extra = Extra.allow

    type: Literal["Relationship"] = "Relationship"
    object: Union[str, List[str]]
    observedAt: Optional[ObservedAt] = None
    createdAt: Optional[CreatedAt] = None
    modifiedAt: Optional[ModifiedAt] = None
    datasetId: Optional[DatasetId] = None
    instanceId: Optional[InstanceId] = None


class GeoProperty(BaseModel):
    class Config:
        extra = Extra.allow

    type: Literal["GeoProperty"] = "GeoProperty"
    value: GeometrySchema
    observedAt: Optional[ObservedAt] = None
    createdAt: Optional[CreatedAt] = None
    modifiedAt: Optional[ModifiedAt] = None
    datasetId: Optional[DatasetId] = None
    instanceId: Optional[InstanceId] = None


Entity.update_forward_refs()