import logging
import os

from fastapi import FastAPI

from platform_registry.clients.ngsi_ld import NGSILDAPI
from platform_registry.legacy import loader as legacy_loader
from platform_registry.models.rest import Registration

logger = logging.getLogger(__name__)


# NGSI-LD Context Broker
BROKER_URI = os.getenv("BROKER_URI", "http://scorpio:9090")
# Context Catalog
CONTEXT_CATALOG_URI = os.getenv(
    "CONTEXT_CATALOG_URI", "http://context-catalog:8080/context.jsonld"
)

# Init NGSI-LD API Client
ngsi_ld = NGSILDAPI(url=BROKER_URI, context=CONTEXT_CATALOG_URI)

# Init FastAPI server
app = FastAPI(title="Platform Registry API", version="1.0.0")


@app.post("/platforms/")
async def register_platform(registration: Registration):
    legacy_loader(registration, ngsi_ld)
