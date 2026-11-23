# Release source snapshots

These four input snapshots are included with the package. `manifest.json` records their byte counts and SHA-256 hashes. The bundled inputs support generation and reconciliation independently of the original development environment. The resource workbook contains the released curation data; unused working tabs are not required by the tools.

Original specifications, competency-question records and curation annotations are CC BY 4.0 under [the repository licence scope](../LICENSE.md). Descriptions of external standards and resources do not relicense their underlying content; see [third-party notices](../THIRD_PARTY_NOTICES.md).

| Snapshot                                                      | Used by                                                            |
| ------------------------------------------------------------- | ------------------------------------------------------------------ |
| `icareonto_review_workbook_v221126.xlsx`                    | Ontology Serialiser and source reconciliation                      |
| `icareonto_alignment_mapping_workbook_v301026_4.xlsx`       | Approved semantic alignment generation                             |
| `icareonto_final_consolidated_competency_questions_v5.xlsx` | Ontology term coverage and canonical CQ register                   |
| `MAYA_consolidated_educational_resources.xlsx`             | Educational catalogue publication from the Release resources sheet |

The educational workbook uses a stable filename as curation continues. Its
SHA-256 hash, Git history and catalogue release identifier identify the exact
input snapshot. The public workbook contains only the curated, annotated,
approved and complete release entries and their field guide; the full discovery
inventory is not a runtime dependency.
