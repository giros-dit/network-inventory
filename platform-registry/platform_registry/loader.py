import argparse
import logging
import sys

from ncclient import manager
from pygnmi.client import gNMIclient
from pyparsing import Dict

from platform_registry.clients.ngsi_ld import NGSILDAPI
from platform_registry.models.ngsi_ld.platform import (Credentials, Module,
                                                       ModuleSet, Platform,
                                                       Protocol, Submodule,
                                                       hasModule)

logger = logging.getLogger(__name__)

ORG_NAMESPACES_MAPPING = {
    "arista": ["http://arista.com", "urn:aristanetworks"],
    "cisco": "http://cisco.com",
    "ietf": "urn:ietf:params:xml:ns",
    "huawei": "urn:huawei",
    "openconfig": "http://openconfig.net",
    "opendaylight": "urn:opendaylight"
}

def get_org_from_namespace(namespace: str) -> str:
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

def main(args: dict, ngsi_ld_api: NGSILDAPI):
    # Produce Credentials entity
    # Common to both protocols
    credentials_entity = Credentials(
        id="urn:ngsi-ld:Credentials:{0}".format(args.platform_id),
        username={"value": args.username},
        password={"value": args.password}
    )
    logger.info("Creating %s" % credentials_entity.id)
    ngsi_ld_api.createEntity(credentials_entity.dict(exclude_none=True))
    module_entities = []
    # Produce Protocol entities
    protocol_entities = []
    if "gnmi" in args.protocol:
        host = (args.address, args.gnmi_port)
        gc = gNMIclient(host, username=args.username, password=args.password, insecure=True, debug=True)
        gc.connect()
        capabilities = gc.capabilities()
        encoding_formats = capabilities["supported_encodings"]
        version = capabilities["gnmi_version"]
        protocol_entity = Protocol(
            id="urn:ngsi-ld:Protocol:{0}:gnmi".format(args.platform_id),
            name={"value": args.protocol},
            address={"value": args.address},
            port={"value": args.gnmi_port},
            encodingFormats={"value": encoding_formats},
            version={"value": version},
            hasCredentials={"object": credentials_entity.id}
        )
        logger.info("Creating %s" % protocol_entity.id)
        ngsi_ld_api.createEntity(protocol_entity.dict(exclude_none=True))
        protocol_entities.append(protocol_entity)
    # Then NETCONF
    if "netconf" in args.protocol:
        nc=manager.connect(
            host=args.address, port=args.netconf_port, timeout=30,
            username=args.username, password=args.password, hostkey_verify=False)
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
            id="urn:ngsi-ld:Protocol:{0}:netconf".format(args.platform_id),
            name={"value": args.protocol},
            address={"value": args.address},
            port={"value": args.netconf_port},
            capabilities={"value": [capability.namespace_uri for capability in nc_capabilites]},
            hasCredentials={"object": credentials_entity.id}
        )
        logger.info("Creating %s" % protocol_entity.id)
        ngsi_ld_api.createEntity(protocol_entity.dict(exclude_none=True))
        protocol_entities.append(protocol_entity)

        has_module_list = []
        for module in nc_modules:
            name = module.parameters["module"]
            revision = module.parameters["revision"]
            organization = get_org_from_namespace(module.namespace_uri)
            if not organization:
                import pdb; pdb.set_trace()
            module_entity = Module(
                id="urn:ngsi-ld:Module:{0}:{1}:{2}".format(
                    name, revision, organization),
                name={"value": name},
                revision={"value": revision},
                organization={"value": organization},
                namespace={"value": module.namespace_uri}
            )
            logger.info("Creating %s" % module_entity.id)
            ngsi_ld_api.createEntity(module_entity.dict(exclude_none=True))
            module_entities.append(module_entity)

            deviation = None
            feature = None
            if "deviations" in module.parameters:
                deviation = module.parameters["deviations"]
            if "features" in module.parameters:
                feature = module.parameters["features"]
            has_module_rel = hasModule(
                object=module_entity.id,
                deviation=deviation,
                feature=feature,
                datasetId=module_entity.id
            )
            has_module_list.append(has_module_rel)

    # Produce ModuleSet entity
    module_set_entity = ModuleSet(
        id="urn:ngsi-ld:ModuleSet:{0}:default".format(args.platform_id),
        name={"value": "default"},
        hasModule=has_module_list
    )
    logger.info("Creating %s" % module_set_entity.id)
    ngsi_ld_api.createEntity(module_set_entity.dict(exclude_none=True))

    # Produce Platform entity
    protocol_relationships = []
    for protocol in protocol_entities:
        protocol_relationships.append(
            {"object": protocol.id,
            "datasetId": protocol.id}
        )
    platform_entity = Platform(
        id="urn:ngsi-ld:Platform:{0}".format(args.platform_id),
        name={"value": args.platform_name},
        vendor={"value": args.vendor},
        softwareVersion={"value": args.software_version},
        hasProtocol=protocol_relationships,
        hasModuleSet=[{"object": module_set_entity.id}]
    )
    ngsi_ld_api.createEntity(platform_entity.dict(exclude_none=True))
    logger.info("Creating %s" % platform_entity.id)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--protocol',
        dest='protocol',
        required=True,
        choices=["gnmi", "netconf"],
        nargs="+",
        help='Types of network management protocol.')
    parser.add_argument(
        '--address',
        dest='address',
        required=True,
        help='IP address of network management protocol service in the platform.')
    parser.add_argument(
        '--gnmi-port',
        dest='gnmi_port',
        required=True,
        help='Port of gNMI protocol service in the platform.')
    parser.add_argument(
        '--netconf-port',
        dest='netconf_port',
        required=True,
        help='Port of NETCONF protocol service in the platform.')
    parser.add_argument(
        '--username',
        dest='username',
        required=True,
        help='Username of network management protocol service in the platform.')
    parser.add_argument(
        '--password',
        dest='password',
        required=True,
        help='Password of network management protocol service in the platform.')
    parser.add_argument(
        '--platform-id',
        dest='platform_id',
        required=True,
        help='Identifier of the platform.')
    parser.add_argument(
        '--platform-name',
        dest='platform_name',
        required=True,
        help='Name of the platform.')
    parser.add_argument(
        '--vendor',
        dest='vendor',
        required=True,
        help='Vendor of the platform.')
    parser.add_argument(
        '--software-version',
        dest='software_version',
        required=True,
        help='Software version of the platform.')
    argv = sys.argv[1:]
    known_args, _ = parser.parse_known_args(argv)

    # Init NGSI-LD REST API Client
    # Set URL to Stellio API-Gateway
    #url = "http://api-gateway:8080"
    url = "http://localhost:8080"
    headers = {"Accept": "application/json"}
    context = "http://context-catalog:8080/context.jsonld"
    debug = False
    ngsi_ld_api = NGSILDAPI(url, headers=headers,
                        context=context, debug=debug)

    main(known_args, ngsi_ld_api)
