# Education Resource Selector

This workflow reads the curated resource worksheet and publishes ontology-based metadata, resource-selection results and three draft educational activity templates. The current collection has **41 approved, complete resources** across Spanish (11), English (11), German (6), Italian (5), Polish (4) and Portuguese (4). The public source worksheet contains only these curated and annotated entries. The workbook is the curation input; the generated JSON and RDF can be used without Excel or the source workbook at runtime.

Original catalogue metadata, annotations and learning-activity content are CC BY 4.0; the software is MIT-licensed. RDF graph headers record the metadata licence and attribution; `catalogue.json` provides `metadata_license` and `metadata_rights`. Each resource retains its separate permitted-use annotation. Linked provider content retains its own terms, including any registration or copying restrictions. Catalogue licensing grants no permission to reproduce or ingest the linked publications. See [licence scope](../LICENSE.md) and [third-party notices](../THIRD_PARTY_NOTICES.md).

The [tool overview](../TOOLS.md) describes the selector's role and its relationship to the other components.

The workflow exports **metadata and source links**. All current resources are marked Link / Signpost Only, so it does not download, reproduce or ingest their full text. A resource requiring registration can remain eligible after its content has been reviewed; the interface returns its access conditions. Collection-page annotations describe their reviewed scope and do not certify every linked item.

## Build and update

Use Python 3.10+ with the dependencies in `requirements.txt`. From the project root:

```bash
python education/scripts/education_resources.py build
```

The defaults are `sources/MAYA_consolidated_educational_resources.xlsx` and the **Release resources** worksheet. The filename stays stable; Git history, source hashes and catalogue releases identify revisions. For a different file or worksheet:

```bash
python education/scripts/education_resources.py build \
  --workbook /path/to/reviewed-resources.xlsx \
  --sheet "Release resources" \
  --output /path/to/education-output \
  --ontology-dir /path/to/serialisation \
  --base-iri https://your-project.example/education/
```

Save Excel before running the build. It reads the saved file rather than an open Excel session. Header names locate fields, so changing column order or moving the header row does not break the import. `MAYA Target audience` and `Target audience` are accepted header variants. The obsolete Suggested support needs column is ignored. Publication / last updated is preserved verbatim because entries may contain a year, an update date or a provider-review date; a new publication date is never inferred.

The curation columns are **Curated by**, **Curation date** and **Applicability notes**. The importer uses these names directly. JSON records expose `curated_by`, `curation_date` and `applicability_notes`; RDF uses `edu:curatedBy`, `edu:curatedOn` and `edu:applicabilityNotes`. The catalogue profile is version `1.2`. These fields document catalogue curation, not clinical approval for use at a particular site.

To add resources, add rows with unused Resource IDs, complete the annotations, record curator/date, and set **Curation status = Approved** and **Completion status = Complete**. Rerun the same command. No list of permitted resource IDs is hard-coded. Applicable activity templates also acquire newly eligible resources automatically through their topic, need, audience and journey-stage criteria.

The importer requires the curated title, URL, language, audience, journey stage, topic, need, purpose, format, complexity, provider, description, access conditions, permitted use and curation details. Unknown vocabulary values, duplicate IDs or incomplete approved entries stop publication and leave the current release intact. Other statuses are excluded. `--allow-empty` explicitly permits withdrawing all resources.

Changing an existing row updates that resource while retaining its IRI. Putting it on hold, removing it, or changing it away from approved/complete withdraws it from the next active release. Repeated processing of unchanged inputs returns `UNCHANGED`. Resource identity comes from the Resource ID, not its row number, title or URL. Keep the deployment namespace stable; use a separate output directory for another namespace.

## Outputs and publication

`generated/current.json` points to the current release under `generated/releases/<release-id>/`. Each release contains:

| File | Content |
|---|---|
| `catalogue.json` | Ordinary application JSON containing resource metadata and available activity templates; not JSON-LD |
| `catalogue.ttl` | Shared resource knowledge graph using iCARE Onto |
| `activity-templates.ttl` | Three draft health-literacy interventions, their goals and eligible resources |
| `dataset.ttl` | Entry point importing the resource and activity graphs; it does not repeat their assertions |
| `dataset.trig` | The two instance graphs as named graphs |
| `catalog-v001.xml` | Offline import resolution for Protégé |
| `manifest.json` | File integrity hashes |
| `validation/build-report.json` | Included/excluded entries, additions, changes and withdrawals |
| `validation/source-records.json` | Original worksheet values and row-level audit provenance |
| `validation/shacl-report.ttl` | Required-field and controlled-value graph checks |

