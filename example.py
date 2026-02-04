from typing import TypedDict, Annotated, Union, Literal, NotRequired, Any

# --- Reusable Components (equivalent to $defs) ---

class GeoLocation(TypedDict):
    # 'type': 'number', 'minimum': -90, 'maximum': 90
    lat: Annotated[float, "min=-90; max=90"]
    # 'type': 'number', 'minimum': -180, 'maximum': 180
    lng: Annotated[float, "min=-180; max=180"]

class ResourceTag(TypedDict):
    key: Annotated[str, "min_len=1; regex=^[a-zA-Z0-9_-]+$"]
    value: str

# --- Main Schema ---

class ClusterConfig(TypedDict):
    # 1. CONST & ENUMS ('const', 'enum')
    # The literal value enforces an exact match
    api_version: Literal["v1"] 
    environment: Literal["production", "staging", "dev"]

    # 2. STRING CONSTRAINTS ('pattern', 'format', 'minLength')
    cluster_id: Annotated[str, "regex=^cl-[a-z0-9]{8}$; format=uuid"]
    description: Annotated[str, "min_len=10; max_len=500"]
    
    # 3. NUMERIC CONSTRAINTS ('multipleOf', 'exclusiveMinimum')
    # Using NotRequired handles the 'required' array logic implicitly
    replica_count: NotRequired[Annotated[int, "min=1; max=100"]]
    cpu_limit: Annotated[float, "exclusive_min=0.0; step=0.5"]

    # 4. ARRAY CONSTRAINTS ('minItems', 'uniqueItems', 'prefixItems')
    # A list of strings with specific constraints
    zones: Annotated[list[str], "min_items=3; unique"]
    
    # Tuple validation (JSON Schema 'prefixItems' - ordered validation)
    # First item must be int, second must be string
    maintenance_window: tuple[int, str] 

    # 5. NESTED OBJECTS & REFERENCES ('$ref')
    primary_location: GeoLocation
    
    # List of objects
    tags: Annotated[list[ResourceTag], "max_items=50"]

    # 6. LOGICAL COMPOSITION ('oneOf', 'anyOf')
    # Union by itself acts like 'anyOf' (matches the first valid one).
    # Adding "one_of" flag enforces strict 'oneOf' (matches exactly one, fails if 2 match).
    network_config: Annotated[
        Union['VPCConfig', 'LegacyNetConfig'], 
        "one_of"
    ]

    # 7. GENERIC / DYNAMIC TYPES ('type': ['string', 'integer'])
    # Can allow multiple scalar types
    custom_metadata: Union[str, int, bool]

    # 8. OBJECT META-CONSTRAINTS
    # The special '_' key holds schema-level rules
    # strict: equivalent to additionalProperties: false
    # min_props: equivalent to minProperties
    # dependencies: if 'secondary_location' is present, 'primary_location' is required
    _: Annotated[None, "additional_properties=false; min_props=2; dependencies=secondary_location:primary_location"]

# --- Definitions for the Union Example above ---

class VPCConfig(TypedDict):
    vpc_id: str
    cidr: Annotated[str, "format=ipv4"]

class LegacyNetConfig(TypedDict):
    classic_link: bool
    vlan_id: Annotated[int, "min=1; max=4095"]

# --- Logical 'allOf' (Intersection) ---

class BaseUser(TypedDict):
    id: str

class AuditFields(TypedDict):
    created_at: Annotated[str, "format=datetime"]

# Python inheritance handles JSON Schema 'allOf' naturally
# This creates a schema requiring properties from BOTH BaseUser AND AuditFields
class AdminUser(BaseUser, AuditFields):
    role: Literal["admin", "superadmin"]
