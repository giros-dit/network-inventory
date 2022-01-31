from typing import List, Literal, Optional

from platform_registry.models.ngsi_ld.entity import (Entity, Property,
                                                     Relationship)


class Credentials(Entity):
    type: Literal["Credentials"] = "Credentials"
    username: Property
    password: Property

class Datastore(Entity):
    type: Literal["Datastore"] = "Datastore"
    name: Property
    hasSchema: Relationship

class hasModule(Relationship):
    feature: Optional[Property]
    deviation: Optional[Property]
    conformanceType: Optional[Property]
    location: Optional[Property]

class hasSubmodule(Relationship):
    location: Optional[Property]

class Module(Entity):
    type: Literal["Module"] = "Module"
    name: Property
    revision: Property
    organization: Property
    namespace: Property
    includesSubmodule: Optional[Relationship]

class ModuleSet(Entity):
    type: Literal["ModuleSet"] = "ModuleSet"
    name: Property
    hasModule: List[hasModule]
    hasSubmodule: Optional[hasSubmodule]

class Platform(Entity):
    type: Literal["Platform"] = "Platform"
    name: Property
    vendor: Property
    softwareVersion: Property
    softwareFlavor: Optional[Property]
    osVersion: Optional[Property]
    osType: Optional[Property]
    hasProtocol: List[Relationship]
    hasModuleSet: Optional[List[Relationship]]
    hasDatastore: Optional[List[Relationship]]

class Protocol(Entity):
    type: Literal["Protocol"] = "Protocol"
    name: Property
    address: Property
    port: Property
    capabilities: Optional[Property]
    encodingFormats: Optional[Property]
    version: Optional[Property]
    hasCredentials: Optional[Relationship]

class Schema(Entity):
    type: Literal["Schema"] = "Schema"
    name: Property
    hasModuleSet: Relationship

class Submodule(Entity):
    type: Literal["Submodule"] = "Submodule"
    name: Property
    revision: Property
