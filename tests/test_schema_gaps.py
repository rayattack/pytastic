
from typing import TypedDict, Annotated, Optional, NotRequired
from pytastic import Pytastic, ValidationError
import json

vx = Pytastic()

class SchemaGap(TypedDict):
    opt_val: Optional[int]
    not_req: NotRequired[str]
    desc: Annotated[int, "description='My Desc'; title='My Title'; default=42"]

try:
    print("Testing Schema Generation...")
    s = vx.schema(SchemaGap)
    print(s)
    
    print("\nTesting Validation...")
    # Optional (None)
    vx.validate(SchemaGap, {"opt_val": None})
    print("Optional (None): OK")
    
    # Optional (Value)
    vx.validate(SchemaGap, {"opt_val": 10})
    print("Optional (Val): OK")
    
    # NotRequired (Missing)
    vx.validate(SchemaGap, {"opt_val": 1})
    print("NotRequired (Missing): OK")
    
    # NotRequired (Present)
    vx.validate(SchemaGap, {"opt_val": 1, "not_req": "hello"})
    print("NotRequired (Present): OK")
    
    print("ALL OK")

except Exception as e:
    print(f"FAILED: {e}")
