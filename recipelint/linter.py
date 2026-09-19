"""Checks that recipe text will still make sense after you multiply it by 0.5 or 3."""

import re
from dataclasses import dataclass

# Phrases with no fixed amount. Doubling "a pinch" is not "two pinches",
# it's still just "a pinch" -- the whole point is that it isn't measured.
VAGUE_QUANTITIES = (
    "to taste",
    "a pinch",
    "a dash",
    "a splash",
    "as needed",
    "a few",
    "a handful",
    "a couple",
)

# Only the units we can actually reason about for the mixed-system check.
# Counting words ("large", "medium", "whole") are deliberately left out --
# they aren't a measurement system, just a size hint.
UNIT_WORDS = {
    "volume": {
        "cup", "cups", "tsp", "teaspoon", "teaspoons", "tbsp",
        "tablespoon", "tablespoons", "ml", "milliliter", "milliliters",
        "l", "liter", "liters", "pint", "pints", "quart", "quarts",
        "gallon", "gallons",
    },
    "mass": {
        "g", "gram", "grams", "kg", "kilogram", "kilograms", "oz",
        "ounce", "ounces", "lb", "lbs", "pound", "pounds",
    },
}

# A leading quantity: a mixed number ("2 1/4"), a plain fraction ("3/4"),
# a decimal, or an integer. Anything that starts with something else
# (a vague phrase, a parenthetical, free text) is left for the caller
# to classify instead of trying to force it in here.
QUANTITY_RE = re.compile(
    r"""^
    (?P<qty>\d+\s+\d+/\d+ | \d+/\d+ | \d+\.\d+ | \d+)
    \s+
    (?P<unit>[A-Za-z]+\.?)?
    \s*
    (?P<rest>.*)
    $""",
    re.VERBOSE,
)

# A can/jar/package size given as a parenthetical, e.g. "1 (14 oz) can
# crushed tomatoes" or, with no count in front because there's only one
# of it, "(400 g) can crushed tomatoes". The outer number (if any) is how
# many cans -- a count, not a measurement -- so the unit that actually
# matters for the mixed-system check lives inside the parens.
PAREN_UNIT_RE = re.compile(
    r"""\(\s*
    (?:\d+\s+\d+/\d+ | \d+/\d+ | \d+\.\d+ | \d+)
    \s*
    (?P<unit>[A-Za-z]+\.?)
    \s*\)""",
    re.VERBOSE,
)

HEADING_RE = re.compile(r"^#+\s*(.+)$")
HEADER_FIELD_RE = re.compile(r"^([A-Za-z_]+)\s*:\s*(.*)$")


@dataclass
class Finding:
    line: int
    level: str  # "error", "warning", or "info"
    message: str


def parse_recipe(text):
    """Split a recipe file into its header fields and ingredient/instruction lines.

    Sections are introduced by a markdown-style heading ("## ingredients").
    Everything before the first heading is treated as "key: value" header
    fields (title, servings, ...). Blank lines are skipped everywhere.
    """
    header = {}
    header_line_for_key = {}
    section = None
    ingredient_lines = []
    instruction_lines = []

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        heading = HEADING_RE.match(line)
        if heading:
            section = heading.group(1).strip().lower()
            continue

        if section is None:
            field = HEADER_FIELD_RE.match(line)
            if field:
                key = field.group(1).lower()
                header[key] = field.group(2).strip()
                header_line_for_key[key] = line_no
            continue

        if section.startswith("ingredient"):
            ingredient_lines.append((line_no, line))
        elif section.startswith("instruction"):
            instruction_lines.append((line_no, line))

    return header, header_line_for_key, ingredient_lines, instruction_lines


def check_servings(header, header_line_for_key):
    if "servings" not in header:
        return [Finding(1, "error",
                         "no 'servings' field in the header; scaling needs a known base amount")]

    raw = header["servings"]
    line = header_line_for_key["servings"]
    try:
        value = float(raw)
    except ValueError:
        return [Finding(line, "error", f"servings value {raw!r} is not a number")]

    if value <= 0:
        return [Finding(line, "error", f"servings value {raw!r} must be positive")]

    return []


def check_vague_quantities(ingredient_lines):
    findings = []
    for line_no, text in ingredient_lines:
        lowered = text.lower()
        for phrase in VAGUE_QUANTITIES:
            if phrase in lowered:
                findings.append(Finding(
                    line_no, "warning",
                    f"quantity '{phrase}' has no fixed amount and won't scale",
                ))
                break
    return findings


def _quantity_and_unit(text):
    """Find the leading quantity of an ingredient line and any unit tied to it.

    Returns (has_quantity, unit). unit is None when there's a quantity but
    no unit to reason about ("2 large eggs"). It's found by digging into a
    parenthetical can/jar size when the leading number is just a count
    ("1 (14 oz) can ...").
    """
    match = QUANTITY_RE.match(text)
    if match:
        unit = match.group("unit")
        if not unit:
            paren = PAREN_UNIT_RE.search(match.group("rest"))
            if paren:
                unit = paren.group("unit")
        return True, (unit.lower().rstrip(".") if unit else None)

    paren = PAREN_UNIT_RE.match(text)
    if paren:
        return True, paren.group("unit").lower().rstrip(".")

    return False, None


def check_unparseable_quantity(ingredient_lines):
    findings = []
    for line_no, text in ingredient_lines:
        lowered = text.lower()
        if any(phrase in lowered for phrase in VAGUE_QUANTITIES):
            continue
        has_quantity, _ = _quantity_and_unit(text)
        if not has_quantity:
            findings.append(Finding(
                line_no, "warning",
                "no leading quantity found; this line will be left unscaled",
            ))
    return findings


def check_mixed_unit_systems(ingredient_lines):
    systems_seen = {}
    for line_no, text in ingredient_lines:
        _, unit = _quantity_and_unit(text)
        if not unit:
            continue
        for system, units in UNIT_WORDS.items():
            if unit in units and system not in systems_seen:
                systems_seen[system] = (line_no, unit)

    if len(systems_seen) <= 1:
        return []

    parts = [f"'{unit}' on line {line_no}" for line_no, unit in systems_seen.values()]
    first_line = min(line_no for line_no, _ in systems_seen.values())
    return [Finding(
        first_line, "info",
        "recipe mixes measurement systems (" + ", ".join(parts) + "); "
        "pick one before scaling so rounding doesn't compound",
    )]


def lint(text):
    header, header_line_for_key, ingredient_lines, instruction_lines = parse_recipe(text)

    findings = []
    findings += check_servings(header, header_line_for_key)
    findings += check_vague_quantities(ingredient_lines)
    findings += check_unparseable_quantity(ingredient_lines)
    findings += check_mixed_unit_systems(ingredient_lines)

    findings.sort(key=lambda f: f.line)
    return findings