These are different formats and entry points within one release. `catalogue.ttl` contains the actual resource metadata in RDF and imports iCARE Onto. `dataset.ttl` brings that catalogue and `activity-templates.ttl` together through imports, making it the convenient file to open in Protégé. `dataset.trig` contains both sets of assertions directly as separate named graphs for a graph store. Applications can use `catalogue.json` without parsing RDF.

Different release directories represent historical snapshots. `current.json` identifies the active snapshot; it does not contain the resource records themselves.

All files are validated and written before one atomic update of `current.json` publishes the release. Earlier snapshots are retained. Consumers must resolve the current pointer when refreshing their catalogue; an old snapshot intentionally continues to contain its historical resources. Do not edit generated files. This local publisher expects one writer; an application should serialise build calls. A graph-store deployment must replace the active catalogue/activities graphs rather than append old and new snapshots, otherwise withdrawn resources remain queryable.

Open the current release's `dataset.ttl` in Protégé and keep the relative directory structure alongside `serialisation/`. For a graph store, load the ontology separately and load the **current** `dataset.trig`; OWL imports in Turtle do not themselves configure a Fuseki dataset. No server connection or deployment is performed by these scripts.

The distributed release is under `data/catalogue/`. [examples/demo/participant-education.ttl](examples/demo/participant-education.ttl) is a compact fictional participant example importing that release through its adjacent catalogue. Ordinary generated runs are excluded; this selected example is retained for inspection.

The `education/metadata#` annotations record application metadata such as journey stage, access conditions and curation state. They are declared as OWL annotation properties in the generated graphs and do not add domain entities to the core ontology. Topics, needs, purposes and other controlled classifications use the actual iCARE Onto values. Country of contribution is never used as a language or eligibility inference. English and Spanish map to generic `en` and `es`, not unverified regional variants.

## Resource access and need-based selection

A consuming interface can use `catalogue.json` and its resource descriptions, classifications and source links for participant-led browsing and filtering. Browsing does not require a recorded health-literacy need. The participant-facing browsing interface is supplied by the consuming application; it is not bundled in this repository.

For need-based signposting, the selector below accepts an identified need and participant context and returns candidate links with matching explanations. Its request requires a need and its identification method/source. Keep browsing independent of this request contract rather than inventing a need to retrieve resources. Both routes can be used without executing a structured educational activity or an avatar-led lesson.

## Selection interface

```bash
python education/scripts/education_resources.py select \
  --request education/examples/spanish-cardiovascular.json
```

`schemas/selection.schema.json` documents the readable request contract. Required inputs are the intended audience, one of the three journey stages, language, topic(s), identified need(s), and the method/source of need identification. The sample is a fictional discussion, not a validated assessment instrument. The operational selector does not save participant requests.

Resources must match the audience, journey stage and language, plus at least one requested topic and at least one identified need. Required accessibility features are strict constraints. Preferred formats and complexities affect ordering; they do not silently exclude all other resources. A generic language such as `es` matches `es-ES`; a resource advertised only as `es-ES` is not automatically assumed suitable for every other regional variant. Match ordering is deterministic and ties use Resource ID. The response records the actual need/topic matches and which preferences are met.

`include_registration_required: false` excludes registration/access-restricted resources. The default includes reviewed restricted resources and returns an explicit access flag. No match returns `NO_SUITABLE_RESOURCE` and the unmet needs; no unrelated language or topic is substituted. The selector rejects a catalogue built against a different ontology fingerprint until it is rebuilt.

These are metadata-matched candidate signposts. Free-text applicability conditions, age ranges, clinical restrictions and local service eligibility are returned for the delivery component to interpret. The current request does not enforce arbitrary clinical conditions or infer literacy needs from diagnoses. Marking a resource approved does not establish that it is suitable for every participant.

