# recipelint

A linter for recipe files. It doesn't scale a recipe for you -- it checks
whether the recipe *can* be scaled without someone having to guess.

## the problem

Recipes get written for one occasion and then reused at other sizes: you
want to halve a recipe for two people, or triple it for a party. That
multiplication only works cleanly if every quantity in the recipe is
actually a number. In practice recipes are full of things that don't
survive being multiplied by 0.5 or 3:

- `salt to taste`, `a pinch of nutmeg`, `a splash of milk` -- there's no
  number here to scale in the first place.
- No servings count in the recipe at all, so there's no base to scale
  from.
- Cups in one line and grams in another. Converting each independently
  and rounding compounds the error across the recipe.
- Free-text amounts like `a can of crushed tomatoes` that a scaling
  script will silently skip.

`recipelint` reads a recipe file and reports every line where this will
bite you, with a line number, before you find out the hard way in the
middle of cooking.

## recipe file format

```
title: Chocolate Chip Cookies
servings: 24

## ingredients
2 1/4 cups all-purpose flour
1 tsp baking soda
1 cup butter, softened
3/4 cup sugar
2 large eggs
a pinch of flaky sea salt for topping

## instructions
Preheat oven to 375F.
Cream butter and sugar, beat in eggs.
Fold in the dry ingredients.
```

The header (before the first `##` section) is `key: value` pairs.
`servings` is required -- it's the base amount everything else in the
file is scaled relative to. Ingredient lines start with a quantity
(a whole number, a decimal, a fraction like `3/4`, or a mixed number
like `2 1/4`) followed by a unit and the ingredient name.

## usage

```
python -m recipelint.cli examples/cookies.recipe
```

Against the example above (see `examples/cookies.recipe`), that prints:

```
examples/cookies.recipe:12: info: '2 eggs' counts whole items; a non-integer multiplier (1.5x, 0.75x, ...) leaves a fractional amount that doesn't work in the kitchen
examples/cookies.recipe:14: warning: quantity 'a pinch' has no fixed amount and won't scale
```

Every other line in that file parses cleanly, has a consistent (volume)
unit system, and the recipe declares its servings count, so nothing else
is flagged. Exit status is non-zero only if at least one `error`-level
finding was reported (currently: a missing or invalid `servings` field).

If installed as a package (`pip install .`), the same check is available
as `recipelint examples/cookies.recipe`.

## what it checks today

- missing or non-positive `servings` field (error)
- vague quantities with no fixed amount: "to taste", "a pinch", "a
  splash", and similar (warning)
- ingredient lines with no leading quantity at all, e.g. free text like
  "a can of tomatoes" (warning)
- a recipe mixing volume units (cups, tsp) and mass units (g, oz) across
  different ingredients (info) -- this also looks inside can/jar sizes
  given as a parenthetical, e.g. `1 (14 oz) can crushed tomatoes`, since
  the unit that matters for this check is the one in the parens, not the
  can count in front of it
- whole-item counts like `2 eggs`, `3 cloves garlic`, or `1 can` of
  something (info) -- these scale cleanly by a whole factor (2x, 3x) but
  a 1.5x or 0.75x scale leaves a fractional egg or can that someone has
  to round off by hand

## license

MIT, see LICENSE.
