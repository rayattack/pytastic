import json
from typing import Any, Dict, Type, List, Optional
from pytastic.validators import (
    Validator, NumberValidator, StringValidator, 
    CollectionValidator, ObjectValidator, 
    UnionValidator, LiteralValidator
)

class JsonSchemaGenerator:
    """Generates JSON Schema from Pytastic Validators."""

    def __init__(self):
        self.definitions: Dict[str, Any] = {}
    
    def generate(self, validator: Validator, root_name: str = "Root") -> Dict[str, Any]:
        """
        Generates a full JSON schema object.
        """
        self.definitions = {}
        schema = self._visit(validator)
        
        if self.definitions:
            schema["$defs"] = self.definitions
            
        return schema

    def _visit(self, validator: Validator) -> Dict[str, Any]:
        schema = {}
        if isinstance(validator, NumberValidator):
            schema = self._visit_number(validator)
        elif isinstance(validator, StringValidator):
            schema = self._visit_string(validator)
        elif isinstance(validator, CollectionValidator):
            schema = self._visit_collection(validator)
        elif isinstance(validator, ObjectValidator):
            schema = self._visit_object(validator)
        elif isinstance(validator, UnionValidator):
            schema = self._visit_union(validator)
        elif isinstance(validator, LiteralValidator):
            schema = self._visit_literal(validator)
        
        # Inject metadata
        if validator.title: schema["title"] = validator.title
        if validator.description: schema["description"] = validator.description
        if validator.default is not None: schema["default"] = validator.default
        
        return schema

    def _visit_number(self, v: NumberValidator) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"type": "integer" if v.number_type is int else "number"}
        
        if v.min_val is not None: schema['minimum'] = v.min_val
        if v.max_val is not None: schema['maximum'] = v.max_val
        if v.exclusive_min_val is not None: schema['exclusiveMinimum'] = v.exclusive_min_val
        if v.exclusive_max_val is not None: schema['exclusiveMaximum'] = v.exclusive_max_val
        if v.step_val is not None: schema['multipleOf'] = v.step_val
        
        return schema

    def _visit_string(self, v: StringValidator) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"type": "string"}
        
        if v.min_len is not None: schema['minLength'] = v.min_len
        if v.max_len is not None: schema['maxLength'] = v.max_len
        if v.pattern: schema['pattern'] = str(v.pattern)
        if v.format: schema['format'] = str(v.format)
        
        return schema

    def _visit_collection(self, v: CollectionValidator) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"type": "array"}
        c = v.constraints
        
        if 'min_items' in c: schema['minItems'] = int(c['min_items'])
        if 'max_items' in c: schema['maxItems'] = int(c['max_items'])
        if c.get('unique') or c.get('unique_items'): schema['uniqueItems'] = True
        
        if isinstance(v.item_validator, list):
            # Tuple validation using 'prefixItems' (JSON Schema 2020-12+)
            schema['prefixItems'] = [self._visit(iv) for iv in v.item_validator]
            schema['minItems'] = len(v.item_validator)
            schema['maxItems'] = len(v.item_validator)
            schema['items'] = False # No extra items allowed
        elif isinstance(v.item_validator, Validator):
            schema['items'] = self._visit(v.item_validator)
            
        return schema

    def _visit_object(self, v: ObjectValidator) -> Dict[str, Any]:
        schema: Dict[str, Any] = {"type": "object", "properties": {}, "required": [], "additionalProperties": True}
        
        for name, field_validator in v.fields.items():
            schema["properties"][name] = self._visit(field_validator)
        
        schema["required"] = list(v.required_keys)
        
        c = v.constraints
        if c.get('strict') or c.get('additional_properties') is False:
             schema['additionalProperties'] = False
        
        min_p = c.get('min_properties') or c.get('min_props')
        if min_p: schema['minProperties'] = int(min_p)

        return schema

    def _visit_union(self, v: UnionValidator) -> Dict[str, Any]:
        schemas = [self._visit(sv) for sv in v.validators]
        key = "oneOf" if v.mode == "one_of" else "anyOf"
        return {key: schemas}

    def _visit_literal(self, v: LiteralValidator) -> Dict[str, Any]:
        if len(v.allowed_values) == 1 and v.allowed_values[0] is None:
             return {"type": "null"}
        return {"enum": list(v.allowed_values)}

def to_json_string(schema: Dict[str, Any]) -> str:
    return json.dumps(schema, indent=2)
