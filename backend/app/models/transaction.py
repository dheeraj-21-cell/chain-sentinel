from typing import List, Optional
from pydantic import BaseModel, Field


class NormalizedTransaction(BaseModel):
    """Canonical model for a normalized Bitcoin transaction or P2P network observation record."""
    dataset_id: str = Field(..., description="Unique dataset identifier to prevent cross-dataset contamination")
    timestamp: Optional[str] = Field(None, description="Normalized UTC ISO-8601 timestamp string")
    src_ip: Optional[str] = Field(None, description="Validated source IPv4/IPv6 address")
    dst_ip: Optional[str] = Field(None, description="Validated destination IPv4/IPv6 address")
    src_port: Optional[int] = Field(None, description="Source port (1..65535)")
    dst_port: Optional[int] = Field(None, description="Destination port (1..65535)")
    txid: Optional[str] = Field(None, description="Bitcoin transaction hash (txid)")
    input_addresses: List[str] = Field(default_factory=list, description="List of source input addresses")
    output_addresses: List[str] = Field(default_factory=list, description="List of destination output addresses")
    input_amounts: List[float] = Field(default_factory=list, description="List of input amounts in BTC")
    output_amounts: List[float] = Field(default_factory=list, description="List of output amounts in BTC")
    fee: Optional[float] = Field(None, description="Transaction fee in BTC")
    script_type: Optional[str] = Field(None, description="Observed script type (e.g., p2pkh, p2sh, p2wpkh, p2tr)")
    geo_country: Optional[str] = Field(None, description="Observed/provided country code or name")
    asn: Optional[int] = Field(None, description="Autonomous System Number")
