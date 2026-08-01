# Pelican scorecard

| Dimension | Core question | Example V1 evidence |
|---|---|---|
| Integrity | Is the artifact safe and valid? | parser limits, forbidden elements, external reference scan |
| Animal identity | Does it read as the requested animal? | ontology features, blind caption, human pairwise rating |
| Animal anatomy | Are required parts plausible? | bill, pouch, wings, legs, webbed feet |
| Object identity | Does it read as the requested mobile object? | component graph and semantic judgement |
| Object mechanics | Are components connected plausibly? | wheels, frame, fork, crank, pedals |
| Interface/role | Is the animal actually riding/driving/piloting/etc.? | contact and occupancy relations |
| Instruction coverage | Are atomic constraints met? | generated scene questions |
| Composition | Is the scene readable and coherent? | occlusion, scale, layout and human preference |
| Artifact editability | Can a requested local edit be made locally? | selector/group structure and repair task |
| Reliability | Does performance persist across samples/paraphrases? | repeated runs and variance |
| Efficiency | What resources were used? | latency, tokens, cost, tool calls |
| Reproducibility | Can the run be identified and repeated? | content-addressed manifest |

## Critical V1 gates

An output is not a successful pelican-on-a-bicycle rendering unless integrity,
animal identity, bicycle identity and riding-interface gates all pass. Aesthetic
quality cannot compensate for one of these failures.
