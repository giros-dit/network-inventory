import logging

from pygnmi.client import gNMIclient

from platform_registry.clients.ngsi_ld import NGSILDAPI
from platform_registry.models.ngsi_ld.platform import (BelongsTo, Credentials,
                                                       Module, ModuleSet,
                                                       Platform, Protocol)

logger = logging.getLogger(__name__)


def build_module_set(platform: Platform, name: str = "default") -> ModuleSet:
    # Produce ModuleSet entity
    module_set_entity = ModuleSet(
        id="urn:ngsi-ld:ModuleSet:{0}:{1}".format(platform.id, name),
        name={"value": name},
        definedBy={"object": platform.id},
    )
    logger.info("Building %s" % module_set_entity.id)
    return module_set_entity

def loader(platform: Platform, gnmi: Protocol,
           credentials: Credentials, ngsi_ld_api: NGSILDAPI) -> None:

    gc = gNMIclient(
        target=(str(gnmi.address.value), gnmi.port.value),
        username=credentials.username.value,
        password=credentials.password.value,
        insecure=True,
        debug=True,
    )
    gc.connect()
    capabilities = gc.capabilities()
    supported_models = capabilities["supported_models"]

    # This is Legacy mechanism, set Module Set to "default"
    module_set_entity = build_module_set(platform)
    logger.info("Creating %s" % module_set_entity.id)
    ngsi_ld_api.batchEntityUpsert([module_set_entity.dict(exclude_none=True)])

    for model in supported_models:
        name = model["name"]
        revision = model["version"]
        organization = model["organization"]
        # Build Module entity
        belongs_to_rel = BelongsTo(
            object=module_set_entity.id,
            datasetId=module_set_entity.id,
        )
        module_entity = Module(
            id="urn:ngsi-ld:Module:{0}:{1}".format(
                name, revision
            ),
            name={"value": name},
            revision={"value": revision},
            organization={"value": organization},
            belongsTo=belongs_to_rel,
        )
        logger.info("Creating %s" % module_entity.id)
        ngsi_ld_api.batchEntityUpsert(
            [module_entity.dict(exclude_none=True)], "update"
        )
