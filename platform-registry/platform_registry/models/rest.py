import ipaddress
from typing import Optional

from pydantic import BaseModel, SecretStr


class Credentials(BaseModel):
    username: str
    password: SecretStr

class ProtocolConfig(BaseModel):
    address: ipaddress.IPv4Address
    port: int
    credentials: Credentials

class Registration(BaseModel):
    platform_id: str
    platform_name: str
    vendor: str
    software_version: str
    software_flavor: Optional[str]
    os_version: Optional[str]
    os_type: Optional[str]
    gNMI: Optional[ProtocolConfig]
    netconf: Optional[ProtocolConfig]
