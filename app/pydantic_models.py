from pydantic import BaseModel


class RegisterRequestModel(BaseModel):
    key: str


class RegisterResponseModel(BaseModel):
    server_pubkey: str
    endpoint_address: str
    endpoint_port: int
    client_inbound_ip: str
    server_inbound_ip: str
