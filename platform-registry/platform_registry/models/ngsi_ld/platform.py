from typing import List, Literal, Optional

from platform_registry.models.ngsi_ld.entity import Entity, Property, Relationship


class BelongsTo(Relationship):
    conformanceType: Optional[Property]
    deviation: Optional[Property]
    feature: Optional[Property]
    location: Optional[Property]


class Credentials(Entity):
    type: Literal["Credentials"] = "Credentials"
    hasProtocol: Relationship
    username: Property
    password: Property


class Datastore(Entity):
    type: Literal["Datastore"] = "Datastore"
    hasSchema: Relationship
    name: Property


class HasSubmodule(Relationship):
    location: Optional[Property]


class Module(Entity):
    type: Literal["Module"] = "Module"
    belongsTo: Optional[BelongsTo]
    name: Property
    namespace: Property
    organization: Property
    revision: Property


class ModuleSet(Entity):
    type: Literal["ModuleSet"] = "ModuleSet"
    definedBy: Relationship
    name: Property


class Platform(Entity):
    type: Literal["Platform"] = "Platform"
    name: Property
    vendor: Property
    softwareVersion: Property
    softwareFlavor: Optional[Property]
    osVersion: Optional[Property]
    osType: Optional[Property]


class Protocol(Entity):
    type: Literal["Protocol"] = "Protocol"
    name: Property
    address: Property
    port: Property
    capabilities: Optional[Property]
    encodingFormats: Optional[Property]
    version: Optional[Property]
    supportedBy: Relationship


class Schema(Entity):
    type: Literal["Schema"] = "Schema"
    implementedBy: Relationship
    name: Property


class Submodule(Entity):
    type: Literal["Submodule"] = "Submodule"
    isSubmoduleOf: Relationship
    name: Property
    revision: Property
