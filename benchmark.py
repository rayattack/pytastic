import time
from typing import TypedDict, Annotated, Literal, List
import msgspec
from pydantic import BaseModel, Field, field_validator
from pytastic import Pytastic

# Test data
SAMPLE_DATA = {
    "username": "john_doe",
    "email": "john@example.com",
    "age": 30,
    "role": "admin",
    "tags": ["python", "developer", "senior"],
    "active": True
}

ITERATIONS = 100_000

# Pytastic Schema
class PytasticUser(TypedDict):
    username: Annotated[str, "min_len=3; max_len=50"]
    email: Annotated[str, "regex=^[^@]+@[^@]+\\.[^@]+$"]
    age: Annotated[int, "min=18; max=120"]
    role: Literal["admin", "user", "guest"]
    tags: Annotated[List[str], "min_items=1; max_items=10"]
    active: bool

# Pydantic Schema
class PydanticUser(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
    age: int = Field(ge=18, le=120)
    role: Literal["admin", "user", "guest"]
    tags: List[str] = Field(min_length=1, max_length=10)
    active: bool

# msgspec Schema
class MsgspecUser(msgspec.Struct):
    username: str
    email: str
    age: int
    role: Literal["admin", "user", "guest"]
    tags: List[str]
    active: bool

def benchmark_pytastic():
    vx = Pytastic()
    vx.register(PytasticUser)
    
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        vx.PytasticUser(SAMPLE_DATA)
    end = time.perf_counter()
    
    return end - start

def benchmark_pydantic():
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        PydanticUser(**SAMPLE_DATA)
    end = time.perf_counter()
    
    return end - start

def benchmark_msgspec():
    decoder = msgspec.json.Decoder(MsgspecUser)
    json_data = msgspec.json.encode(SAMPLE_DATA)
    
    start = time.perf_counter()
    for _ in range(ITERATIONS):
        decoder.decode(json_data)
    end = time.perf_counter()
    
    return end - start

if __name__ == "__main__":
    print(f"Running benchmark with {ITERATIONS:,} iterations...\n")
    
    # Warmup
    vx = Pytastic()
    vx.register(PytasticUser)
    vx.validate(PytasticUser, SAMPLE_DATA)
    PydanticUser(**SAMPLE_DATA)
    
    # Benchmarks
    pytastic_time = benchmark_pytastic()
    pydantic_time = benchmark_pydantic()
    msgspec_time = benchmark_msgspec()
    
    # Results
    print("=" * 60)
    print(f"{'Library':<15} {'Time (s)':<12} {'Ops/sec':<15} {'Relative':<10}")
    print("=" * 60)
    
    fastest = min(pytastic_time, pydantic_time, msgspec_time)
    
    results = [
        ("Pytastic", pytastic_time),
        ("Pydantic", pydantic_time),
        ("msgspec", msgspec_time)
    ]
    
    for name, duration in sorted(results, key=lambda x: x[1]):
        ops_per_sec = ITERATIONS / duration
        relative = duration / fastest
        print(f"{name:<15} {duration:<12.4f} {ops_per_sec:<15,.0f} {relative:<10.2f}x")
    
    print("=" * 60)
