import argparse
import json
import sys
from . import validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate"])
    parser.add_argument("file")
    args = parser.parse_args()
    try:
        with open(args.file) as stream:
            validate(json.load(stream))
    except (ValueError, OSError):
        print("INVALID: input does not satisfy the contract", file=sys.stderr)
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
