from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class APIConfig:
    active: bool
    name: str
    url: str
    method: str = "GET"
    token: str = ""
    body: Optional[Dict[str, Any]] = field(default_factory=dict)
    body_raw: str = ""
    headers: Dict[str, str] = field(default_factory=dict)

@dataclass
class DynamicData:
    key: str
    value: str

@dataclass
class APIResult:
    api: APIConfig
    status: Optional[int]
    text: str
    error: Optional[str] = None
