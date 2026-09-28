from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class VolumeStats(BaseModel):
    total_input_btc: float = Field(0.0, description="Sum of all input amounts in BTC")
    total_output_btc: float = Field(0.0, description="Sum of all output amounts in BTC")
    avg_amount: Optional[float] = Field(None, description="Average output amount in BTC where available")
    min_amount: Optional[float] = Field(None, description="Minimum output amount in BTC where available")
    max_amount: Optional[float] = Field(None, description="Maximum output amount in BTC where available")


class FeeStats(BaseModel):
    total_fee_btc: float = Field(0.0, description="Sum of recorded transaction fees")
    avg_fee_btc: Optional[float] = Field(None, description="Average fee in BTC where available")
    min_fee_btc: Optional[float] = Field(None, description="Minimum fee in BTC where available")
    max_fee_btc: Optional[float] = Field(None, description="Maximum fee in BTC where available")
    fee_recorded_count: int = Field(0, description="Number of transactions with fees recorded")


class DatasetAnalyticsSummary(BaseModel):
    dataset_id: str
    total_records: int
    unique_txids: int
    unique_wallets: int
    unique_ips: int
    volume_stats: VolumeStats
    fee_stats: FeeStats
    earliest_timestamp: Optional[str] = None
    latest_timestamp: Optional[str] = None
    script_types: Dict[str, int] = Field(default_factory=dict)
    countries: Dict[str, int] = Field(default_factory=dict)
    asns: Dict[str, int] = Field(default_factory=dict)
    ports: Dict[str, int] = Field(default_factory=dict)


class WalletActivity(BaseModel):
    address: str
    tx_count: int
    input_count: int
    output_count: int
    total_sent: float
    total_received: float
    net_flow: float


class TimeSeriesBucket(BaseModel):
    timestamp_bucket: str
    tx_count: int
    volume: float


class NetworkObservation(BaseModel):
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    geo_country: Optional[str] = None
    asn: Optional[int] = None
    observation_count: int


class CorrelationRecord(BaseModel):
    txid: Optional[str] = None
    timestamp: Optional[str] = None
    input_addresses: List[str] = Field(default_factory=list)
    output_addresses: List[str] = Field(default_factory=list)
    input_amounts: List[float] = Field(default_factory=list)
    output_amounts: List[float] = Field(default_factory=list)
    fee: Optional[float] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    geo_country: Optional[str] = None
    asn: Optional[int] = None
    script_type: Optional[str] = None
