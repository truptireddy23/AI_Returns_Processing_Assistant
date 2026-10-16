"""Write the API's OpenAPI schema to a file (used to generate frontend types)."""

import json
import sys
from pathlib import Path

from returnguard.main import create_app


def main() -> None:
    out = Path(sys.argv[1])
    out.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
