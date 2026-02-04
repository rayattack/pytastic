from abc import ABC, abstractmethod
from typing import Any, List, Dict, Generic, TypeVar, Union, Set, Tuple
import re
import math
from pytastic.exceptions import ValidationError

T = TypeVar("T")

class Validator(ABC, Generic[T]):
    """Abstract base class for all validators."""
    
    @abstractmethod
    def validate(self, data: Any, path: str = "") -> T:
        pass

class AnyValidator(Validator[Any]):
    __slots__ = ()
    
    def validate(self, data: Any, path: str = "") -> Any:
        return data

class NumberValidator(Validator[Union[int, float]]):
    __slots__ = ('number_type', 'min_val', 'max_val', 'exclusive_min_val', 'exclusive_max_val', 'step_val')
    
    def __init__(self, constraints: Dict[str, Any], number_type: type = int):
        self.number_type = number_type
        self.min_val = float(constraints['min']) if 'min' in constraints else None
        self.max_val = float(constraints['max']) if 'max' in constraints else None
        self.exclusive_min_val = float(constraints['exclusive_min']) if 'exclusive_min' in constraints else None
        self.exclusive_max_val = float(constraints['exclusive_max']) if 'exclusive_max' in constraints else None
        step = constraints.get('step') or constraints.get('multiple_of')
        self.step_val = float(step) if step else None

    def validate(self, data: Any, path: str = "") -> Union[int, float]:
        if not isinstance(data, (int, float)):
            raise ValidationError(f"Expected number, got {type(data).__name__}", [{"path": path, "message": "Invalid type"}])
        
        if self.number_type is int and isinstance(data, float) and not data.is_integer():
             raise ValidationError(f"Expected integer, got float", [{"path": path, "message": "Expected integer"}])

        val = data

        if self.min_val is not None and val < self.min_val:
            raise ValidationError(f"Value {val} is less than minimum {self.min_val}", [{"path": path, "message": f"Must be >= {self.min_val}"}])
        
        if self.max_val is not None and val > self.max_val:
            raise ValidationError(f"Value {val} is greater than maximum {self.max_val}", [{"path": path, "message": f"Must be <= {self.max_val}"}])

        if self.exclusive_min_val is not None and val <= self.exclusive_min_val:
            raise ValidationError(f"Value {val} must be greater than {self.exclusive_min_val}", [{"path": path, "message": f"Must be > {self.exclusive_min_val}"}])
                
        if self.exclusive_max_val is not None and val >= self.exclusive_max_val:
            raise ValidationError(f"Value {val} must be less than {self.exclusive_max_val}", [{"path": path, "message": f"Must be < {self.exclusive_max_val}"}])

        if self.step_val is not None:
            if not math.isclose(val % self.step_val, 0, abs_tol=1e-9) and not math.isclose(val % self.step_val, self.step_val, abs_tol=1e-9):
                 raise ValidationError(f"Value {val} is not a multiple of {self.step_val}", [{"path": path, "message": f"Must be multiple of {self.step_val}"}])

        return self.number_type(val)

class StringValidator(Validator[str]):
    __slots__ = ('min_len', 'max_len', 'pattern', 'format')
    
    def __init__(self, constraints: Dict[str, Any]):
        min_l = constraints.get('min_length') or constraints.get('min_len')
        self.min_len = int(min_l) if min_l else None
        max_l = constraints.get('max_length') or constraints.get('max_len')
        self.max_len = int(max_l) if max_l else None
        self.pattern = constraints.get('regex') or constraints.get('pattern')
        self.format = constraints.get('format')

    def validate(self, data: Any, path: str = "") -> str:
        if not isinstance(data, str):
            raise ValidationError(f"Expected string, got {type(data).__name__}", [{"path": path, "message": "Invalid type"}])
        
        val = data

        if self.min_len is not None and len(val) < self.min_len:
           raise ValidationError(f"String length {len(val)} is shorter than min {self.min_len}", [{"path": path, "message": f"Length must be >= {self.min_len}"}])

        if self.max_len is not None and len(val) > self.max_len:
           raise ValidationError(f"String length {len(val)} is longer than max {self.max_len}", [{"path": path, "message": f"Length must be <= {self.max_len}"}])

        if self.pattern and isinstance(self.pattern, str) and not re.search(self.pattern, val):
            raise ValidationError(f"String does not match pattern '{self.pattern}'", [{"path": path, "message": "Pattern mismatch"}])

        if self.format == 'email':
            if '@' not in val: # Very basic check
                raise ValidationError("Invalid email format", [{"path": path, "message": "Invalid email"}])
        elif self.format == 'uuid':
            # Basic UUID pattern
            if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', val.lower()):
                 raise ValidationError("Invalid UUID format", [{"path": path, "message": "Invalid UUID"}])
        
        
        return val

