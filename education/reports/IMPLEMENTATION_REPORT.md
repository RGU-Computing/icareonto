# MAYA educational resource workflow

Initially implemented on 3 November 2026; the packaged catalogue, selected example and education-specific validation evidence were refreshed on 23 November 2026. This package connects curated and annotated educational resources to ontology-based selection and draft learning activities. It is an offline, reusable workflow for subsequent Health Hub and avatar integration.

## Current collection and ontology

The release contains **41 resources** marked both Approved and Complete in the saved Release resources worksheet: 11 Spanish, 11 English, six German, five Italian, four Polish and four Portuguese. The public source sheet contains only these 41 entries. Approved resources with verified registration requirements remain eligible, with their access conditions exposed to the delivery component.

The 23 November update adds ten records: English and Spanish ESMO survivorship editions, the inventory's English NCI survivorship guide, a Polish Alivia information-appraisal article, English and Spanish NCI information-appraisal pages, German fatigue guidance, Italian symptom guidance, Portuguese misinformation guidance and an English smoking-cessation page. It also adds self-monitoring annotations to the existing Polish and Portuguese survivorship guides and cardiovascular-late-effects coverage to the Portuguese guide. No existing resource was withdrawn. Across the eight ontology topics and six catalogue languages, the remaining zero annotation cell is Spanish self-monitoring; this does not establish absence of relevant content in every resource.

The ontology remains technical version `0.2.0`, generated from `icareonto_review_workbook_v221126.xlsx`, with 17 modules, 283 classes, 284 object properties, 137 data properties, 304 controlled values and 62 schemes. This catalogue refresh uses the same ontology fingerprint; it does not alter the core ontology.

The source is now `sources/MAYA_consolidated_educational_resources.xlsx`, using a stable filename and the headings `Curated by`, `Curation date` and `Applicability notes`. The importer maps controlled labels to ontology IRIs, preserves Resource IDs, separates semicolon-delimited values, retains curation and rights metadata, and publishes metadata and links without retrieving source content. Catalogue profile `1.2` exports `curated_by` and `curation_date` in JSON and `edu:curatedBy` and `edu:curatedOn` in RDF; applicability notes remain `applicability_notes` / `edu:applicabilityNotes`. The previous curation headings and export fields are not supported. Application annotations describe catalogue curation, not clinical approval for every participant or site.

The packaged release identifier is `d72ec58cb5da7142a48583bb`. Its build report records all 31 existing records as updated because the curation fields changed; ten further records are additions. Source hashes and row provenance are retained in validation sidecars.

Controlled annotations are validated directly against ontology values. Journey stages use the three permitted options; no resource-specific substitutions are applied.

## Educational activities and matching

Three newly authored templates cover cardiovascular follow-up, everyday nutrition/activity choices and adjustment after treatment. Each records a learning objective, need/topic criteria, delivery steps and reflection prompts. Their **Draft** status is separate from the approval of the underlying resources. They require editorial/domain review before participant delivery.

Selection requires matching audience, journey stage, language, at least one identified need and at least one requested topic. Required accessibility annotations are enforced. Format and complexity preferences affect ordering and are reported transparently. No matching resource produces an explicit gap. Clinical suitability, age-specific applicability and local service eligibility remain contextual considerations for the delivery component rather than unimplemented automatic guarantees.

The fictional post-treatment cardiovascular example returns **MAYA-EDU-0004** and **MAYA-EDU-0077e** for an identified comprehension need and a Spanish language preference. Both match the preferred written format and have standard complexity. The preferred foundational complexity is reported as unmet, and Resource ID breaks the ranking tie. Its RDF links a fictional participant and needs-identification event to a draft care plan, goal and HealthLiteracyIntervention using both resources' real metadata. The English nutrition request still selects **MAYA-EDU-0023** for an information-appraisal need and exposes its registration requirement. These examples do not assert delivered interventions, completed learning or improved literacy.

## Validation

The education-specific checks below were repeated on 23 November 2026 against the refreshed catalogue and unchanged ontology 0.2.0.

| Validation activity | Result |
|---|---|
| Educational workflow tests | 43 checks passed, with no failures or errors; workbook unchanged during testing |
| Resource graph validation | All 41 records passed required-field SHACL and explicit ontology type/domain/range checks |
| Educational demonstration OWLAPI/HermiT | 26 documents; zero OWL 2 DL violations; consistent; no unsatisfiable named classes |
| Source integrity | All four input files match their source-manifest byte counts and SHA-256 hashes |

The core ontology and CQ results remain the separately dated 22 November baseline: 4,655 source-reconciliation checks, consistent OWL 2 DL ontology validation, and all 78 CQ queries plus four controls passed. They were not rerun for this catalogue-only refresh.

The workflow checks exercise new resource IDs, status gating, stable identifiers, row/column movement, updates, withdrawal, repeated builds, interrupted publication, integrity failures, matching and a synthetic draft intervention. Two additional tests verify preservation of curation metadata in JSON/RDF and rejection of missing curation details. Tests use a fixed metadata fixture so that later additions to the live collection do not invalidate the regression baseline. Expected selection results are independently specified resource IDs. These are technical checks; they do not establish educational effectiveness or clinical validation.

See [workflow results](WORKFLOW_CHECKS.md), [machine-readable checks](workflow-checks.json), [educational OWL report](owlapi-report.json), [CQ report](../../validation/reports/CQ_VALIDATION_REPORT.md) and [ontology validation](../../serialisation/validation/).

## Adding and maintaining resources

Save the updated worksheet and rerun the build. Every new approved/complete Resource ID is considered automatically, including for applicable activity templates. Changed records retain their IRIs; withdrawn entries disappear from the current release. Validated snapshots and a single current pointer support reproducibility and rollback. Consumers refresh from the current pointer or replace the active named graphs; appending historical snapshots would retain withdrawn data.

The next integration step is for consuming Health Hub services to call the selection function with identified needs and preferences, present the returned metadata/links, and record use and feedback. Full-text ingestion requires an independently established permitted use. Ongoing curation can prioritise gaps in language, topic, format or support needs and revise activities using participant and professional feedback.
