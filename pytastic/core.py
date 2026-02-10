from typing import Any, Type, Dict, TypeVar, Optional, Callable
from pytastic.codegen import CodegenCompiler
from pytastic.exceptions import PytasticError
from pytastic.schema import JsonSchemaGenerator, to_json_string
from pytastic.compiler import SchemaCompiler

T = TypeVar("T")

class Pytastic:
    """
    Main entry point for Pytastic validation.
    Functions as a registry and factory for validators.
    """
    def __init__(self):
        self.codegen = CodegenCompiler()
        self.compiler = SchemaCompiler()
        self._registry: Dict[str, Any] = {}
        self._attr_cache: Dict[str, Callable[[Any], Any]] = {}

    def register(self, schema: Type[T]) -> None:
        """
        Registers a schema (TypedDict) with Pytastic.
        Compiles the schema immediately using code generation.
        """
        validator = self.codegen.compile(schema)
        self._registry[schema.__name__] = validator

    def validate(self, schema: Type[T], data: Any, strip: bool = False) -> T:
        """
        Validates data against a schema using code generation.

        Args:
            strip: If True, removes fields from data not defined in the schema.
                   For best performance, define strip=True in the schema's
                   Annotated metadata instead (compiled once, always fast).
        """
        validator = self.codegen.compile(schema, strip=strip)
        return validator(data)

    def __getattr__(self, name: str) -> Callable[[Any], Any]:
        """
        Enables dynamic syntax: vx.UserSchema(data)
        """
        if name in self._attr_cache:
            return self._attr_cache[name]
            
        if name in self._registry:
            validator = self._registry[name]
            self._attr_cache[name] = validator
            return validator
        
        raise AttributeError(f"'Pytastic' object has no attribute '{name}'. Did you forget to register the schema?")

    def schema(self, schema: Type[T]) -> str:
        """
        Returns the JSON Schema definition for a model as a string.
        """
        validator = self.compiler.compile(schema)
        generator = JsonSchemaGenerator()
        json_dict = generator.generate(validator)
        return to_json_string(json_dict)
