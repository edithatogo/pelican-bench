# Ontology roadmap

## Seed layer

1. `Animal`: generic anatomy, identity evidence and locomotor parts.
2. `Pelican`: bill, gular pouch, wing, webbed foot and posture constraints.
3. `MobileNonLivingObject`: components, support, control, propulsion and motion.
4. `Bicycle`: two-wheel cycle topology, frame, steering and pedal drivetrain.
5. `AgentMobilitySystemInterface`: role, support, contact, control, occupancy and
   force relations.
6. `PelicanBicycleRidingInterface`: concrete composition of the three layers.

## Abstraction

The ontology is not intended to become a single universal biological or vehicle
ontology. It is an evaluation ontology: the smallest explicit concepts needed to
generate tasks, ask atomic questions, interpret failures and support extensions.
External ontologies may be mapped through identifiers, while PelicanBench retains
its own stable evaluation contract.

## Formal interoperability profile

[`benchmark/ontologies/interoperability-profile.json`](../benchmark/ontologies/interoperability-profile.json)
is the machine-readable boundary between local evaluation semantics and the wider ontology
ecosystem. It records:

- JSON, JSON-LD and SHACL representations;
- validation surfaces and executable competency cases;
- UOGTO as a design-pattern source, not a game-theory semantic import;
- HPO as a mature governance and identifier reference, not a clinical class import; and
- `edithatogo/w3id.org` as the intended persistent namespace host.

The namespace `https://w3id.org/pelicanbench/ontology#` is currently
`registration-planned`. PelicanBench must not represent it as published until a reviewed
resolver rule and registration evidence are committed. A future semantic import requires
an explicit mapping, licence decision, version pin, competency tests and modelling rationale.

Validation is executable:

```bash
pelicanbench ontology-interoperability-status
pelicanbench validate-repo
```

## AI-generated extensions

Agents may propose new animal, object and interface classes from a source pack.
A proposal must include provenance, definitions, parent classes, distinguishing
features, required/optional parts, role compatibility, competency questions,
negative examples, SHACL-like constraints and held-out validation. Promotion is
manual and versioned.
