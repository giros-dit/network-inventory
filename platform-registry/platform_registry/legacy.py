import logging
from typing import List

from ncclient import manager
from ncclient.capabilities import Capability
from pygnmi.client import gNMIclient

from platform_registry.clients.ngsi_ld import NGSILDAPI
from platform_registry.models.ngsi_ld.platform import (
    BelongsTo,
    Credentials,
    Module,
    ModuleSet,
    Platform,
    Protocol,
)
from platform_registry.models.rest import (
    CredentialsConfig,
    ProtocolConfig,
    Registration,
)

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


def build_credentials(
    cred_config: CredentialsConfig, protocol: Protocol
) -> Credentials:
    # Build Credentials entity
    credentials_entity = Credentials(
        id="urn:ngsi-ld:Credentials:{0}".format(protocol.id),
        username={"value": cred_config.username},
        password={"value": cred_config.password.get_secret_value()},
        hasProtocol={"object": protocol.id},
    )
    logger.info("Building %s" % credentials_entity.id)
    return credentials_entity


def build_module_set(platform: Platform, name: str = "default") -> ModuleSet:
    # Produce ModuleSet entity
    module_set_entity = ModuleSet(
        id="urn:ngsi-ld:ModuleSet:{0}:{1}".format(platform.id, name),
        name={"value": name},
        definedBy={"object": platform.id},
    )
    logger.info("Building %s" % module_set_entity.id)
    return module_set_entity


def build_platform(registration: Registration) -> Platform:
    platform_entity = Platform(
        id="urn:ngsi-ld:Platform:{0}".format(registration.platform_id),
        name={"value": registration.platform_name},
        vendor={"value": registration.vendor},
        softwareVersion={"value": registration.software_version},
    )
    logger.info("Building %s" % platform_entity.id)
    return platform_entity


def discover_gnmi_protocol(
    capabilities: dict, proto_config: ProtocolConfig, platform: Platform
) -> Protocol:
    encoding_formats = capabilities["supported_encodings"]
    version = capabilities["gnmi_version"]
    protocol_entity = Protocol(
        id="urn:ngsi-ld:Protocol:{0}:gnmi".format(platform.id),
        name={"value": "gnmi"},
        address={"value": str(proto_config.address)},
        port={"value": proto_config.port},
        encodingFormats={"value": encoding_formats},
        version={"value": version},
        supportedBy={"object": platform.id},
    )
    logger.info("Building %s" % protocol_entity.id)
    return protocol_entity


def discover_netconf_protocol(
    nc_capabilities: List[Capability], proto_config: ProtocolConfig, platform: Platform
) -> Protocol:
    protocol_entity = Protocol(
        id="urn:ngsi-ld:Protocol:{0}:netconf".format(platform.id),
        name={"value": "netconf"},
        address={"value": str(proto_config.address)},
        port={"value": proto_config.port},
        capabilities={
            "value": [capability.namespace_uri for capability in nc_capabilities]
        },
        supportedBy={"object": platform.id},
    )
    logger.info("Building %s" % protocol_entity.id)
    return protocol_entity


def loader(registration: Registration, ngsi_ld_api: NGSILDAPI) -> None:

    platform = build_platform(registration)
    logger.info("Creating %s" % platform.id)
    ngsi_ld_api.batchEntityUpsert([platform.dict(exclude_none=True)])

    # Check gNMI support
    if registration.gnmi:
        gnmi = registration.gnmi
        gc = gNMIclient(
            target=(str(gnmi.address), gnmi.port),
            username=gnmi.credentials.username,
            password=gnmi.credentials.password.get_secret_value(),
            insecure=True,
            debug=True,
        )
        gc.connect()
        capabilities = gc.capabilities()
        gnmi_entity = discover_gnmi_protocol(capabilities, registration.gnmi, platform)
        logger.info("Creating %s" % gnmi_entity.id)
        ngsi_ld_api.batchEntityUpsert([gnmi_entity.dict(exclude_none=True)])

        credentials_entity = build_credentials(gnmi.credentials, gnmi_entity)
        logger.info("Creating %s" % credentials_entity.id)
        ngsi_ld_api.batchEntityUpsert([credentials_entity.dict(exclude_none=True)])

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
        capabilities = nc.server_capabilities
        nc_capabilities = []
        nc_modules = []
        for c_key in capabilities:
            capability = capabilities[c_key]
            # NETCONF protocol capabilities
            if "module" not in capability.parameters:
                nc_capabilities.append(capability)
            # YANG modules
            else:
                nc_modules.append(capability)
        netconf_entity = discover_netconf_protocol(
            nc_capabilities, registration.netconf, platform
        )
        logger.info("Creating %s" % netconf_entity.id)
        ngsi_ld_api.batchEntityUpsert([netconf_entity.dict(exclude_none=True)])

        credentials_entity = build_credentials(netconf.credentials, netconf_entity)
        logger.info("Creating %s" % credentials_entity.id)
        ngsi_ld_api.batchEntityUpsert([credentials_entity.dict(exclude_none=True)])

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
            organization = _get_org_from_namespace(module.namespace_uri)
            # Catch unknown organizations
            if not organization:
                logger.error(module.namespace_uri)
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
                id="urn:ngsi-ld:Module:{0}:{1}:{2}".format(
                    name, revision, organization
                ),
                name={"value": name},
                revision={"value": revision},
                organization={"value": organization},
                namespace={"value": module.namespace_uri},
                belongsTo=belongs_to_rel,
            )
            logger.info("Creating %s" % module_entity.id)
            ngsi_ld_api.batchEntityUpsert(
                [module_entity.dict(exclude_none=True)], "update"
            )
