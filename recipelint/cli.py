import argparse
import sys

from fractions import Fraction

from .linter import lint
from .scale import scale_recipe


def format_finding(path, finding):
    return f"{path}:{finding.line}: {finding.level}: {finding.message}"


def parse_factor(value):
    try:
        factor = Fraction(value)
    except (ValueError, ZeroDivisionError):
        raise argparse.ArgumentTypeError(f"{value!r} is not a number")
    if factor <= 0:
        raise argparse.ArgumentTypeError(f"factor {value!r} must be positive")
    return factor


def scale_file(path, factor):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        print(f"{path}: could not read file ({exc.strerror})", file=sys.stderr)
        return 1

    sys.stdout.write(scale_recipe(text, factor))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="recipelint",
        description="Lint recipe files for things that break when you scale servings up or down.",
    )
    parser.add_argument("files", nargs="+", help="recipe files to check")
    parser.add_argument(
        "--scale", metavar="FACTOR", type=parse_factor,
        help="print the recipe with servings and quantities multiplied by "
             "FACTOR (e.g. 2, 0.5, 3/2) instead of linting it; takes one file",
    )
    args = parser.parse_args(argv)

    if args.scale is not None:
        if len(args.files) != 1:
            parser.error("--scale takes exactly one recipe file")
        return scale_file(args.files[0], args.scale)

    had_error = False
    for path in args.files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            print(f"{path}: could not read file ({exc.strerror})", file=sys.stderr)
            had_error = True
            continue

        for finding in lint(text):
            print(format_finding(path, finding))
            if finding.level == "error":
                had_error = True

    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())
