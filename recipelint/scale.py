"""Multiply a recipe's quantities by a factor, leaving everything else alone."""

from fractions import Fraction

from .linter import (
    HEADER_FIELD_RE,
    HEADING_RE,
    QUANTITY_RE,
    VAGUE_QUANTITIES,
)

# Denominators a cook can actually measure out. Anything else (sevenths,
# twelfths) is printed as a rounded decimal instead of a fraction nobody
# has a spoon for.
KITCHEN_DENOMINATORS = (2, 3, 4, 8)


def parse_quantity(text):
    """Turn "2 1/4", "3/4", "1.5" or "2" into a Fraction."""
    parts = text.split()
    if len(parts) == 2:
        return Fraction(parts[0]) + Fraction(parts[1])
    return Fraction(parts[0])


def format_quantity(value):
    if value.denominator == 1:
        return str(value.numerator)

    if value.denominator in KITCHEN_DENOMINATORS:
        whole, remainder = divmod(value.numerator, value.denominator)
        fraction = f"{remainder}/{value.denominator}"
        return f"{whole} {fraction}" if whole else fraction

    rounded = f"{float(value):.2f}".rstrip("0").rstrip(".")
    if rounded in ("", "0"):
        # A tiny amount would round to nothing; keep some significance.
        rounded = f"{float(value):.2g}"
    return rounded


def _scale_ingredient(line, factor):
    if any(phrase in line.lower() for phrase in VAGUE_QUANTITIES):
        return line

    indent = line[:len(line) - len(line.lstrip())]
    body = line.strip()
    match = QUANTITY_RE.match(body)
    if not match:
        return line

    scaled = format_quantity(parse_quantity(match.group("qty")) * factor)
    return indent + scaled + body[match.end("qty"):]


def _scale_header(line, factor):
    field = HEADER_FIELD_RE.match(line.strip())
    if not field or field.group(1).lower() != "servings":
        return line

    try:
        value = parse_quantity(field.group(2).strip())
    except (ValueError, ZeroDivisionError):
        return line

    return f"{field.group(1)}: {format_quantity(value * factor)}"


def scale_recipe(text, factor):
    """Return the recipe text with servings and ingredient quantities scaled.

    Works line by line so blank lines, comments in the header, and the
    instructions come through untouched. Vague quantities and lines with no
    leading number are passed through, which is what the linter warns about.
    """
    factor = Fraction(factor)
    section = None
    out = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            out.append(raw)
            continue

        heading = HEADING_RE.match(line)
        if heading:
            section = heading.group(1).strip().lower()
            out.append(raw)
        elif section is None:
            out.append(_scale_header(raw, factor))
        elif section.startswith("ingredient"):
            out.append(_scale_ingredient(raw, factor))
        else:
            out.append(raw)

    return "\n".join(out) + "\n"
