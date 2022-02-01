import argparse
import json
import logging
import sys
import traceback

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
        yield lst[i:i + n]

def deserialize_yang(data: dict) -> binding.yang_catalog:
    return pybindJSON.loads_ietf(data, binding, "yang_catalog")

def compute_module_properties(
    data: binding.yc_module_yang_catalog__catalog_modules_module) -> dict:
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
        properties_dict["moduleClassification"] = {
            "value": data.module_classification}
    if data.compilation_status:
        properties_dict["compilationStatus"] = {
            "value": data.compilation_status}
    if data.compilation_result:
        properties_dict["compilationResult"] = {
            "value": data.compilation_result}
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
        properties_dict["semanticVersion"] = {
            "value": data.semantic_version}
    if data.derived_semantic_version:
        properties_dict["derivedSemanticVersion"] = {
            "value": data.derived_semantic_version}
    return properties_dict

def compute_dependency_id(df: pd.DataFrame, name: str, revision: str = None) -> str:
    logger.debug("Computing entity id for dependency %s" % name)
    dependency_module = None
    if not revision:
        filtered_modules = df[df["name"] == name].sort_values(
                by="revision", ascending=False)
        # Get latest revision
        filtered_modules["revision"] = filtered_modules[
            "revision"].dt.strftime('%Y-%m-%d')
        # Catch Ghost dependency
        if filtered_modules.empty:
            revision = "unknown"
            organization = "unknown"
            module_type = "module"
        else:
            dependency_module = filtered_modules.iloc[0]
            revision = dependency_module["revision"]
            organization = dependency_module["organization"]
            module_type = dependency_module["module-type"]
    else:
        filtered_modules = df[
            (df["name"] == name) & (df["revision"] == str(revision))]
        # Catch Ghost dependency
        if filtered_modules.empty:
            organization = "unknown"
            module_type = "module"
        else:
            dependency_module = filtered_modules.iloc[0]
            organization = dependency_module["organization"]
            module_type = dependency_module["module-type"]
    # Generate entity ID
    if module_type == "module":
        id = "urn:ngsi-ld:Module:{0}:{1}:{2}".format(
            name, revision, organization)
    else:
        id = "urn:ngsi-ld:Submodule:{0}:{1}:{2}".format(
            name, revision, organization)
    return id

def build_module_entity(
        df: pd.DataFrame,
        yang_data: binding.yc_module_yang_catalog__catalog_modules_module) -> dict:
    entity = None
    # Compute submodule relationship
    submodules = None
    if yang_data.submodule.items():
        submodules = []
        for _, submodule in yang_data.submodule.iteritems():
            entity_id = compute_dependency_id(
                df, submodule.name, submodule.revision)
            submodules.append({
                "object": entity_id,
                "datasetId": entity_id
            })
    # Compute dependencies
    dependencies = None
    if yang_data.dependencies.items():
        dependencies = []
        for _, dependency in yang_data.dependencies.iteritems():
            entity_id = compute_dependency_id(
                df, dependency.name, dependency.revision)
            dependencies.append({
                "object": entity_id,
                "datasetId": entity_id
            })
    # Compute dependents
    dependents = None
    if yang_data.dependents.items():
        dependents = []
        for _, dependent in yang_data.dependents.iteritems():
            entity_id = compute_dependency_id(
                df, dependent.name, dependent.revision)
            dependents.append({
                "object": entity_id,
                "datasetId": entity_id
            })
    # Compute properties
    yang_module_id = "{0}:{1}:{2}".format(
            yang_data.name,
            yang_data.revision,
            yang_data.organization
    )
    properties = compute_module_properties(yang_data)
    if yang_data.module_type == "module":
        id = "urn:ngsi-ld:Module:{0}".format(
            yang_module_id
        )
        entity = Module(
            id=id,
            name={"value": yang_data.name},
            revision={"value": yang_data.revision},
            organization={"value": yang_data.organization},
            namespace={"value": yang_data.namespace},
            includesSubmodule=submodules,
            hasDependency=dependencies,
            hasDependent=dependents,
            **properties
        )
    # Submodule then
    else:
        id = "urn:ngsi-ld:Submodule:{0}".format(
            yang_module_id
        )
        entity = Submodule(
            id=id,
            name={"value": yang_data.name},
            revision={"value": yang_data.revision},
            organization={"value": yang_data.organization},
            namespace={"value": yang_data.namespace},
            includesSubmodule=submodules,
            hasDependency=dependencies,
            hasDependent=dependents,
            **properties
        )
    return entity.dict(exclude_none=True, by_alias=True)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--update',
        dest='update',
        default=False,
        required=False,
        action='store_true',
        help='Pull data from YANG Catalog.')
    argv = sys.argv[1:]
    known_args, _ = parser.parse_known_args(argv)

    if known_args.update:
        # Init YANGCatalog API Client
        yangcatalog_api = YangCatalogAPI()
        dataset = yangcatalog_api.get_whole_catalog()
        f = open('data.json', "w")
        f.write(json.dumps(dataset))
        f.close()

    # Init NGSI-LD REST API Client
    # Set URL to Stellio API-Gateway
    #url = "http://api-gateway:8080"
    url = "http://localhost:8080"
    headers = {"Accept": "application/json"}
    context = "http://context-catalog:8080/context.jsonld"
    debug = False
    ngsi_ld_api = NGSILDAPI(url, headers=headers,
                        context=context, debug=debug)

    f = open('data.json')
    data = json.load(f)
    # Build pandas DataFrame from module list for fast queries
    df = pd.json_normalize(data["yang-catalog:catalog"]["modules"]["module"])
    df["revision"] = pd.to_datetime(df["revision"], format="%Y-%m-%d", errors="coerce")
    # Build Python generator from module list for NGSI-LD transformation
    module_list_generator = chunks(
        data["yang-catalog:catalog"]["modules"]["module"], BATCH_SIZE
    )
    while True:
        try:
            module_list_batch = next(module_list_generator)
            yang_batch = {
                "yang-catalog:catalog": {
                    "modules": {
                        "module": module_list_batch
                    }
                }
            }
            yc = deserialize_yang(yang_batch)
            for index, module in yc.catalog.modules.module.iteritems():
                logger.debug("Parsing %s" % module.name)
                module_entity = build_module_entity(df, module)
                logger.info("Created %s" % module_entity["id"])
                ngsi_ld_api.createEntity(module_entity)
        except StopIteration:
            break
        except Exception as e:
            logger.error(traceback.format_exc())
            continue
