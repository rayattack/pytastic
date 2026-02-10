from typing import Any, Type, Dict, get_origin, get_args, Union, List, Tuple, Annotated, _TypedDictMeta, Literal
from typing import get_type_hints
from pytastic.exceptions import SchemaDefinitionError
from pytastic.utils import parse_constraints, ConstraintNode, LeafConstraint, ConditionalConstraint, OrConstraint, NotConstraint
import math 
import re

try:
    from typing import NotRequired, Required
except ImportError:
    try:
        from typing_extensions import NotRequired, Required
    except ImportError:
        NotRequired = Required = object() # Fallback


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
        code_lines.append(f"def validate_{schema_name}(data, path='', context=None):")
        
        body_lines = self._generate_validator(schema, 'data', 'path', 'context', indent=1)
        code_lines.extend(body_lines)
        code_lines.append("    return data")
        
        code = '\n'.join(code_lines)
        
        # DEBUG: Print generated code to debug failures
        # print(f"--- Generated Code for {schema_name} ---\n{code}\n--------------------------------")
        
        namespace = {
            'ValidationError': __import__('pytastic.exceptions', fromlist=['ValidationError']).ValidationError,
            're': __import__('re'),
            'math': __import__('math'),
        }
        
        exec(code, namespace)
        validator_func = namespace[f'validate_{schema_name}']
        
        self._cache[schema] = validator_func
        return validator_func
    
    def _generate_validator(self, schema: Type, var_name: str, path_var: str, context_var: str, indent: int) -> List[str]:
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
            parsed = parse_constraints(constraint_str)
            
            constraints = {}
            wrappers = []
            
            if isinstance(parsed, dict):
                constraints = parsed
            else:
                for node in parsed:
                    if isinstance(node, LeafConstraint):
                        constraints[node.key] = node.value
                    else:
                        wrappers.append(node)
            
            # Generate base validation
            base_lines = []
            base_origin = get_origin(base_type)
            
            if base_type is int or base_type is float:
                base_lines = self._gen_number(var_name, path_var, base_type, constraints, indent)
            elif base_type is str:
                base_lines = self._gen_string(var_name, path_var, constraints, indent)
            elif self._is_typeddict(base_type):
                base_lines = self._gen_object(base_type, var_name, path_var, context_var, constraints, indent)
            elif base_origin is list or base_origin is List:
                inner_type = get_args(base_type)[0] if get_args(base_type) else Any
                base_lines = self._gen_list(var_name, path_var, context_var, inner_type, constraints, indent)
            elif base_origin is tuple or base_origin is Tuple:
                inner_types = get_args(base_type)
                base_lines = self._gen_tuple(var_name, path_var, context_var, inner_types, constraints, indent)
            
            lines.extend(base_lines)
            
            # Wrappers applied AFTER base type checks (AND logic)
            for wrapper in wrappers:
                lines.extend(self._gen_complex_node(wrapper, var_name, path_var, context_var, base_type, indent))
                
            return lines
        
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
                     parsed = parse_constraints(constraint_str)
                     if isinstance(parsed, dict):
                         constraints.update(parsed)
            return self._gen_object(schema, var_name, path_var, context_var, constraints, indent)
        
        if origin is list or origin is List:
            inner_type = args[0] if args else Any
            return self._gen_list(var_name, path_var, context_var, inner_type, {}, indent)
        
        if origin is tuple or origin is Tuple:
            return self._gen_tuple(var_name, path_var, context_var, args, {}, indent)
        
        if origin is Union:
            return self._gen_union(var_name, path_var, context_var, args, indent)
        
        if origin is Literal:
            return self._gen_literal(var_name, path_var, args, indent)
        
        if schema is int or schema is float:
            return self._gen_number(var_name, path_var, schema, {}, indent)
        
        if schema is str:
            return self._gen_string(var_name, path_var, {}, indent)
        
        if schema is bool:
            lines.append(f"{ind}# bool validation (passthrough)")
            
        if schema is type(None):
            lines.append(f"{ind}if {var_name} is not None:")
            lines.append(f"{ind}    raise ValidationError(f'Expected None at {{{path_var}}}', [{{'path': {path_var}, 'message': 'Must be None'}}])")

        if origin is NotRequired or origin is Required:
            return self._generate_validator(args[0], var_name, path_var, context_var, indent)
        
        return lines

    def _gen_complex_node(self, node: ConstraintNode, var: str, path: str, context: str, base_type: Type, indent: int) -> List[str]:
        ind = '    ' * indent
        lines = []
        
        if isinstance(node, ConditionalConstraint):
            lines.append(f"{ind}# Conditional Check: {node.condition}")
            key, val = node.condition.split('==')
            key = key.strip()
            val = val.strip()
            
            lines.append(f"{ind}_cond_match = False")
            lines.append(f"{ind}if isinstance({context}, dict):")
            lines.append(f"{ind}    _cond_ctx_val = {context}.get('{key}')")
            lines.append(f"{ind}    if str(_cond_ctx_val) == '{val}':") 
            lines.append(f"{ind}        _cond_match = True")
            
            lines.append(f"{ind}if _cond_match:")
            if isinstance(node.constraint, LeafConstraint):
                 c = {node.constraint.key: node.constraint.value}
                 if base_type is int or base_type is float:
                     lines.extend(self._gen_number(var, path, base_type, c, indent + 1))
                 elif base_type is str:
                     lines.extend(self._gen_string(var, path, c, indent + 1))
            else:
                 lines.extend(self._gen_complex_node(node.constraint, var, path, context, base_type, indent + 1))
                 
        elif isinstance(node, NotConstraint):
            lines.append(f"{ind}# NOT Check")
            lines.append(f"{ind}try:")
            if isinstance(node.constraint, LeafConstraint):
                 c = {node.constraint.key: node.constraint.value}
                 if base_type is int or base_type is float:
                     lines.extend(self._gen_number(var, path, base_type, c, indent + 1))
                 elif base_type is str:
                     lines.extend(self._gen_string(var, path, c, indent + 1))
            else:
                 lines.extend(self._gen_complex_node(node.constraint, var, path, context, base_type, indent + 1))
            lines.append(f"{ind}except ValidationError:")
            lines.append(f"{ind}    pass # Expected failure for NOT")
            lines.append(f"{ind}else:")
            lines.append(f"{ind}    raise ValidationError(f'NOT constraint failed at {{{path}}}', [{{'path': {path}, 'message': 'NOT check failed'}}])")

        elif isinstance(node, OrConstraint):
            lines.append(f"{ind}# OR Check")
            lines.append(f"{ind}_or_errors = []")
            lines.append(f"{ind}_or_success = False")
            
            for sub_node in node.constraints:
                lines.append(f"{ind}if not _or_success:")
                lines.append(f"{ind}    try:")
                if isinstance(sub_node, LeafConstraint):
                     c = {sub_node.key: sub_node.value}
                     if base_type is int or base_type is float:
                         lines.extend(self._gen_number(var, path, base_type, c, indent + 2))
                     elif base_type is str:
                         lines.extend(self._gen_string(var, path, c, indent + 2))
                else:
                     lines.extend(self._gen_complex_node(sub_node, var, path, context, base_type, indent + 2))
                lines.append(f"{ind}        _or_success = True")
                lines.append(f"{ind}    except ValidationError as e:")
                lines.append(f"{ind}        _or_errors.append(e)")
            
            lines.append(f"{ind}if not _or_success:")
            lines.append(f"{ind}    raise ValidationError(f'OR constraint failed at {{{path}}}', [{{'path': {path}, 'message': 'OR check failed'}}])")
            
        return lines

    def _gen_number(self, var: str, path: str, num_type: type, constraints: Dict, indent: int) -> List[str]:
        """Generate number validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}if not isinstance({var}, (int, float)):")
        lines.append(f"{ind}    raise ValidationError(f'Expected number at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        if num_type is int:
            lines.append(f"{ind}if isinstance({var}, float) and not {var}.is_integer():")
            lines.append(f"{ind}    raise ValidationError(f'Expected integer at {{{path}}}', [{{'path': {path}, 'message': 'Expected integer'}}])")
        
        if 'min' in constraints:
            min_val = float(constraints['min'])
            lines.append(f"{ind}if {var} < {min_val}:")
            lines.append(f"{ind}    raise ValidationError(f'Value {{{var}}} < {min_val} at {{{path}}}', [{{'path': {path}, 'message': 'Must be >= {min_val}'}}])")
        
        if 'max' in constraints:
            max_val = float(constraints['max'])
            lines.append(f"{ind}if {var} > {max_val}:")
            lines.append(f"{ind}    raise ValidationError(f'Value {{{var}}} > {max_val} at {{{path}}}', [{{'path': {path}, 'message': 'Must be <= {max_val}'}}])")

        if 'exclusive_min' in constraints:
            ex_min = float(constraints['exclusive_min'])
            lines.append(f"{ind}if {var} <= {ex_min}:")
            lines.append(f"{ind}    raise ValidationError(f'Value {{{var}}} <= {ex_min} at {{{path}}}', [{{'path': {path}, 'message': 'Must be > {ex_min}'}}])")

        if 'exclusive_max' in constraints:
            ex_max = float(constraints['exclusive_max'])
            lines.append(f"{ind}if {var} >= {ex_max}:")
            lines.append(f"{ind}    raise ValidationError(f'Value {{{var}}} >= {ex_max} at {{{path}}}', [{{'path': {path}, 'message': 'Must be < {ex_max}'}}])")

        step = constraints.get('step') or constraints.get('multiple_of')
        if step:
            step_val = float(step)
            lines.append(f"{ind}if not math.isclose({var} % {step_val}, 0, abs_tol=1e-9) and not math.isclose({var} % {step_val}, {step_val}, abs_tol=1e-9):")
            lines.append(f"{ind}    raise ValidationError(f'Value {{{var}}} is not a multiple of {step_val} at {{{path}}}', [{{'path': {path}, 'message': 'Must be multiple of {step_val}'}}])")

        return lines
    
    def _gen_string(self, var: str, path: str, constraints: Dict, indent: int) -> List[str]:
        """Generate string validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}if not isinstance({var}, str):")
        lines.append(f"{ind}    raise ValidationError(f'Expected string at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        min_len = constraints.get('min_length') or constraints.get('min_len')
        if min_len:
            min_len = int(min_len)
            lines.append(f"{ind}if len({var}) < {min_len}:")
            lines.append(f"{ind}    raise ValidationError(f'String too short at {{{path}}}', [{{'path': {path}, 'message': 'Min length {min_len}'}}])")
        
        max_len = constraints.get('max_length') or constraints.get('max_len')
        if max_len:
            max_len = int(max_len)
            lines.append(f"{ind}if len({var}) > {max_len}:")
            lines.append(f"{ind}    raise ValidationError(f'String too long at {{{path}}}', [{{'path': {path}, 'message': 'Max length {max_len}'}}])")
        
        pattern = constraints.get('regex') or constraints.get('pattern')
        if pattern:
            escaped_pattern = pattern.replace("'", "\\'")
            lines.append(f"{ind}if not re.search(r'{escaped_pattern}', {var}):")
            lines.append(f"{ind}    raise ValidationError(f'Pattern mismatch at {{{path}}}', [{{'path': {path}, 'message': 'Pattern mismatch'}}])")
        
        fmt = constraints.get('format')
        if fmt:
            if fmt == 'email':
                lines.append(f"{ind}if '@' not in {var}:")
                lines.append(f"{ind}    raise ValidationError('Invalid email format', [{{'path': {path}, 'message': 'Invalid email'}}])")
            elif fmt == 'uuid':
                uuid_pat = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                lines.append(f"{ind}if not re.match(r'{uuid_pat}', {var}.lower()):")
                lines.append(f"{ind}    raise ValidationError('Invalid UUID format', [{{'path': {path}, 'message': 'Invalid UUID'}}])")
            elif fmt == 'ipv4':
                lines.append(f"{ind}parts = {var}.split('.')")
                lines.append(f"{ind}if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):")
                lines.append(f"{ind}    raise ValidationError('Invalid IPv4 format', [{{'path': {path}, 'message': 'Invalid IPv4'}}])")
            elif fmt == 'date-time':
                 lines.append(f"{ind}if not re.match(r'^\\d{{4}}-\\d{{2}}-\\d{{2}}T\\d{{2}}:\\d{{2}}:\\d{{2}}', {var}):")
                 lines.append(f"{ind}    raise ValidationError('Invalid date-time format', [{{'path': {path}, 'message': 'Invalid date-time'}}])")
            elif fmt == 'uri':
                 lines.append(f"{ind}if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', {var}):")
                 lines.append(f"{ind}    raise ValidationError('Invalid URI format', [{{'path': {path}, 'message': 'Invalid URI'}}])")

        return lines
    
    def _gen_object(self, td_cls: Type, var: str, path: str, context: str, constraints: Dict, indent: int) -> List[str]:
        """Generate object/TypedDict validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}if not isinstance({var}, dict):")
        lines.append(f"{ind}    raise ValidationError(f'Expected dict at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        type_hints = get_type_hints(td_cls, include_extras=True)
        is_total = getattr(td_cls, '__total__', True)
        required_keys = getattr(td_cls, '__required_keys__', set(type_hints.keys()) if is_total else set())
        
        # We need to pass 'var' (the current dict) as 'context' to children
        child_context = var
        
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
            # Pass child_context (var) to sub-generators
            field_lines = self._generate_validator(field_type, field_var, field_path, child_context, indent)
            lines.extend(field_lines)
            
            if not is_required:
                indent -= 1
                ind = '    ' * indent
        
        # Additional Properties Check
        if constraints.get('strict') or constraints.get('additional_properties') is False:
             lines.append(f"{ind}known_keys = set({repr(list(type_hints.keys()))}) - {{'_'}}")
             lines.append(f"{ind}extra_keys = set({var}.keys()) - known_keys")
             lines.append(f"{ind}if extra_keys:")
             lines.append(f"{ind}    raise ValidationError(f'Extra fields not allowed at {{{path}}}: {{extra_keys}}', [{{'path': {path}, 'message': 'Extra fields not allowed'}}])")

        # Min Properties
        min_props = constraints.get('min_properties') or constraints.get('min_props')
        if min_props:
             min_props_val = int(min_props)
             lines.append(f"{ind}if len({var}) < {min_props_val}:")
             lines.append(f"{ind}    raise ValidationError(f'Too few properties at {{{path}}}', [{{'path': {path}, 'message': 'Min properties {min_props_val}'}}])")

        return lines
    
    def _gen_list(self, var: str, path: str, context: str, item_type: Type, constraints: Dict, indent: int) -> List[str]:
        """Generate list validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}if not isinstance({var}, list):")
        lines.append(f"{ind}    raise ValidationError(f'Expected list at {{{path}}}', [{{'path': {path}, 'message': 'Invalid type'}}])")
        
        min_items = constraints.get('min_items')
        if min_items:
            min_items_val = int(min_items)
            lines.append(f"{ind}if len({var}) < {min_items_val}:")
            lines.append(f"{ind}    raise ValidationError(f'Too few items at {{{path}}}', [{{'path': {path}, 'message': 'Min {min_items_val} items'}}])")
        
        max_items = constraints.get('max_items')
        if max_items:
            max_items_val = int(max_items)
            lines.append(f"{ind}if len({var}) > {max_items_val}:")
            lines.append(f"{ind}    raise ValidationError(f'Too many items at {{{path}}}', [{{'path': {path}, 'message': 'Max {max_items_val} items'}}])")
        
        if constraints.get('unique'):
            lines.append(f"{ind}if len({var}) != len(set({var})):")
            lines.append(f"{ind}    raise ValidationError(f'Duplicate items found at {{{path}}}', [{{'path': {path}, 'message': 'Duplicate items found'}}])")
        
        idx_var = f"_idx_{indent}"
        item_var = f"_item_{indent}"
        
        lines.append(f"{ind}for {idx_var}, {item_var} in enumerate({var}):")
        item_path = f"{path} + f'[{{{idx_var}}}]'"
        # Let's pass 'context' variable (which is parent of list)
        item_lines = self._generate_validator(item_type, item_var, item_path, context, indent + 1)
        lines.extend(item_lines)
        
        return lines
    
    def _gen_union(self, var: str, path: str, context: str, types: Tuple, indent: int) -> List[str]:
        """Generate union validation code."""
        ind = '    ' * indent
        lines = []
        
        lines.append(f"{ind}_union_match = False")
        lines.append(f"{ind}_union_errors = []")
        
        for i, union_type in enumerate(types):
            lines.append(f"{ind}if not _union_match:")
            lines.append(f"{ind}    try:")
            type_lines = self._generate_validator(union_type, var, path, context, indent + 2)
            lines.extend(type_lines)
            lines.append(f"{ind}        _union_match = True")
            lines.append(f"{ind}    except ValidationError as _e:")
            lines.append(f"{ind}        _union_errors.append(_e)")
            
        lines.append(f"{ind}if not _union_match:")
        lines.append(f"{ind}    raise ValidationError(f'No union match at {{{path}}}', [{{'path': {path}, 'message': 'No match'}}])")
        
        return lines
    
    def _gen_tuple(self, var: str, path: str, context: str, item_types: Tuple[Type, ...], constraints: Dict, indent: int) -> List[str]:
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
            
            item_lines = self._generate_validator(item_type, temp_var, item_path, context, indent)
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
