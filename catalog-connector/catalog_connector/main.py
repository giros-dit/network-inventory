import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Union
from urllib.parse import urlparse

import pandas as pd
import pyangbind.lib.pybindJSON as pybindJSON

from catalog_connector.clients.ngsi_ld import NGSILDAPI
from catalog_connector.clients.yang_catalog import YangCatalogAPI
from catalog_connector.models.ngsi_ld.catalog import Module, Submodule
from catalog_connector.models.yang import yang_catalog as binding

logger = logging.getLogger(__name__)

BATCH_SIZE = 20


def chunks(lst, n):
    """
    Yield successive n-sized chunks from lst.

    Reference: https://stackoverflow.com/questions/312443/
               how-do-you-split-a-list-into-evenly-sized-chunks
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def deserialize_yang(data: dict) -> binding.yang_catalog:
    return pybindJSON.loads_ietf(data, binding, "yang_catalog")


def compute_module_properties(
    data: binding.yc_module_yang_catalog__catalog_modules_module,
) -> dict:
    properties_dict = {}
    if data.ietf.ietf_wg:
        properties_dict["ietfWg"] = {"value": data.ietf.ietf_wg}
    if data.schema:
        properties_dict["schema"] = {"value": data.schema}
    if data.generated_from:
        properties_dict["generatedFrom"] = {"value": data.generated_from}
    if data.maturity_level:
        properties_dict["maturityLevel"] = {"value": data.maturity_level}
    if data.document_name:
        properties_dict["documentName"] = {"value": data.document_name}
    if data.author_email:
        properties_dict["authorEmail"] = {"value": data.author_email}
    if data.reference:
        properties_dict["reference"] = {"value": data.reference}
    if data.module_classification:
        properties_dict["moduleClassification"] = {"value": data.module_classification}
    if data.compilation_status:
        properties_dict["compilationStatus"] = {"value": data.compilation_status}
    if data.compilation_result:
        properties_dict["compilationResult"] = {"value": data.compilation_result}
    if data.prefix:
        properties_dict["prefix"] = {"value": data.prefix}
    if data.yang_version:
        properties_dict["yangVersion"] = {"value": data.yang_version}
    if data.description:
        properties_dict["description"] = {"value": data.description}
    if data.contact:
        properties_dict["contact"] = {"value": data.contact}
    if data.belongs_to:
        properties_dict["belongsTo"] = {"value": data.belongs_to}
    if data.tree_type:
        properties_dict["treeType"] = {"value": data.tree_type}
    if data.yang_tree:
        properties_dict["yangTree"] = {"value": data.yang_tree}
    if data.expires:
        properties_dict["expires"] = {"value": data.expires}
    if data.expired:
        properties_dict["expired"] = {"value": data.expired}
    if data.semantic_version:
        properties_dict["semanticVersion"] = {"value": data.semantic_version}
    if data.derived_semantic_version:
        properties_dict["derivedSemanticVersion"] = {
            "value": data.derived_semantic_version
        }
    return properties_dict


def build_dep(
    df: pd.DataFrame,
    dep_name: str,
    dep_revision: str = None,
    dep_schema: str = None,
) -> dict:
    dependency_id = None
    # (A) revision value takes preference when identifying the module
    if dep_revision:
        filtered_modules = df[
            (df["name"] == dep_name) & (df["revision"] == str(dep_revision))
        ]
        # Catch ghost dependency
        if filtered_modules.empty:
            organization = "unknown"
            module_type = "module"
        else:
            dependency_module = filtered_modules.iloc[0]
            organization = dependency_module["organization"]
            module_type = dependency_module["module-type"]
        # Generate dependency entity ID
        dependency_id = "urn:ngsi-ld:{0}:{1}:{2}:{3}".format(
            module_type.capitalize(), dep_name, dep_revision, organization
        )
    # (B) use schema URL to identify the module
    if not dep_revision and dep_schema:
        filtered_modules = df[
            (df["name"] == dep_name) & (df["schema"] == str(dep_schema))
        ]
        revision = None
        # Catch ghost dependency
        if filtered_modules.empty:
            # Try to figure out revision date from filename
            revision = (
                urlparse(dep_schema).path.split("/")[-1].split("@")[-1].split(".")[0]
            )
            try:
                _ = datetime.strptime(revision, "%Y-%m-%d")
                filtered_modules = df[
                    (df["name"] == dep_name) & (df["revision"] == revision)
                ]
                # Catch ghost dependency
                if filtered_modules.empty:
                    organization = "unknown"
                    module_type = "module"
                else:
                    dependency_module = filtered_modules.iloc[0]
                    organization = dependency_module["organization"]
                    module_type = dependency_module["module-type"]
            except ValueError:
                revision = "unknown"
                organization = "unknown"
                module_type = "module"
        # Module found in the database
        else:
            dependency_module = filtered_modules.iloc[0]
            revision = dependency_module["revision"]
            organization = dependency_module["organization"]
            module_type = dependency_module["module-type"]
        # Generate dependency entity ID
        dependency_id = "urn:ngsi-ld:{0}:{1}:{2}:{3}".format(
            module_type.capitalize(), dep_name, revision, organization
        )
    # (C) fallback mechanism: set to unknown
    if not dep_revision and not dep_schema:
        revision = "unknown"
        organization = "unknown"
        module_type = "module"
        # Generate dependency entity ID
        dependency_id = "urn:ngsi-ld:{0}:{1}:{2}:{3}".format(
            module_type.capitalize(), dep_name, revision, organization
        )

    return {
        "object": dependency_id,
        "datasetId": dependency_id,
    }


def collect_deps(
    module_id: str,
    df: pd.DataFrame,
    yang_data: binding.yc_module_yang_catalog__catalog_modules_module,
) -> dict:
    # Compute deps
    deps = {}
    # Then this entity becomes a dependency of its dependents
    if yang_data.dependents.items():
        logger.info("Collecting dependents of {0}".format(module_id))
        deps["hasDependents"] = []
        for _, dependent in yang_data.dependents.iteritems():
            dependent_object = build_dep(
                df, dependent.name, dependent.revision, dependent.schema
            )
            deps["hasDependents"].append(dependent_object)

    # Then this entity becomes a dependent of its dependents
    if yang_data.dependencies.items():
        logger.info("Collecting dependencies of {0}".format(module_id))
        deps["hasDependencies"] = []
        for _, dependency in yang_data.dependencies.iteritems():
            dependency_object = build_dep(
                df, dependency.name, dependency.revision, dependency.schema
            )
            deps["hasDependencies"].append(dependency_object)

    return deps


def build_module_entity(
    df: pd.DataFrame, yang_data: binding.yc_module_yang_catalog__catalog_modules_module
) -> Union[Module, Submodule]:

    # Compute properties
    yang_module_id = "{0}:{1}:{2}".format(
        yang_data.name, yang_data.revision, yang_data.organization
    )
    properties = compute_module_properties(yang_data)
    if yang_data.module_type == "module":
        id = "urn:ngsi-ld:Module:{0}".format(yang_module_id)
        deps = collect_deps(id, df, yang_data)
        if deps:
            properties.update(deps)
        module = Module(
            id=id,
            name={"value": yang_data.name},
            revision={"value": yang_data.revision},
            organization={"value": yang_data.organization},
            namespace={"value": yang_data.namespace},
            **properties
        )
        return module
    # Submodule then
    else:
        id = "urn:ngsi-ld:Submodule:{0}".format(yang_module_id)
        deps = collect_deps(id, df, yang_data)
        if deps:
            properties.update(deps)
        submodule = Submodule(
            id=id,
            name={"value": yang_data.name},
            revision={"value": yang_data.revision},
            organization={"value": yang_data.organization},
            namespace={"value": yang_data.namespace},
            **properties
        )
        return submodule


def main(ngsi_ld_api: NGSILDAPI, local_catalog: bool):
    if local_catalog:
        f = open("data.json")
        catalog_data = json.load(f)
        f.close()
    else:
        # Init YANGCatalog API Client
        yangcatalog_api = YangCatalogAPI()
        logger.info("Collecting data from YANG Catalog...")
        catalog_data = yangcatalog_api.get_whole_catalog()
        logger.info("Loaded module data from YANG Catalog!")
    # Build pandas DataFrame from module list for fast queries
    df = pd.json_normalize(catalog_data["yang-catalog:catalog"]["modules"]["module"])
    # Build Python generator from module list for NGSI-LD transformation
    module_list_generator = chunks(
        catalog_data["yang-catalog:catalog"]["modules"]["module"], BATCH_SIZE
    )
    while True:
        try:
            module_list_batch = next(module_list_generator)
        except StopIteration:
            break
        yang_batch = {
            "yang-catalog:catalog": {"modules": {"module": module_list_batch}}
        }
        yc = deserialize_yang(yang_batch)
        batch_entities = []
        for _, yang_module in yc.catalog.modules.module.iteritems():
            module_entity = build_module_entity(df, yang_module)
            batch_entities.append(module_entity.dict(exclude_none=True, by_alias=True))
        # Send batch of entities
        ngsi_ld_api.batchEntityUpsert(batch_entities, "update")

    logger.info("Synchronization with YANG Catalog completed!")


if __name__ == "__main__":
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="'%(asctime)s - %(name)s - %(levelname)s - %(message)s'",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--broker-uri",
        dest="broker_uri",
        default="http://localhost:9090",
        required=False,
        help="NGSI-LD Context Broker URI.",
    )
    parser.add_argument(
        "--context-catalog-uri",
        dest="context_catalog_uri",
        default="http://context-catalog:8080/context.jsonld",
        required=False,
        help="Context Catalog URI.",
    )
    parser.add_argument(
        "--local-catalog", dest="local_catalog", default=False, required=False
    )
    argv = sys.argv[1:]
    known_args, _ = parser.parse_known_args(argv)

    # Init NGSI-LD API Client
    ngsi_ld_api = NGSILDAPI(
        url=known_args.broker_uri, context=known_args.context_catalog_uri
    )
    main(ngsi_ld_api, known_args.local_catalog)
