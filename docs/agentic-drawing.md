# Agentic drawing strategy

## Canonical environment: PelicanCanvas

A browser SVG environment gives every agent a deterministic canvas, explicit
element tree, bounded actions, screenshots/renders, undo, checkpoints and event
trace. It is independent of one desktop application's plugin policy and supports
containerised OpenEnv deployment.

## Real-application options

| Option | Strengths | Limitations | Recommendation |
|---|---|---|---|
| Penpot | Open source, self-hostable, editable vector/design model, promising MCP pathway | Adapter maturity must be validated | Preferred first real-app target |
| Figma | Mature collaboration and broad ecosystem | Commercial service, permissions and reproducibility constraints | Optional comparison adapter |
| Krita + `edithatogo/krita-cli` | Existing 50+ tool raster workflow, replay, rollback and pelican history | Plugin/support friction and raster-first model | Preserve as legacy and import trajectory evidence |
| Inkscape | Open SVG-native CLI and renderer | Interactive automation surface less uniform | Renderer/validator first; editing adapter later |
| Blender | Strong 3D/animation automation | Different task class and much larger action space | Post-v1 3D track |

## Trajectory outcomes

Final score, improvement from initial state, area under quality-versus-step curve,
steps to threshold, regressions, recovery, redundant actions, inspection before
revision, critique accuracy, local preservation and resource cost are reported.
Controlled failures test recovery from missing references, stale canvas state,
ambiguous feedback and tool errors.
