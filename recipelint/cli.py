import argparse
import sys

from .linter import lint


def format_finding(path, finding):
    return f"{path}:{finding.line}: {finding.level}: {finding.message}"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="recipelint",
        description="Lint recipe files for things that break when you scale servings up or down.",
    )
    parser.add_argument("files", nargs="+", help="recipe files to check")
    args = parser.parse_args(argv)

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
