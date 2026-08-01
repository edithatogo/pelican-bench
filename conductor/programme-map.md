# Programme map

```mermaid
flowchart TB
    T00[Foundation and governance] --> T02[Schemas and provenance]
    T01[History and rights] --> T04[Corpus NLP and idea coverage]
    T01 --> T05[Longitudinal quantification]
    T03[Ontologies] --> T06[SVG and render scoring]
    T03 --> T08[Affordance-aware task grammar]
    T04 --> T07[Semantic and human calibration]
    T05 --> T09[Statistics and Pelicanmaxxing]
    T06 --> T10[Runner and adapters]
    T07 --> T10
    T08 --> T10
    T09 --> T10
    T10 --> T11[Hugging Face execution]
    T10 --> T13[Explorer]
    T14[Repair] --> T15[Agentic environments]
    T15 --> T16[Trajectories and learning]
    T17[Security and adversarial] --> T06
    T17 --> T10
    T18[Accessibility] --> T15
    T12[CI, supply chain and Entire] --> T20[Maturity and releases]
    T11 --> T19[Publications]
    T13 --> T19
    T20 --> T21[Video, 3D and transfer]

    RB01{{RB-01 Measurement validity}} --> T06
    RB01 --> T07
    RB01 --> T17
    RB02{{RB-02 Prospective pilot}} --> T08
    RB02 --> T09
    RB02 --> T10
    RB03{{RB-03 Human calibration}} --> T07
    RB03 --> T09
    RB04{{RB-04 Reproduction and publication}} --> T11
    RB04 --> T12
    RB04 --> T20
    RB05{{RB-05 Rights and governance}} --> T01
    RB05 --> T04
    RB05 --> T18
```

V1 is the narrow empirical slice through T00, T02, T03, T06, T07, T08, T09, T10, T11, T12, T17 and T20. Repair and agentic drawing remain V1.x tracks rather than enlarging the initial claim. The five release blockers cut across capability tracks and prevent fixture completion from being mistaken for empirical or operational maturity.
