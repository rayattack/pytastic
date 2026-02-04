from typing import Any, Type, Dict, get_origin, get_args, Union, List, Tuple, Annotated, _TypedDictMeta, Literal
from typing import get_type_hints
from pytastic.exceptions import SchemaDefinitionError
from pytastic.utils import parse_constraints


class CodegenCompiler:
    """Generates optimized Python validation functions from type schemas."""
    def __init__(self):
        self._cache: Dict[Type, Any] = {}
        self._counter = 0
    
    def compile(self, schema: Type) -> Any:
        """Compiles a schema into a fast validation function."""
        if schema in self._cache:
            return self._cache[schema]
        
        schema_name = getattr(schema, '__name__', f'Schema{self._counter}')
        self._counter += 1
        
        code_lines = []
        code_lines.append(f"def validate_{schema_name}(data, path=''):")
        
        body_lines = self._generate_validator(schema, 'data', 'path', indent=1)
        code_lines.extend(body_lines)
        code_lines.append("    return data")
        
        code = '\n'.join(code_lines)
        
        namespace = {
            'ValidationError': __import__('pytastic.exceptions', fromlist=['ValidationError']).ValidationError,
            're': __import__('re'),
            'math': __import__('math'),
        }
        
        exec(code, namespace)
        validator_func = namespace[f'validate_{schema_name}']
        
        self._cache[schema] = validator_func
        return validator_func
    
    def _generate_validator(self, schema: Type, var_name: str, path_var: str, indent: int) -> List[str]:
        """Generate validation code for a schema type."""
        origin = get_origin(schema)
        args = get_args(schema)
        ind = '    ' * indent
        lines = []
        
        if origin is Annotated:
            base_type = args[0]
            constraint_str = ''
            for arg in args[1:]:
                if isinstance(arg, str):
                    constraint_str += arg + ';'
            constraints = parse_constraints(constraint_str)
            
            base_origin = get_origin(base_type)
            
            if base_type is int or base_type is float:
                return self._gen_number(var_name, path_var, base_type, constraints, indent)
            elif base_type is str:
                return self._gen_string(var_name, path_var, constraints, indent)
            elif self._is_typeddict(base_type):
                return self._gen_object(base_type, var_name, path_var, constraints, indent)
            elif base_origin is list or base_origin is List:
                inner_type = get_args(base_type)[0] if get_args(base_type) else Any
                return self._gen_list(var_name, path_var, inner_type, constraints, indent)
            elif base_origin is tuple or base_origin is Tuple:
                inner_types = get_args(base_type)
                return self._gen_tuple(var_name, path_var, inner_types, constraints, indent)
        
        if self._is_typeddict(schema):
            constraints = {}
            # Handle metadata from `_: Annotated[...]` pattern
            if hasattr(schema, '__annotations__') and '_' in schema.__annotations__:
                 meta_annotation = schema.__annotations__.get('_', None)
                 if meta_annotation and get_origin(meta_annotation) is Annotated:
                     meta_args = get_args(meta_annotation)
                     constraint_str = ""
                     for arg in meta_args[1:]:
                        if isinstance(arg, str):
                            constraint_str += arg + ";"
                     meta_constraints = parse_constraints(constraint_str)
                     constraints.update(meta_constraints)
            return self._gen_object(schema, var_name, path_var, constraints, indent)
        
        if origin is list or origin is List:
            inner_type = args[0] if args else Any
            return self._gen_list(var_name, path_var, inner_type, {}, indent)
        
        if origin is tuple or origin is Tuple:
            return self._gen_tuple(var_name, path_var, args, {}, indent)
        
        if origin is Union:
            return self._gen_union(var_name, path_var, args, indent)
        
        if origin is Literal:
            return self._gen_literal(var_name, path_var, args, indent)
        
        if schema is int or schema is float:
            return self._gen_number(var_name, path_var, schema, {}, indent)
        
        if schema is str:
            return self._gen_string(var_name, path_var, {}, indent)
        
        if schema is bool:
            lines.append(f"{ind}# bool validation (passthrough)")
        
        return lines
    
    def _gen_number(self, var: str, path: str, num_type: type, constraints: Dict, indent: int) -> List[str]:
        """Generate number validation code."""
        ind = '    ' * indent
        lines = []
        
        type_name = 'int' if num_type is int else 'float'
        lines.append(f"{ind}if not isinstance({var}, (int, float)):")
        lines.append(f"{ind}    raise ValidationError(f'Expected number at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        if num_type is int:
            lines.append(f"{ind}if isinstance({var}, float) and not {var}.is_integer():")
            lines.append(f"{ind}    raise ValidationError(f'Expected integer at {{{path}}}', [{{'path': {path}, 'message': 'Expected integer'}}])")
        
        if 'min' in constraints:
            min_val = constraints['min']
            lines.append(f"{ind}if {var} < {min_val}:")
            lines.append(f"{ind}    raise ValidationError(f'Value {{{var}}} < {min_val} at {{{path}}}', [{{'path': {path}, 'message': 'Must be >= {min_val}'}}])")
        
        if 'max' in constraints:
            max_val = constraints['max']
            lines.append(f"{ind}if {var} > {max_val}:")
            lines.append(f"{ind}    raise ValidationError(f'Value {{{var}}} > {max_val} at {{{path}}}', [{{'path': {path}, 'message': 'Must be <= {max_val}'}}])")
        
        return lines
    
    def _gen_string(self, var: str, path: str, constraints: Dict, indent: int) -> List[str]:
        """Generate string validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}if not isinstance({var}, str):")
        lines.append(f"{ind}    raise ValidationError(f'Expected string at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        min_len = constraints.get('min_length') or constraints.get('min_len')
        if min_len:
            lines.append(f"{ind}if len({var}) < {min_len}:")
            lines.append(f"{ind}    raise ValidationError(f'String too short at {{{path}}}', [{{'path': {path}, 'message': 'Min length {min_len}'}}])")
        
        max_len = constraints.get('max_length') or constraints.get('max_len')
        if max_len:
            lines.append(f"{ind}if len({var}) > {max_len}:")
            lines.append(f"{ind}    raise ValidationError(f'String too long at {{{path}}}', [{{'path': {path}, 'message': 'Max length {max_len}'}}])")
        
        pattern = constraints.get('regex') or constraints.get('pattern')
        if pattern:
            escaped_pattern = pattern.replace("'", "\\'")
            lines.append(f"{ind}if not re.search(r'{escaped_pattern}', {var}):")
            lines.append(f"{ind}    raise ValidationError(f'Pattern mismatch at {{{path}}}', [{{'path': {path}, 'message': 'Pattern mismatch'}}])")
        
        return lines
    
    def _gen_object(self, td_cls: Type, var: str, path: str, constraints: Dict, indent: int) -> List[str]:
        """Generate object/TypedDict validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}if not isinstance({var}, dict):")
        lines.append(f"{ind}    raise ValidationError(f'Expected dict at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        type_hints = get_type_hints(td_cls, include_extras=True)
        is_total = getattr(td_cls, '__total__', True)
        required_keys = getattr(td_cls, '__required_keys__', set(type_hints.keys()) if is_total else set())
        
        for key, field_type in type_hints.items():
            if key == '_':
                continue
            
            field_var = f"{var}__{key}"
            is_required = key in required_keys
            
            lines.append(f"{ind}{field_var} = {var}.get('{key}')")
            
            if is_required:
                lines.append(f"{ind}if {field_var} is None:")
                lines.append(f"{ind}    raise ValidationError(f'Missing field {key} at {{{path}}}', [{{'path': {path} + '.{key}', 'message': 'Required'}}])")
            else:
                lines.append(f"{ind}if {field_var} is not None:")
                indent += 1
                ind = '    ' * indent
            
            field_path = f"{path} + '.{key}'" if path != "''" else f"'{key}'"
            field_lines = self._generate_validator(field_type, field_var, field_path, indent)
            lines.extend(field_lines)
            
            if not is_required:
                indent -= 1
        
        # Additional Properties Check
        if constraints.get('strict') or constraints.get('additional_properties') is False:
             lines.append(f"{ind}known_keys = set({repr(list(type_hints.keys()))}) - {{'_'}}")
             lines.append(f"{ind}extra_keys = set({var}.keys()) - known_keys")
             lines.append(f"{ind}if extra_keys:")
             lines.append(f"{ind}    raise ValidationError(f'Extra fields not allowed at {{{path}}}: {{extra_keys}}', [{{'path': {path}, 'message': 'Extra fields not allowed'}}])")

        # Min Properties
        min_props = constraints.get('min_properties') or constraints.get('min_props')
        if min_props:
             lines.append(f"{ind}if len({var}) < {min_props}:")
             lines.append(f"{ind}    raise ValidationError(f'Too few properties at {{{path}}}', [{{'path': {path}, 'message': 'Min properties {min_props}'}}])")

        return lines
    
    def _gen_list(self, var: str, path: str, item_type: Type, constraints: Dict, indent: int) -> List[str]:
        """Generate list validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}if not isinstance({var}, list):")
        lines.append(f"{ind}    raise ValidationError(f'Expected list at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        min_items = constraints.get('min_items')
        if min_items:
            lines.append(f"{ind}if len({var}) < {min_items}:")
            lines.append(f"{ind}    raise ValidationError(f'Too few items at {{{path}}}', [{{'path': {path}, 'message': 'Min {min_items} items'}}])")
        
        max_items = constraints.get('max_items')
        if max_items:
            lines.append(f"{ind}if len({var}) > {max_items}:")
            lines.append(f"{ind}    raise ValidationError(f'Too many items at {{{path}}}', [{{'path': {path}, 'message': 'Max {max_items} items'}}])")
        
        if constraints.get('unique'):
            lines.append(f"{ind}if len({var}) != len(set({var})):")
            lines.append(f"{ind}    raise ValidationError(f'Duplicate items found at {{{path}}}', [{{'path': {path}, 'message': 'Duplicate items found'}}])")
        
        lines.append(f"{ind}for _idx, _item in enumerate({var}):")
        item_path = f"{path} + f'[{{_idx}}]'"
        item_lines = self._generate_validator(item_type, '_item', item_path, indent + 1)
        lines.extend(item_lines)
        
        return lines
    
    def _gen_union(self, var: str, path: str, types: Tuple, indent: int) -> List[str]:
        """Generate union validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}_union_errors = []")
        for i, union_type in enumerate(types):
            lines.append(f"{ind}try:")
            type_lines = self._generate_validator(union_type, var, path, indent + 1)
            lines.extend(type_lines)
            if i < len(types) - 1:
                lines.append(f"{ind}except ValidationError as _e:")
                lines.append(f"{ind}    _union_errors.append(_e)")
            else:
                lines.append(f"{ind}except ValidationError:")
                lines.append(f"{ind}    raise ValidationError(f'No union match at {{{path}}}', [{{'path': {path}, 'message': 'No match'}}])")
        
        return lines
    
    def _gen_tuple(self, var: str, path: str, item_types: Tuple[Type, ...], constraints: Dict, indent: int) -> List[str]:
        """Generate tuple validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}if not isinstance({var}, (list, tuple)):")
        lines.append(f"{ind}    raise ValidationError(f'Expected tuple at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        expected_len = len(item_types)
        lines.append(f"{ind}if len({var}) != {expected_len}:")
        lines.append(f"{ind}    raise ValidationError(f'Expected {expected_len} items at {{{path}}}', [{{'path': {path}, 'message': 'Expected {expected_len} items'}}])")
        
        for i, item_type in enumerate(item_types):
            item_path = f"{path} + f'[{i}]'"
            # Tuple items are accessed by index
            # We need to assign to a temp var to be safe for recursive validation
            temp_var = f"_tuple_item_{indent}_{i}"
            lines.append(f"{ind}{temp_var} = {var}[{i}]")
            
            item_lines = self._generate_validator(item_type, temp_var, item_path, indent)
            lines.extend(item_lines)
            
        return lines

    def _gen_literal(self, var: str, path: str, values: Tuple, indent: int) -> List[str]:
        """Generate literal validation code."""
        ind = '    ' * indent
        lines = []
        
        allowed = list(values)
        lines.append(f"{ind}_allowed = {repr(allowed)}")
        lines.append(f"{ind}if {var} not in _allowed:")
        lines.append(f"{ind}    raise ValidationError(f'Invalid literal value at {{{path}}}', [{{'path': {path}, 'message': 'Must be one of ' + str(_allowed)}}])")
        
        return lines
    
    def _is_typeddict(self, t: Type) -> bool:
        """Check if type is a TypedDict."""
        return isinstance(t, _TypedDictMeta) or (isinstance(t, type) and issubclass(t, dict) and hasattr(t, '__annotations__'))
