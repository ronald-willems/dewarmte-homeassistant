# DeWarmte integration documentation

This folder holds the documentation that is not in the main [README](../README.md).

## For users

- [ENTITIES.md](ENTITIES.md): every entity the integration creates, with a one-sentence description and the device types it applies to. Regenerate it with the prompt in [REGENERATE_ENTITY_DOCS_PROMPT.md](REGENERATE_ENTITY_DOCS_PROMPT.md) after adding or changing entities.

## For developers

- [WEBAPP_SCHEMA.md](WEBAPP_SCHEMA.md): what the official web app requires from the settings API (required and nullable fields, write bodies), extracted from the app's own JavaScript bundle. This is the reference when a user's payload differs from what the integration expects. See `scripts/extract-webapp-schema.py`.
- [AGENTS.md](../AGENTS.md) in the repository root: repository layout, Home Assistant rules the code follows, and the local test, deploy and log workflow.
- `../custom_components/dewarmte/api/openapi.yaml`: the DeWarmte API as the integration uses it.

## Diagrams

The PlantUML sources describe how the integration is put together. The PNGs in `images/` are generated from them with `scripts/generate_diagrams.sh` (needs `plantuml`, which needs Java).

| File | Shows |
|------|-------|
| `class_diagram.puml` | The classes of the integration: coordinator, API client, models and entities. |
| `setup_sequence.puml` | What happens when the integration is set up: login, device discovery, one coordinator per device, platform setup. |
| `update_cycle_sequence.puml` | One polling cycle: the coordinator fetches status and settings and the entities update. |
| `switch_control_sequence.puml` | What happens when a setting is changed from Home Assistant: the write, the API's echo of the new settings, and the entity update. |

`DeWarmte Integration Flow.png` is an older overview of the same flow.

### Viewing a diagram

- **Online**: paste the file's contents into the [PlantUML server](http://www.plantuml.com/plantuml/uml/).
- **VS Code**: install the PlantUML extension, open the file and press Alt+D.
- **Command line**: `brew install plantuml` (macOS) or `apt-get install plantuml`, then `scripts/generate_diagrams.sh` to regenerate all PNGs, or `plantuml docs/<file>.puml` for one.

The diagrams were drawn for the first version and are not updated with every change. The code is authoritative; treat them as an introduction to the structure (coordinator per device, API client, entities reading from coordinator data), not as a specification.
