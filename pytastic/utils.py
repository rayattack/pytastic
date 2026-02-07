from typing import Dict, Any, Union, List, Optional
import re
from dataclasses import dataclass

@dataclass
class ParseNode:
    pass

@dataclass
class LeafConstraint(ParseNode):
    key: str
    value: Any

@dataclass
class ConditionalConstraint(ParseNode):
    condition: str  # e.g. "payment_type==credit"
    constraint: 'ConstraintNode'

@dataclass
class OrConstraint(ParseNode):
    constraints: List['ConstraintNode']

@dataclass
class NotConstraint(ParseNode):
    constraint: 'ConstraintNode'

ConstraintNode = Union[LeafConstraint, ConditionalConstraint, OrConstraint, NotConstraint, Dict[str, Any]]

def parse_constraints(annotation_str: str) -> Union[Dict[str, Any], List[ConstraintNode]]:
    """
    Parses a constraint string into a structure.
    Returns a dict for simple cases (backwards compatibility) or a list of ConstraintNodes for complex cases.
    """
    if not annotation_str:
        return {}
    
    # Check for complex syntax characters
    if any(c in annotation_str for c in "?!|") or "==" in annotation_str:
        return _parse_complex(annotation_str)

    # Fallback to simple parser for standard cases
    return _parse_simple(annotation_str)

def _parse_simple(text: str) -> Dict[str, Any]:
    constraints = {}
    pattern = r"([^=;\s]+)\s*=\s*'([^']*)'|([^=;\s]+)\s*=\s*([^;]+)|([^=;\s]+)"
    for match in re.finditer(pattern, text):
        if match.group(1): 
            constraints[match.group(1)] = match.group(2)
        elif match.group(3):
            key, val = match.group(3), match.group(4)
            if val.lower() == 'true': val = True
            elif val.lower() == 'false': val = False
            constraints[key] = val
        elif match.group(5):
            constraints[match.group(5)] = True
    return constraints

def _parse_complex(text: str) -> List[ConstraintNode]:
    """
    Parses complex constraint strings with ?, !, and |.
    """
    nodes: List[ConstraintNode] = []
    
    # Split by semicolon first (AND)
    # We treat top-level semicolons as separate constraints (implicitly ANDed)
    parts = _split_respecting_quotes(text, ';')
    for part in parts:
        part = part.strip()
        if not part: continue
        nodes.append(_parse_single_constraint(part))
        
    return nodes

def _split_respecting_quotes(text: str, delimiter: str) -> List[str]:
    parts = []
    current = []
    quote_char = None
    for char in text:
        if quote_char:
            if char == quote_char: quote_char = None
            current.append(char)
        elif char == "'":
            quote_char = "'"
            current.append(char)
        elif char == delimiter:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if current: parts.append("".join(current))
    return parts

def _parse_single_constraint(text: str) -> ConstraintNode:
    text = text.strip()
    
    # Check for OR
    if '|' in text:
        subs = _split_respecting_quotes(text, '|')
        if len(subs) > 1:
            return OrConstraint([_parse_single_constraint(s) for s in subs])

    # Check Key==Val ? Res
    cond_match = re.match(r"^([^?]+)\s*\?\s+(.+)$", text)
    if cond_match:
        condition = cond_match.group(1).strip()
        result = cond_match.group(2).strip()
        return ConditionalConstraint(condition, _parse_single_constraint(result))

    # Check !Not
    if text.startswith('!'):
        return NotConstraint(_parse_single_constraint(text[1:]))

    # Standard Leaf
    # key=value or flag
    kv_match = re.match(r"^([^=]+)=(.+)$", text)
    if kv_match:
        k = kv_match.group(1).strip()
        v = kv_match.group(2).strip().strip("'")
        if v.lower() == 'true': v = True
        elif v.lower() == 'false': v = False
        return LeafConstraint(k, v)
    else:
        return LeafConstraint(text, True)

def normalize_key(key: str) -> str:
    return key.lower().replace(" ", "_")
