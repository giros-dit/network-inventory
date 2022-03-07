from typing import List, Literal, Optional

from catalog_connector.models.ngsi_ld.entity import Entity, Property, Relationship
from pydantic import Field


class Module(Entity):
    class Config:
        allow_population_by_field_name = True

    type: Literal["Module"] = "Module"
    name: Property
    revision: Property
    organization: Optional[Property]
    ietfWg: Optional[Property]
    namespace: Optional[Property]
    schemaURL: Optional[Property] = Field(alias="schema")
    generatedFrom: Optional[Property]
    maturityLevel: Optional[Property]
    documentName: Optional[Property]
    authorEmail: Optional[Property]
    reference: Optional[Property]
    moduleClassification: Optional[Property]
    compilationStatus: Optional[Property]
    compilationResult: Optional[Property]
    prefix: Optional[Property]
    yangVersion: Optional[Property]
    description: Optional[Property]
    contact: Optional[Property]
    belongsTo: Optional[Property]
    treeType: Optional[Property]
    yangTree: Optional[Property]
    expires: Optional[Property]
    expired: Optional[Property]
    isDependencyOf: Optional[List[Relationship]]
    isDependentOf: Optional[List[Relationship]]
    semanticVersion: Optional[Property]
    derivedSemanticVersion: Optional[Property]


class Submodule(Module):
    class Config:
        allow_population_by_field_name = True

    type: Literal["Submodule"] = "Submodule"
