from typing import Dict, Any, Union

import re

def parse_constraints(annotation_str: str) -> Dict[str, Any]:
    """
    Parses a constraint string into a dictionary.
    Example: "min=10; max=20; unique" -> {'min': '10', 'max': '20', 'unique': True}
    Handles quoted values: "description='foo; bar'"
    """
    if not annotation_str: return {}
    constraints = {}
    
    # Split by semicolon but respect quotes
    # Regex lookbehind/ahead is complex, let's use a simpler state machine or specific regex
    # Pattern: key='value' OR key=value OR boolean_flag
    # separated by ; (and whitespace)
    
    # Matches: key='val' | key=val | flag
    pattern = r"([^=;\s]+)\s*=\s*'([^']*)'|([^=;\s]+)\s*=\s*([^;]+)|([^=;\s]+)"
    
    matches = re.finditer(pattern, annotation_str)
    
    for match in matches:
        if match.group(1): # key='val'
            key, val = match.group(1), match.group(2)
            constraints[key] = val
        elif match.group(3): # key=val
            key, val = match.group(3), match.group(4)
            # Handle booleans in unquoted values
            if val.strip().lower() == 'true': val = True
            elif val.strip().lower() == 'false': val = False
            else: val = val.strip()
            constraints[key] = val
        elif match.group(5): # flag
            key = match.group(5)
            constraints[key] = True
            
    return constraints

def normalize_key(key: str) -> str:
    """
    Normalizes keys to snake_case.
    e.g. 'minItems' -> 'min_items' (if we supported camelInput)
    But our spec focuses on snake_case input.
    """
    return key.lower().replace(" ", "_")
