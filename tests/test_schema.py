import unittest
import json
from typing import TypedDict, Annotated, List, Literal
from pytastic import Pytastic

vx = Pytastic()

class Model(TypedDict):
    name: Annotated[str, "min_len=3"]
    age: Annotated[int, "min=18; max=99"]
    tags: Annotated[List[str], "min_items=1"]
    status: Literal["active", "inactive"]

vx.register(Model)

class TestJsonSchema(unittest.TestCase):
    def test_schema_generation(self):
        schema_json = vx.schema(Model)
        schema = json.loads(schema_json)
        
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["name"]["type"], "string")
        self.assertEqual(schema["properties"]["name"]["minLength"], 3)
        
        self.assertEqual(schema["properties"]["age"]["type"], "integer")
        self.assertEqual(schema["properties"]["age"]["minimum"], 18.0)
        
        self.assertEqual(schema["properties"]["tags"]["type"], "array")
        self.assertEqual(schema["properties"]["tags"]["minItems"], 1)
        
        self.assertEqual(schema["properties"]["status"]["enum"], ["active", "inactive"])
        
        print("\nGenerated Schema:\n", schema_json)

if __name__ == "__main__":
    unittest.main()
