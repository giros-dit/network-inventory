from typing import List, Literal, Optional, Union

from platform_registry.models.ngsi_ld.entity import (Entity, Property,
                                                     Relationship)
from pydantic import Extra


class BelongsTo(Relationship):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    conformanceType: Optional[Property]
    deviation: Optional[Property]
    feature: Optional[Property]
    location: Optional[Property]


class Credentials(Entity):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    type: Literal["Credentials"] = "Credentials"
    hasProtocol: Relationship
    username: Property
    password: Property


class Datastore(Entity):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    type: Literal["Datastore"] = "Datastore"
    name: Property
    supportedBy: Relationship


class HasSubmodule(Relationship):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    location: Optional[Property]


class Module(Entity):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    type: Literal["Module"] = "Module"
    belongsTo: Optional[BelongsTo]
    name: Property
    namespace: Optional[Property]
    organization: Optional[Property]
    revision: Property


class ModuleSet(Entity):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    type: Literal["ModuleSet"] = "ModuleSet"
    definedBy: Optional[Union[Relationship, List[Relationship]]]
    name: Property


class Platform(Entity):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    type: Literal["Platform"] = "Platform"
    name: Property
    vendor: Property
    softwareVersion: Property
    softwareFlavor: Optional[Property]
    osVersion: Optional[Property]
    osType: Optional[Property]


class Protocol(Entity):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    type: Literal["Protocol"] = "Protocol"
    name: Property
    address: Property
    port: Property
    capabilities: Optional[Property]
    encodingFormats: Optional[Property]
    version: Optional[Property]
    supportedBy: Relationship


class Schema(Entity):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    type: Literal["Schema"] = "Schema"
    implementedBy: Union[Relationship, List[Relationship]]
    name: Property


class Submodule(Entity):

    class Config:
        validate_assignment = True
        extra = Extra.forbid
        allow_population_by_field_name = True

    type: Literal["Submodule"] = "Submodule"
    isSubmoduleOf: Relationship
    name: Property
    revision: Property
