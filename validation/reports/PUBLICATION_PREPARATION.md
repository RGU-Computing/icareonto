# Publication package validation

Refreshed against technical ontology version 0.2.0 on 22 November 2026 using the repository's bundled inputs, fixtures and dependency specifications. A clean temporary ontology rebuild was also compared with the distributed graphs.

| Activity | Result |
|---|---|
| Release source snapshots | Four bundled workbooks verified against the source manifest |
| Source-to-ontology reconciliation | 4,655 checks passed |
| Ontology rebuild using bundled inputs | 22 rebuilt ontology graphs are semantically identical to the distributed graphs |
| KG initialisation workflow | 49 checks passed |
| Fillable-template and refresh interface | 18 checks passed |
| Grouped clinical records, JSON-LD and calendar/duration validation | 38 checks passed |
| Saved pilot-ranking workflow | 31 checks passed against regenerated, current-ontology fixtures |
| Live encoder and operational mapping interface | 22 checks passed with a separately configured local encoder |
| Educational catalogue workflow | 41 checks passed |
| Canonical competency questions | All 78 expected answers matched; four controls passed |
| Shared demonstration smoke checks | 17 checks passed |
| Public check runner with live encoder enabled | All ten commands passed; 199 workflow/interface checks across the six tool suites |
| Curated and annotated educational catalogue | 31 eligible resources; one current release package retained |
| Local import portability | Ontology, shared fixtures, educational catalogue and selected demo resolve within this repository |
| Ontology OWLAPI/HermiT | 22 documents; zero profile violations; consistent; no unsatisfiable named classes |
| CQ fixture OWLAPI/HermiT | 24 documents; zero profile violations; consistent; no unsatisfiable named classes |
| Educational example OWLAPI/HermiT | 26 documents; zero profile violations; consistent; no unsatisfiable named classes |
| Full clinical and populated date/duration examples OWLAPI/HermiT | 26 documents; zero profile violations; consistent; no unsatisfiable named classes |

The earlier populated-date profile finding is resolved by the source-model change to validated strings for the date and all three duration properties. The new tests include valid/invalid calendar dates, century/leap-year exceptions, malformed durations, legacy typed RDF rejection and unchanged outputs after a failed update. See [the tested policy and migration guide](../../instantiation/reports/DATATYPE_COMPATIBILITY.md) and [populated OWL results](../../instantiation/reports/temporal-owlapi-report.json). These technical results do not establish clinical/predictive validity.

The fixed pilot-ranking baseline was recomputed with a fresh local encoder run against the packaged ontology; stale fingerprints were not bypassed. The test baseline is distributed without embedding caches or model weights. Source model/encoder provenance is retained in `pilot-mapping/tests/fixtures/rankings.json`. Reusing fictional demonstration decisions does not constitute new operational approval.

The distributed assets include a current resource catalogue and a compact fictional educational example. Runtime outputs, histories and caches are excluded by the repository's ignore rules.

The core checks can be reproduced from the repository root with `python scripts/run_checks.py`. Live encoder integration is enabled with `--with-encoder` and the documented environment settings.
