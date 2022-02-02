import logging

from ncclient import manager
from pygnmi.client import gNMIclient

from platform_registry.clients.ngsi_ld import NGSILDAPI
from platform_registry.models.ngsi_ld.platform import (
    Credentials,
    Module,
    ModuleSet,
    Platform,
    Protocol,
    hasModule,
)
from platform_registry.models.rest import Registration

ORG_NAMESPACES_MAPPING = {
    "arista": ["arista.com", "urn:aristanetworks"],
    "cisco": "cisco.com",
    "ietf": "urn:ietf:params:xml:ns",
    "huawei": "urn:huawei",
    "openconfig": "openconfig.net",
    "opendaylight": "urn:opendaylight",
    "tail-f": "tail-f.com",
}

logger = logging.getLogger(__name__)


def _get_org_from_namespace(namespace: str) -> str:
    """
    Looks for namespace string expression from ORG_NAMESPACES_MAPPING
    against a given full namespace URI.

    If namespace matches then method returns
    the respective organization name.
    """
    for org, ns in ORG_NAMESPACES_MAPPING.items():
        if isinstance(ns, list):
            for nspace in ns:
                if nspace in namespace:
                    return org
        else:
            if ns in namespace:
                return org


def loader(registration: Registration, ngsi_ld_api: NGSILDAPI) -> None:
    # Produce Credentials entity
    # Common to both protocols
    credentials_entity = Credentials(
        id="urn:ngsi-ld:Credentials:{0}".format(registration.platform_id),
        username={"value": registration.netconf.credentials.username},
        password={
            "value": registration.netconf.credentials.password.get_secret_value()
        },
    )
    logger.info("Creating %s" % credentials_entity.id)
    ngsi_ld_api.createEntity(credentials_entity.dict(exclude_none=True))
    module_entities = []
    # Produce Protocol entities
    protocol_entities = []
    if registration.gNMI:
        gnmi = registration.gNMI
        host = (gnmi.address, gnmi.port)
        gc = gNMIclient(
            host,
            username=gnmi.credentials.username,
            password=gnmi.credentials.password,
            insecure=True,
            debug=True,
        )
        gc.connect()
        capabilities = gc.capabilities()
        encoding_formats = capabilities["supported_encodings"]
        version = capabilities["gnmi_version"]
        protocol_entity = Protocol(
            id="urn:ngsi-ld:Protocol:{0}:gnmi".format(registration.platform_id),
            name={"value": "gnmi"},
            address={"value": gnmi.address},
            port={"value": gnmi.port},
            encodingFormats={"value": encoding_formats},
            version={"value": version},
            hasCredentials={"object": credentials_entity.id},
        )
        logger.info("Creating %s" % protocol_entity.id)
        ngsi_ld_api.createEntity(protocol_entity.dict(exclude_none=True))
        protocol_entities.append(protocol_entity)
    # Then NETCONF
    if registration.netconf:
        netconf = registration.netconf
        # https://community.cisco.com/t5/devnet-sandbox/
        # connect-to-ios-xr-always-on-sandbox-using-ncclient/td-p/4442858
        nc = manager.connect(
            host=str(netconf.address),
            port=netconf.port,
            timeout=30,
            username=netconf.credentials.username,
            password=netconf.credentials.password.get_secret_value(),
            hostkey_verify=False,
            look_for_keys=False,
            allow_agent=False,
        )
        nc_capabilites = []
        nc_modules = []
        capabilities = nc.server_capabilities
        for c_key in capabilities:
            capability = capabilities[c_key]
            if "module" not in capability.parameters:
                nc_capabilites.append(capability)
            else:
                nc_modules.append(capability)
        protocol_entity = Protocol(
            id="urn:ngsi-ld:Protocol:{0}:netconf".format(registration.platform_id),
            name={"value": "netconf"},
            address={"value": str(netconf.address)},
            port={"value": netconf.port},
            capabilities={
                "value": [capability.namespace_uri for capability in nc_capabilites]
            },
            hasCredentials={"object": credentials_entity.id},
        )
        logger.info("Creating %s" % protocol_entity.id)
        ngsi_ld_api.createEntity(protocol_entity.dict(exclude_none=True))
        protocol_entities.append(protocol_entity)

        has_module_list = []
        for module in nc_modules:
            name = module.parameters["module"]
            revision = module.parameters["revision"]
            logger.warning(module.parameters)
            organization = _get_org_from_namespace(module.namespace_uri)
            if not organization:
                logger.error(module.namespace_uri)
            module_entity = Module(
                id="urn:ngsi-ld:Module:{0}:{1}:{2}".format(
                    name, revision, organization
                ),
                name={"value": name},
                revision={"value": revision},
                organization={"value": organization},
                namespace={"value": module.namespace_uri},
            )
            logger.info("Creating %s" % module_entity.id)
            ngsi_ld_api.createEntity(module_entity.dict(exclude_none=True))
            module_entities.append(module_entity)
            deviation = None
            feature = None
            if "deviations" in module.parameters:
                deviation = {"value": module.parameters["deviations"].split(",")}
                logger.warning("Found deviation %s" % deviation)
            if "features" in module.parameters:
                feature = {"value": module.parameters["features"].split(",")}
                logger.warning("Found feature %s" % feature)
            has_module_rel = hasModule(
                object=module_entity.id,
                deviation=deviation,
                feature=feature,
                datasetId=module_entity.id,
            )
            has_module_list.append(has_module_rel)

    # Produce ModuleSet entity
    module_set_entity = ModuleSet(
        id="urn:ngsi-ld:ModuleSet:{0}:default".format(registration.platform_id),
        name={"value": "default"},
        hasModule=has_module_list,
    )
    logger.info("Creating %s" % module_set_entity.id)
    ngsi_ld_api.createEntity(module_set_entity.dict(exclude_none=True))

    # Produce Platform entity
    protocol_relationships = []
    for protocol in protocol_entities:
        protocol_relationships.append({"object": protocol.id, "datasetId": protocol.id})
    platform_entity = Platform(
        id="urn:ngsi-ld:Platform:{0}".format(registration.platform_id),
        name={"value": registration.platform_name},
        vendor={"value": registration.vendor},
        softwareVersion={"value": registration.software_version},
        hasProtocol=protocol_relationships,
        hasModuleSet=[{"object": module_set_entity.id}],
    )
    ngsi_ld_api.createEntity(platform_entity.dict(exclude_none=True))
    logger.info("Creating %s" % platform_entity.id)
