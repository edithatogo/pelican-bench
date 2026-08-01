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

## AI-generated extensions

Agents may propose new animal, object and interface classes from a source pack.
A proposal must include provenance, definitions, parent classes, distinguishing
features, required/optional parts, role compatibility, competency questions,
negative examples, SHACL-like constraints and held-out validation. Promotion is
manual and versioned.
