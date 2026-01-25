# Math Formatting Rules

When writing mathematical expressions, follow these rules EXACTLY:

## Inline Math
Use single dollar signs for math within text:
- $V = IR$ (Ohm's law)
- $F = ma$ (Newton's second law)
- $E = mc^2$ (mass-energy equivalence)

## Display Math (Standalone Equations)
Use double dollar signs on their own line for important equations:

$$
F = ma
$$

$$
\frac{d}{dx}(x^2) = 2x
$$

## Fractions and Complex Expressions
Use LaTeX notation inside dollar signs:
- Inline fraction: $\frac{a}{b}$
- Display fraction: $$\frac{dy}{dx} = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$$

## FORBIDDEN FORMATS (NEVER USE)
- `\(...\)` or `\[...\]` notation - WRONG
- Bare brackets like `[ V = IR ]` - WRONG
- Unicode math symbols without LaTeX - WRONG
- Plain text equations like "V equals I times R" when math symbols exist - WRONG

## Examples

CORRECT:
```
Ohm's law states that $V = IR$, where $V$ is voltage, $I$ is current, and $R$ is resistance.

For the quadratic formula:
$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$
```

WRONG:
```
Ohm's law states that \(V = IR\)
The equation [ V = IR ] shows...
V equals I times R
```

## When to Use Display vs Inline
- **Inline ($...$)**: Variables, simple expressions, equations within sentences
- **Display ($$...$$)**: Important formulas, multi-line derivations, equations you want to emphasize
