# Conversational-agent ontology exports

This adapter exports the released iCARE Onto into JSON models for conversational-agent use. It also prepares refreshed copies of existing agent models while retaining agent-owned routing, prompt guidance, memory bindings, capture schemas and procedure contracts. The agent application remains a separate codebase.

## Generate and inspect an export

From the repository root, with the core dependencies installed:

```bash
python integrations/conversational-agent/export_agent_models.py export --output build/agent-models
python integrations/conversational-agent/export_agent_models.py verify --bundle build/agent-models
```

Only RDFLib is required; it is already included in the repository dependencies. A standalone installation can use `serialisation/scripts/requirements.txt`. The exporter reads the serialised ontology and its local import catalogue, not screenshots, spreadsheets or network-resolved imports. All output directories must be new; existing files are never overwritten.

The export profile currently selects all 17 modules. `--model clinical_profile --model cancer_history` can restrict the output to selected model IDs. Named parents, types and relationship endpoints from other modules are included when needed.

```text
manifest.json                    Bundle identity, source versions, model paths and file hashes
ontology-index.json              Canonical IRIs, definitions, types, datatypes and value constraints
clinical_profile/model.json      Clinical model in the agent's structural JSON format
cancer_history/model.json        Cancer-history model
...                             Other selected modules
```

A separate `build/agent-models-changes.json` accompanies the export. To compare with a previous bundle:

```bash
python integrations/conversational-agent/export_agent_models.py export --previous build/agent-models --output build/agent-models-next
```

Changes include nodes, relations, taxonomy groups, definitions, property ranges and datatypes. Comparison reports are kept outside the immutable bundle because the same export can be compared with different predecessors.

## Refresh an existing agent copy

Supply the agent's current models directory, containing its `manifest.json` and referenced model files:

```bash
python integrations/conversational-agent/export_agent_models.py refresh --agent-models /path/to/agent/models --bundle build/agent-models --output build/agent-refresh
```

The command creates `build/agent-refresh/refresh-report.json` and a `candidate-models/` directory. It does not modify the supplied agent directory or any stored participant records.

For each existing model it replaces only `model_id`, `title`, `version`, `status`, `source`, `nodes`, `relations` and `taxonomy_groups`. All other model fields are retained, including custom fields, `model_kinds`, `agent_contracts`, `procedure_contracts`, `memory_bindings`, `aliases` and `review_notes`. The complete `runtime` configuration and other application metadata in the agent manifest are retained. Candidate models keep only the modules listed in that agent's own manifest.

- `READY_FOR_AGENT_TESTS` means structural references passed. The candidate still needs the agent project's loading, conversation and memory tests before adoption.
- `REVIEW_REQUIRED` means a binding target or capture mapping is unsupported. The command returns exit code **2**, leaves binding activation unchanged and writes the findings for review. Do not deploy these candidates until resolved. Missing terms are not silently renamed, deleted or invented in the ontology.

Free-text routing and procedure instructions are preserved, not interpreted or enforced by this tool. Their continued suitability needs agent-side review, particularly when the change report lists removed or changed concepts. The exporter does not infer compulsory input fields from OWL domains/ranges, execute memory writes or migrate stored records.

## Copy files or read published files

The publication workflow makes authoritative exports available at:

```text
https://rgu-computing.github.io/icareonto/agent-models/current/manifest.json
https://rgu-computing.github.io/icareonto/agent-models/current/clinical_profile/model.json
https://rgu-computing.github.io/icareonto/agent-models/releases/BUNDLE_ID/manifest.json
```

These paths become available after this implementation is committed and the publishing workflow is run. No w3id rule change is needed: these are application distribution URLs; the ontology terms inside them retain their canonical w3id IRIs.

The fresh export contains ontology structure with **empty agent contracts, procedure contracts and memory bindings**. It is suitable as a data input to the agent's model loader; it must not overwrite an existing combined agent configuration directly. Use `refresh` to prepare copies that retain the application's settings. Each node and relation includes a `description` copied from the ontology's definition, falling back to its comment where necessary. No description is invented where the source has none. Canonical IRIs, definitions, alternative labels, data-property constraints and the distinction between classes and controlled individuals also remain available in `ontology-index.json`. The agent's prompt renderer can use the inline descriptions without loading the index.

An agent can read the manifest and its relative model paths directly over HTTPS, or download a verified local bundle:

```bash
python integrations/conversational-agent/export_agent_models.py download --url https://rgu-computing.github.io/icareonto/agent-models/releases/BUNDLE_ID/ --expected-id BUNDLE_ID --output build/downloaded-agent-models
```

Replace `BUNDLE_ID` with the identifier in the published manifest. The downloader verifies all file hashes, paths and structural references before installing the directory. For deployment, pin a bundle ID and retain a local copy. `current/` can identify a candidate update; it should not cause an untested model change during a conversation.

The bundle identity covers the ontology fingerprint, selected models, profile and exporter code. Export format, exporter and ontology versions are recorded separately. New exports can therefore be published without changing an unchanged ontology version. Archived bundles are preserved by the same publication branch that retains the RDF snapshots.

## Identifier profile and projection scope

`profile.json` maps ontology modules to model IDs and preserves established agent identifiers where their formal ontology counterparts are known. Subsequent labels can change without changing those IDs. New IDs derive deterministically from canonical local names; collisions are rejected. Removed IDs remain reserved in the profile.

The JSON projection contains explicitly asserted named relationships, named subclass hierarchies and instance membership. Anonymous or multiple property domains/ranges are rejected instead of being incorrectly expanded into alternative relationships. It does not replace OWL reasoning. The serialised ontology remains authoritative; the sidecar makes external terms and their IRIs explicit.

The structural `confidence: high` value means the relationship is explicitly asserted in the source ontology; it does not indicate clinical approval. Source term-review annotations are retained in the index.

Review or extend the profile when adding a new ontology module or assigning an established application ID to a renamed formal term. Ambiguous screenshot terms need an explicit modelling decision. A draft application concept with no ontology counterpart can remain application-owned, but should not be presented as an exported ontology class.

## Tests

```bash
python -m unittest discover -s integrations/conversational-agent/tests -v
```

The tests cover ontology coverage, controlled individuals, datatypes, stable IDs, deterministic output, relationship direction, preserved agent settings, invalid bindings, download integrity and output protection. Publication tests under `scripts/tests/` also check preserved exports and introduction of exports into an existing RDF publication.

Original ontology-derived content is CC BY 4.0; exporter software is MIT-licensed. Third-party vocabulary material retains its applicable terms. No participant data or agent-owned operational configuration is published by the exporter.
