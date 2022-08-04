import logging
from typing import List

from ncclient import manager

from platform_registry.clients.ngsi_ld import NGSILDAPI
from platform_registry.models.ngsi_ld.platform import (BelongsTo, Credentials,
                                                       Module, ModuleSet,
                                                       Platform, Protocol)

logger = logging.getLogger(__name__)


def build_module_set(platform: Platform, name: str = "default") -> ModuleSet:
    # Produce ModuleSet entity
    module_set_entity = ModuleSet(
        id="urn:ngsi-ld:ModuleSet:{0}:{1}".format(
            platform.id.split(":")[-1], name),
        name={"value": name},
        definedBy={"object": platform.id},
    )
    logger.info("Building %s" % module_set_entity.id)
    return module_set_entity

def loader(platform: Platform, netconf: Protocol,
           credentials: Credentials, ngsi_ld_api: NGSILDAPI) -> None:

    # We rely on NETCONF to collect module information
    # https://community.cisco.com/t5/devnet-sandbox/
    # connect-to-ios-xr-always-on-sandbox-using-ncclient/td-p/4442858
    nc = manager.connect(
        host=str(netconf.address.value),
        port=netconf.port.value,
        timeout=30,
        username=credentials.username.value,
        password=credentials.password.value,
        hostkey_verify=False,
        look_for_keys=False,
        allow_agent=False,
    )
    capabilities = nc.server_capabilities
    nc_modules = []
    for c_key in capabilities:
        capability = capabilities[c_key]
        # NETCONF protocol capabilities
        if "module" not in capability.parameters:
            continue
        # YANG modules
        else:
            nc_modules.append(capability)

    # This is Legacy mechanism, set Module Set to "default"
    module_set_entity = build_module_set(platform)
    logger.info("Creating %s" % module_set_entity.id)
    ngsi_ld_api.batchEntityUpsert([module_set_entity.dict(exclude_none=True)])

    # Thus far, rely on NETCONF capabilities to discover YANG modules
    # NETCONF hello retrieves features, deviations,
    # and submodules (as other modules though)
    for module in nc_modules:
        name = module.parameters["module"]
        revision = module.parameters["revision"]
        # Build Module entity
        deviation = None
        feature = None
        if "deviations" in module.parameters:
            deviation = {"value": module.parameters["deviations"].split(",")}
            logger.warning("Found deviation %s" % deviation)
        if "features" in module.parameters:
            feature = {"value": module.parameters["features"].split(",")}
            logger.warning("Found feature %s" % feature)
        belongs_to_rel = BelongsTo(
            object=module_set_entity.id,
            deviation=deviation,
            feature=feature,
            datasetId=module_set_entity.id,
        )
        module_entity = Module(
            id="urn:ngsi-ld:Module:{0}:{1}".format(
                name, revision
            ),
            name={"value": name},
            revision={"value": revision},
            namespace={"value": module.namespace_uri},
            belongsTo=belongs_to_rel,
        )
        logger.info("Creating %s" % module_entity.id)
        ngsi_ld_api.batchEntityUpsert(
            [module_entity.dict(exclude_none=True)], "update"
        )