From a Python backend running from the project root:

```python
from education.scripts.education_resources import build_release, load_release, select_resources

# Run after a saved curation update; use a single publisher.
report = build_release(workbook="/path/to/reviewed-resources.xlsx", sheet="Release resources")

# A form, assessment service or avatar can provide this documented request object.
catalogue = load_release()
response = select_resources(request, catalogue)
```

The response contains identifiers, URLs, descriptions, access/rights metadata and match explanations. T3.3 can use these to introduce educational activities and select signposts. No HealthRAG full-text ingestion, avatar execution, FHIR update or live graph-store synchronisation is claimed.

## Educational activities and demonstration

`activities.json` contains MAYA-authored **Draft** templates for:

1. Understanding cardiovascular follow-up.
2. Making manageable everyday health choices.
3. Adjusting to life after treatment.

Each includes a learning objective, identified needs, resource-selection criteria, delivery steps and reflection/understanding-check prompts. They reuse resources through links and do not reproduce their text. These new activity templates need editorial/domain review before being adopted for participant delivery; approval of the source resources is a separate decision.

These templates and the fictional intervention graph illustrate possible future structured educational interaction. The catalogue and resource-selection workflows operate independently of them. They do not establish implemented avatar-led teaching, participant completion or demonstrated learning.

```bash
python education/scripts/education_resources.py demo
```

The default fictional profile requests cardiovascular information after treatment, prefers Spanish and has an explicitly identified comprehension need. The current catalogue returns **MAYA-EDU-0004** and **MAYA-EDU-0077e** as candidates, with the former ranked first because it also matches the preferred foundational complexity. The example links their real resource metadata to a fictional `HealthLiteracyIntervention` and connects that intervention to the fictional person's draft care plan and goal. The graph records the discussion method and need, rather than inferring a need from a clinical record. `generated/demo/learning-activity.json` shows the objective, steps and prompts; `participant-education.ttl` can be opened in Protégé using its adjacent catalogue. No delivery, completion or literacy improvement is asserted.

`examples/english-nutrition.json` selects **MAYA-EDU-0023** for an information-appraisal need, with its registration requirement exposed. The `queries/` folder contains a catalogue query and an independent Spanish cardiovascular query. The fixed regression fixture keeps its independently specified expected matches even as the packaged catalogue grows.

## Verification

Controlled annotations are validated directly against the ontology, and journey stages against the three permitted values. Unknown values stop publication; no fuzzy mapping or resource-specific substitutions are used.

```bash
python education/scripts/check_workflow.py
```

Run this command in the Python environment containing the declared dependencies.

These are 43 Python `unittest` tests of workflow behaviour. Examples include automatically publishing a new approved/complete ID, withdrawing a resource while preserving history, retaining its IRI after an update, rejecting duplicate IDs without replacing the active release, returning the independently specified Spanish cardiovascular match, and exposing registration requirements. They also simulate interrupted writes and manually altered release files, check that catalogue licensing preserves each linked publication's permitted-use annotation, and verify that curation metadata survives JSON/RDF publication and that missing curation details are rejected.

`reports/WORKFLOW_CHECKS.md` lists every test and result; `reports/workflow-checks.json` provides the same results for software. Tests use `tests/fixtures/reviewed-rows.json`, a fixed reviewed-metadata sample, and temporary outputs. Later additions to the live workbook do not change the regression baseline, and tests leave that workbook unchanged. A normal build separately validates all currently eligible rows and their generated graph. Existing ontology and 78-CQ validation remain separate activities. These tests establish technical behaviour, not educational effectiveness.

For an optional OWLAPI/HermiT check of the demonstration:

```bash
python serialisation/scripts/validate_with_protege.py \
  --protege-app /path/to/Protege.app \
  --output education/generated/demo \
  --ontology-file education/generated/demo/participant-education.ttl \
  --report education/reports/owlapi-report.json
```

The minimum ongoing cycle is: review an entry, approve and complete it, save the workbook, rebuild, inspect the change report, and refresh the consuming service's current catalogue. Prioritise further resources using recorded language, topic, format and support-need gaps and participant/professional feedback. Recording signposting or resource use is separate from assessing changes in health literacy.
