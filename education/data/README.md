# Curated catalogue snapshot

`catalogue/current.json` identifies the single complete catalogue release distributed with this package. It contains metadata for **41 approved and complete resources** across Spanish (11), English (11), German (6), Italian (5), Polish (4) and Portuguese (4). The catalogue contains source links and annotations, not copies of provider materials. Its input is `sources/MAYA_consolidated_educational_resources.xlsx`.

Catalogue profile `1.2` records curation using `curated_by`, `curation_date` and `applicability_notes` in JSON and the corresponding `curatedBy`, `curatedOn` and `applicabilityNotes` RDF annotations. Catalogue approval does not establish clinical suitability for every participant or site.

Use it directly without the source workbook:

```bash
python education/scripts/education_resources.py select --output education/data/catalogue --request education/examples/spanish-cardiovascular.json
```

For curation changes, build into ignored `education/generated/`, test and inspect the change report. Then prepare a fresh publication snapshot and update this directory deliberately. Keep the release folder, pointer, manifest and validation files together because the loader verifies the complete package. Earlier published snapshots remain recoverable through Git history/tags rather than accumulating every local build here.
