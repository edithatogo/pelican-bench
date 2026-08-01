# History and prior art

## The natural experiment

Simon Willison's recurring request, “Generate an SVG of a pelican riding a
bicycle,” became an unusually persistent informal test of language-model visual
reasoning. The archive records model generations, output artifacts and evolving
commentary across time. It is valuable because the prompt is stable, SVG exposes
both source and rendered behaviour, and failures are immediately legible to
non-specialists.

Its limitations are equally useful: the prompt is public and increasingly
familiar; models and vendors may have encountered it; one aesthetically pleasing
sample does not measure reliability; and informal commentary cannot be treated
as a calibrated scalar ground truth.

## Agentic drawing experiment

Dylan Mordaunt reproduced the task through iterative tool use rather than native
image generation. The resulting contact sheets and revisions shifted the unit of
analysis from “model output” to the full system: model, instructions, harness,
tool affordances, observations, persistence, references, cost and feedback.
This motivates a separate agentic track rather than merging tool-using systems
with direct generators.

## Environment and proxy-gaming work

Sergio Paniego's public Pelican/OpenEnv work demonstrates both the feasibility of
an executable environment and the danger of narrow structural rewards. A system
can optimise circles, alignment or coarse relative position without producing a
recognisable animal–vehicle scene. PelicanBench therefore treats structural
metrics as interpretable evidence and gates, not a complete reward.

## Pelicanmaxxing

Factorial animal–vehicle tests can ask whether the exact pelican–bicycle cell is
better than expected from a model's general animal and vehicle ability. The
benchmark formalises that question as an interaction estimate with uncertainty,
not an accusation of deliberate training.

## Sources

The machine-readable registry is `data/sources/source-registry.json`. It records
links and rights state but deliberately does not contain third-party article text
or image bytes.