class CollectionValidator(Validator[list]):
    __slots__ = ('constraints', 'item_validator')
    
    def __init__(self, constraints: Dict[str, Any], item_validator: Union[Validator, List[Validator], None] = None):
        self.constraints = constraints
        self.item_validator = item_validator # Can be a single validator (list) or list of validators (tuple)

    def validate(self, data: Any, path: str = "") -> list:
        if not isinstance(data, (list, tuple)):
             raise ValidationError(f"Expected list/tuple, got {type(data).__name__}", [{"path": path, "message": "Invalid type"}])
        
        # Min Items
        if 'min_items' in self.constraints:
            limit = int(self.constraints['min_items'])
            if len(data) < limit:
                raise ValidationError(f"List has fewer items than {limit}", [{"path": path, "message": f"Min items: {limit}"}])

        # Max Items
        if 'max_items' in self.constraints:
            limit = int(self.constraints['max_items'])
            if len(data) > limit:
                raise ValidationError(f"List has more items than {limit}", [{"path": path, "message": f"Max items: {limit}"}])

        # Unique Items
        if self.constraints.get('unique') or self.constraints.get('unique_items'):
            try:
                if len(set(data)) != len(data):
                    raise ValidationError("List items must be unique", [{"path": path, "message": "Duplicate items found"}])
            except TypeError:
                for i in range(len(data)):
                    for j in range(i + 1, len(data)):
                        if data[i] == data[j]:
                             raise ValidationError("List items must be unique", [{"path": path, "message": "Duplicate items found"}])

        validated_data = []
        
        # Tuple validation (positional)
        if isinstance(self.item_validator, list):
             if len(data) != len(self.item_validator):
                 # Strict tuple length? Python tuples usually fixed.
                 raise ValidationError(f"Expected {len(self.item_validator)} items, got {len(data)}", [{"path": path, "message": f"Expected {len(self.item_validator)} items"}])
             
             for i, (item, validator) in enumerate(zip(data, self.item_validator)):
                 validated_data.append(validator.validate(item, path=f"{path}[{i}]"))
        
        # List validation (homogeneous)
        elif isinstance(self.item_validator, Validator):
             for i, item in enumerate(data):
                 validated_data.append(self.item_validator.validate(item, path=f"{path}[{i}]"))
        else:
            validated_data = list(data)

        return validated_data

class UnionValidator(Validator[Any]):
    __slots__ = ('validators', 'mode')
    
    def __init__(self, validators: List[Validator], mode: str = "any_of"):
        self.validators = validators
        self.mode = mode # 'any_of' or 'one_of'

    def validate(self, data: Any, path: str = "") -> Any:
        valid_results = []
        errors = []

        for v in self.validators:
            try:
                valid_results.append(v.validate(data, path))
            except ValidationError as e:
                errors.append(e)
        
        if self.mode == "one_of":
            if len(valid_results) == 1:
                return valid_results[0]
            elif len(valid_results) == 0:
                 raise ValidationError("Matches none of the allowed types", [{"path": path, "message": "No match for OneOf"}])
            else:
                 raise ValidationError("Matches multiple types in OneOf", [{"path": path, "message": "Multiple matches for OneOf"}])

        # Default: any_of (return first match)
        if valid_results:
            return valid_results[0]
        
        raise ValidationError("Matches none of the allowed types", [{"path": path, "message": "No match for Union"}])

class ObjectValidator(Validator[Dict]):
    __slots__ = ('fields', 'constraints', 'required_keys')
    
    def __init__(self, fields: Dict[str, Validator], constraints: Dict[str, Any], required_keys: Set[str]):
        self.fields = fields
        self.constraints = constraints
        self.required_keys = required_keys # Keys that MUST be present

    def validate(self, data: Any, path: str = "") -> Dict:
        if not isinstance(data, dict):
            raise ValidationError(f"Expected object, got {type(data).__name__}", [{"path": path, "message": "Invalid type"}])
        
        final_data = {}
        errors = []

        # Check required keys
        missing = self.required_keys - data.keys()
        if missing:
             for k in missing:
                 errors.append({"path": f"{path}.{k}" if path else k, "message": "Field is required"})
        
        # Validate Fields
        for key, value in data.items():
            if key in self.fields:
                try:
                    final_data[key] = self.fields[key].validate(value, path=f"{path}.{key}" if path else key)
                except ValidationError as e:
                    errors.extend(e.errors)
            else:
                # Extra keys
                if self.constraints.get('additional_properties') is False or self.constraints.get('strict'):
                     errors.append({"path": f"{path}.{key}" if path else key, "message": "Extra field not allowed"})
                else:
                    final_data[key] = value

        # Min/Max Properties
        if 'min_properties' in self.constraints or 'min_props' in self.constraints:
             limit = int(self.constraints.get('min_properties') or self.constraints.get('min_props') or 0)
             if len(data) < limit:
                  errors.append({"path": path, "message": f"Too few properties (min {limit})"})

        if errors:
            raise ValidationError("Validation failed", errors)

        return final_data

class LiteralValidator(Validator[Any]):
    __slots__ = ('allowed_values',)
    
    def __init__(self, allowed_values: Tuple[Any, ...]):
        self.allowed_values = allowed_values

    def validate(self, data: Any, path: str = "") -> Any:
        if data not in self.allowed_values:
            # Format expected values for friendly error
            allowed = ", ".join(repr(v) for v in self.allowed_values)
            raise ValidationError(f"Value must be one of: {allowed}", [{"path": path, "message": f"Expected one of: {allowed}"}])
        return data
