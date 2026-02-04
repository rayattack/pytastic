from typing import Dict, Any, Union

def parse_constraints(annotation_str: str) -> Dict[str, Any]:
    """
    Parses a constraint string into a dictionary.
    Example: "min=10; max=20; unique" -> {'min': '10', 'max': '20', 'unique': True}
    """
    if not annotation_str: return {}
    constraints = {}
    parts = annotation_str.split(';')
    
    for part in parts:
        part = part.strip()
        if not part: continue
        if '=' in part:
            key, value = part.split('=', 1)
            key, value = key.strip(), value.strip()
            
            if value.lower() == 'true': value = True
            elif value.lower() == 'false': value = False
            constraints[key] = value
        else: constraints[part] = True
    return constraints

def normalize_key(key: str) -> str:
    """
    Normalizes keys to snake_case.
    e.g. 'minItems' -> 'min_items' (if we supported camelInput)
    But our spec focuses on snake_case input.
    """
    return key.lower().replace(" ", "_")
