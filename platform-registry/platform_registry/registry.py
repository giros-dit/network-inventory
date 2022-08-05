import logging
import os
import xml.etree.ElementTree as ET
from cmath import log
from re import S
from typing import List

from ncclient import manager
from ncclient.capabilities import Capability
from pygnmi.client import gNMIclient

from platform_registry.clients.ngsi_ld import NGSILDAPI
from platform_registry.gnmi_legacy import loader as gnmi_legacy_loader
from platform_registry.models.ngsi_ld.entity import DatasetId
from platform_registry.models.ngsi_ld.platform import (BelongsTo, Credentials,
                                                       Datastore, Module,
                                                       ModuleSet, Platform,
                                                       Protocol, Schema,
                                                       Submodule)
from platform_registry.models.rest import (CredentialsConfig, ProtocolConfig,
                                           Registration)
from platform_registry.netconf_legacy import loader as netconf_legacy_loader

NS = {"": "urn:ietf:params:xml:ns:yang:ietf-yang-library"}

logger = logging.getLogger(__name__)
script_dir = os.path.dirname(__file__)

def build_credentials(
    cred_config: CredentialsConfig, protocol: Protocol, platform: Platform
) -> Credentials:
    # Build Credentials entity
    credentials_entity = Credentials(
        id="urn:ngsi-ld:Credentials:{0}".format(platform.id.split(":")[-1]),
        username={"value": cred_config.username},
        password={"value": cred_config.password.get_secret_value()},
        hasProtocol={"object": protocol.id},
    )
    logger.info("Building %s" % credentials_entity.id)
    return credentials_entity


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
        id="urn:ngsi-ld:Protocol:{0}:gnmi".format(platform.id.split(":")[-1]),
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
        id="urn:ngsi-ld:Protocol:{0}:netconf".format(platform.id.split(":")[-1]),
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

    platform_entity = build_platform(registration)
    logger.info("Creating %s" % platform_entity.id)
    ngsi_ld_api.batchEntityUpsert([platform_entity.dict(exclude_none=True)])

    modules_discovered = False

    # Then NETCONF
    if registration.netconf:
        logger.info("Configuring netconf")
        netconf = registration.netconf
        device_params = {}
        # ncclient parsing issue for Huawei
        # https://github.com/ncclient/ncclient/issues/289
        if "huawei" in registration.vendor.lower():
            device_params = {"name": "huaweiyang"}
        nc = manager.connect(
            host=str(netconf.address),
            port=netconf.port,
            timeout=30,
            username=netconf.credentials.username,
            password=netconf.credentials.password.get_secret_value(),
            # https://community.cisco.com/t5/devnet-sandbox/
            # connect-to-ios-xr-always-on-sandbox-using-ncclient/td-p/4442858
            hostkey_verify=False,
            look_for_keys=False,
            allow_agent=False,
            device_params=device_params
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
            nc_capabilities, registration.netconf, platform_entity
        )
        logger.info("Creating %s" % netconf_entity.id)
        ngsi_ld_api.batchEntityUpsert([netconf_entity.dict(exclude_none=True)])

        credentials_entity = build_credentials(
            netconf.credentials, netconf_entity, platform_entity)
        logger.info("Creating %s" % credentials_entity.id)
        ngsi_ld_api.batchEntityUpsert([credentials_entity.dict(exclude_none=True)])

        # Collect modules from YANG Library, if supported
        for nc_module in nc_modules:
            if nc_module.parameters["module"] == "ietf-yang-library":
                logger.info("Platform implements YANG Library")
                # Check YANG Library latest release (RFC 8525)
                if nc_module.parameters["revision"] == "2019-01-04":
                    logger.info(
                        "Supported 2019-01-04 version of YANG Library (RFC 8525)")
                    #load_yang_library_rfc8525()
                    filter_path = "netconf_filters/yang-library-rfc8525.xml"
                    yl_filter = open(os.path.join(script_dir, filter_path)).read()
                    netconf_reply = nc.get(yl_filter).xml
                    tree = ET.fromstring(netconf_reply)
                    reply_data = tree[0][0]

                    # Produce Datastore entity
                    datastore_list = reply_data.iterfind("datastore", NS)
                    for datastore in datastore_list:
                        name = datastore.find("name", NS).text
                        datastore_entity = Datastore(
                            id="urn:ngsi-ld:Datastore:{0}:{1}".format(
                                platform_entity.id.split(":")[-1], name),
                            name={"value": name},
                            supportedBy={"object": platform_entity.id},
                        )
                        logger.info("Creating %s" % datastore_entity.id)
                        ngsi_ld_api.batchEntityUpsert(
                            [datastore_entity.dict(exclude_none=True)], "update"
                        )

                    # Produce Schema entity
                    schema_list = reply_data.iterfind("schema", NS)
                    for schema in schema_list:
                        name = schema.find("name", NS).text
                        datastores = []
                        for ds in reply_data.iterfind("datastore", NS):
                            ds_schema = ds.find("schema", NS).text
                            if ds_schema == name:
                                ds_name = ds.find("name", NS).text
                                datastore_id = "urn:ngsi-ld:Datastore:{0}:{1}".format(
                                    platform_entity.id.split(":")[-1], ds_name)
                                datastores.append(
                                    {"type": "Relationship",
                                    "object": datastore_id,
                                    "datasetId": datastore_id}
                                )
                        schema_entity = Schema(
                            id="urn:ngsi-ld:Schema:{0}:{1}".format(
                                platform_entity.id.split(":")[-1], name),
                            name={"value": name},
                            implementedBy=datastores,
                        )
                        logger.info("Creating %s" % schema_entity.id)
                        ngsi_ld_api.batchEntityUpsert(
                            [schema_entity.dict(exclude_none=True)], "update"
                        )

                    # Produce ModuleSet entity
                    module_set_list = reply_data.iterfind("module-set", NS)
                    for module_set in module_set_list:
                        name = module_set.find("name", NS).text
                        schemas = []
                        for sch in reply_data.iterfind("schema", NS):
                            ms_name = sch.find("module-set", NS).text
                            if ms_name == name:
                                schema_name = sch.find("name", NS).text
                                schema_id = "urn:ngsi-ld:Schema:{0}:{1}".format(
                                    platform_entity.id.split(":")[-1], schema_name)
                                schemas.append(
                                    {"type": "Relationship",
                                    "object": schema_id,
                                    "datasetId": schema_id}
                                )

                        module_set_entity = ModuleSet(
                            id="urn:ngsi-ld:ModuleSet:{0}:{1}".format(
                                platform_entity.id.split(":")[-1], name),
                            name={"value": name}
                        )
                        if schemas:
                            module_set_entity.definedBy = schemas

                        logger.info("Creating %s" % module_set_entity.id)
                        ngsi_ld_api.batchEntityUpsert(
                            [module_set_entity.dict(exclude_none=True)], "update"
                        )

                        module_list = module_set.iterfind("module", NS)
                        for module in module_list:
                            name = module.find("name", NS).text
                            revision = module.find("revision", NS).text
                            namespace = module.find("namespace", NS).text
                            feature_list = module.findall("feature", NS)
                            deviation_list = module.findall("deviation", NS)
                            submodule_list = module.findall("submodule", NS)

                            feature = None
                            if feature_list:
                                feature = {
                                    "value": [feat.text for feat in feature_list]
                                }

                            deviation = None
                            if deviation_list:
                                deviation = {"value": []}
                                for dev in deviation_list:
                                    deviation["value"].append(dev.text)

                            # Build Module entity
                            belongs_to_rel = BelongsTo(
                                object=module_set_entity.id,
                                deviation=deviation,
                                feature=feature,
                                datasetId=module_set_entity.id,
                                conformanceType={"value": "implement"}
                            )
                            module_entity = Module(
                                id="urn:ngsi-ld:Module:{0}:{1}".format(
                                    name, revision
                                ),
                                name={"value": name},
                                revision={"value": revision},
                                namespace={"value": namespace},
                                belongsTo=belongs_to_rel,
                            )
                            logger.info("Creating %s" % module_entity.id)
                            ngsi_ld_api.batchEntityUpsert(
                                [module_entity.dict(exclude_none=True)], "update"
                            )

                            # Build Submodule entity
                            for submodule in submodule_list:
                                name = submodule.find("name", NS).text
                                revision = submodule.find("revision", NS).text

                                belongs_to_rel = BelongsTo(
                                    object=module_set_entity.id,
                                    datasetId=module_set_entity.id
                                )

                                submodule_entity = Submodule(
                                id="urn:ngsi-ld:Submodule:{0}:{1}".format(
                                    name, revision
                                ),
                                name={"value": name},
                                revision={"value": revision},
                                isSubmoduleOf={"object": module_entity.id},
                                belongsTo=belongs_to_rel
                            )
                            logger.info("Creating %s" % submodule_entity.id)
                            ngsi_ld_api.batchEntityUpsert(
                                [submodule_entity.dict(exclude_none=True)], "update"
                            )

                        # Find modules that are only imported
                        module_list = module_set.iterfind("import-only-module", NS)
                        for module in module_list:
                            name = module.find("name", NS).text
                            revision = module.find("revision", NS).text
                            namespace = module.find("namespace", NS).text
                            submodule_list = module.findall("submodule", NS)

                            # Build Module entity
                            belongs_to_rel = BelongsTo(
                                object=module_set_entity.id,
                                datasetId=module_set_entity.id,
                                conformanceType={"value": "import"}
                            )
                            module_entity = Module(
                                id="urn:ngsi-ld:Module:{0}:{1}".format(
                                    name, revision
                                ),
                                name={"value": name},
                                revision={"value": revision},
                                namespace={"value": namespace},
                                belongsTo=belongs_to_rel,
                            )
                            logger.info("Creating %s" % module_entity.id)
                            ngsi_ld_api.batchEntityUpsert(
                                [module_entity.dict(exclude_none=True)], "update"
                            )

                            # Build Submodule entity
                            for submodule in submodule_list:
                                name = submodule.find("name", NS).text
                                revision = submodule.find("revision", NS).text

                                belongs_to_rel = BelongsTo(
                                    object=module_set_entity.id,
                                    datasetId=module_set_entity.id
                                )

                                submodule_entity = Submodule(
                                    id="urn:ngsi-ld:Submodule:{0}:{1}".format(
                                        name, revision
                                    ),
                                    name={"value": name},
                                    revision={"value": revision},
                                    isSubmoduleOf={"object": module_entity.id},
                                    belongsTo=belongs_to_rel
                                )
                                logger.info("Creating %s" % submodule_entity.id)
                                ngsi_ld_api.batchEntityUpsert(
                                    [submodule_entity.dict(exclude_none=True)], "update"
                                )

                    modules_discovered = True

                # Check YANG Library first release (RFC 7895)
                elif nc_module.parameters["revision"] == "2016-06-21":
                    logger.info(
                        "Supported 2016-06-21 version of YANG Library (RFC 7895)")
                    #load_yang_library_rfc7895()
                    filter_path = "netconf_filters/yang-library-rfc7895.xml"
                    yl_filter = open(os.path.join(script_dir, filter_path)).read()
                    netconf_reply = nc.get(yl_filter).xml
                    tree = ET.fromstring(netconf_reply)
                    reply_data = tree[0][0]
                    module_set_id = reply_data.find("module-set-id", NS).text

                    # Produce ModuleSet entity
                    module_set_entity = ModuleSet(
                        id="urn:ngsi-ld:ModuleSet:{0}:{1}".format(
                            platform_entity.id.split(":")[-1], module_set_id),
                        name={"value": module_set_id},
                        definedBy={"object": platform_entity.id},
                    )
                    logger.info("Creating %s" % module_set_entity.id)
                    ngsi_ld_api.batchEntityUpsert(
                        [module_set_entity.dict(exclude_none=True)], "update"
                    )

                    module_list = reply_data.iterfind("module", NS)
                    for module in module_list:
                        name = module.find("name", NS).text
                        revision = module.find("revision", NS).text
                        namespace = module.find("namespace", NS).text
                        conformance_type = module.find("conformance-type", NS).text
                        feature_list = module.findall("feature", NS)
                        deviation_list = module.findall("deviation", NS)
                        submodule_list = module.findall("submodule", NS)

                        feature = None
                        if feature_list:
                            feature = {
                                "value": [feat.text for feat in feature_list]
                            }

                        deviation = None
                        if deviation_list:
                            deviation = {"value": []}
                            for dev in deviation_list:
                                dev_name = dev.find("name", NS).text
                                deviation["value"].append(dev_name)

                        # Build Module entity
                        belongs_to_rel = BelongsTo(
                            object=module_set_entity.id,
                            deviation=deviation,
                            feature=feature,
                            datasetId=module_set_entity.id,
                            conformanceType={"value": conformance_type}
                        )
                        module_entity = Module(
                            id="urn:ngsi-ld:Module:{0}:{1}".format(
                                name, revision
                            ),
                            name={"value": name},
                            revision={"value": revision},
                            namespace={"value": namespace},
                            belongsTo=belongs_to_rel,
                        )
                        logger.info("Creating %s" % module_entity.id)
                        ngsi_ld_api.batchEntityUpsert(
                            [module_entity.dict(exclude_none=True)], "update"
                        )

                        # Build Submodule entity
                        for submodule in submodule_list:
                            name = submodule.find("name", NS).text
                            revision = submodule.find("revision", NS).text

                            belongs_to_rel = BelongsTo(
                                object=module_set_entity.id,
                                datasetId=module_set_entity.id
                            )

                            submodule_entity = Submodule(
                                id="urn:ngsi-ld:Submodule:{0}:{1}".format(
                                    name, revision
                                ),
                                name={"value": name},
                                revision={"value": revision},
                                isSubmoduleOf={"object": module_entity.id},
                                belongsTo=belongs_to_rel
                            )
                            logger.info("Creating %s" % submodule_entity.id)
                            ngsi_ld_api.batchEntityUpsert(
                                [submodule_entity.dict(exclude_none=True)], "update"
                            )
                    modules_discovered = True
                else:
                    logger.error("YANG Library {0} release not supported.".format(
                        nc_module.parameters["revision"]
                    ))
                break

        # Discover modules through NETCONF capabalities
        if not modules_discovered:
            logger.info("Collecting modules through legacy NETCONF capabilities mechanism")
            netconf_legacy_loader(
                platform=platform_entity,netconf=netconf_entity,
                credentials=credentials_entity, ngsi_ld_api=ngsi_ld_api)
            modules_discovered = True

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
        gnmi_entity = discover_gnmi_protocol(
            capabilities, registration.gnmi, platform_entity)
        logger.info("Creating %s" % gnmi_entity.id)
        ngsi_ld_api.batchEntityUpsert([gnmi_entity.dict(exclude_none=True)])

        credentials_entity = build_credentials(
            gnmi.credentials, gnmi_entity, platform_entity)
        logger.info("Creating %s" % credentials_entity.id)
        ngsi_ld_api.batchEntityUpsert([credentials_entity.dict(exclude_none=True)])

        # Discover modules through gNMI capabalities
        if not modules_discovered:
            logger.info("Collecting modules through legacy gNMI capabilities mechanism")
            gnmi_legacy_loader(
                platform=platform_entity,gnmi=gnmi_entity,
                credentials=credentials_entity,ngsi_ld_api=ngsi_ld_api)
            modules_discovered = True

