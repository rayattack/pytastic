import sys
import traceback

print("Starting debug script...", file=sys.stderr)
try:
    from pytastic import Pytastic
    print("Import successful", file=sys.stderr)
    vx = Pytastic()
    print("Instantiation successful", file=sys.stderr)
except Exception:
    print("Caught exception:", file=sys.stderr)
    traceback.print_exc()
