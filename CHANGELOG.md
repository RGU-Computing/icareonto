## [Unreleased]

### Changed

- Expanded the curated educational catalogue from 31 to 41 resources across
  six languages, including information appraisal, symptom self-monitoring,
  smoking cessation and further survivorship language editions.
- Updated the topic annotations of the existing Portuguese and Polish
  survivorship resources and refreshed catalogue exports and examples.
- Adopted the stable source filename `MAYA_consolidated_educational_resources.xlsx`
  and the worksheet headings `Curated by`, `Curation date` and `Applicability notes`.
- Updated catalogue profile 1.2 to use `curated_by` and `curation_date` in JSON
  and `curatedBy` and `curatedOn` in RDF, with corresponding validation shapes
  and tests. The previous curation headings and export fields are not supported.

## [0.2.0] – 2026-11-22

### Added

- Ontology-carried value-format constraints and reusable SHACL shapes for
  calendar-date and duration strings, with regression checks for real dates,
  leap years, malformed durations, legacy typed literals and lossless exports.
- A fictional participant input exercising the date and all three duration
  properties, plus representative requirement-to-ontology/query traceability.
- CC BY 4.0 licensing for original ontology content and catalogue metadata,
  MIT licensing for supporting software, full licence texts, attribution
  guidance and third-party notices.
- Persistent licence and attribution annotations in generated ontology
  headers, with checks protecting the external-vocabulary exclusions.
- Copyright notices identifying Robert Gordon University and contributing
  MAYA consortium partners for their respective contributions, with a
  separate development and contributor acknowledgement.

### Changed

- Rebuilt from `icareonto_review_workbook_v221126.xlsx`, with technical
  version 0.2.0 in ontology headers and version IRIs. Review status remains
  Draft toward the initial iCARE Onto Version 1 project baseline.
- Simplified the ontology display label to `iCARE Onto` and removed the
  release-review sentence from its descriptive comment; technical version
  metadata remains in the dedicated OWL annotations.
- Changed `diagnosisDate`, `intervalDuration`, `estimatedCompletionTime` and
  `serviceUseDuration` to validated `xsd:string` representations. Dates retain
  day precision; no time or timezone is invented. Existing JSON values can
  be regenerated; externally stored RDF needs the documented datatype migration.
- Preserved both workbook-specified parent classes for `MeasurementDevice`:
  `MeasurementInstrument` and `Device`, with the revised definition.
- Refreshed dependent source manifests, graph examples, catalogue fingerprints,
  pilot-mapping fixtures and validation evidence for the current ontology.
- Expanded the reviewed educational catalogue from 16 to 31 resources,
  adding German, Italian, Polish and Portuguese coverage alongside
  Spanish and English.
- Refreshed catalogue exports, source integrity metadata, the selected
  educational example and associated validation reports.
- Removed the unapproved row from the public source worksheet and
  refreshed curation provenance after clearing a completed resource to-do;
  the 31 published resources and their coverage are unchanged.
- Preserved licence and attribution metadata while refreshing ontology
  fingerprints and dependent catalogue and demonstration assets.

## [0.1.0-draft] – 2026-11-06

### Added

- Modular OWL ontology covering 17 interconnected knowledge areas.
- Ontology Serialiser for generating and validating the ontology.
- KG Instantiator for creating and refreshing pilot and participant
  knowledge graphs, with Turtle and JSON-LD exports.
- Pilot Mapper for semantic ranking, reviewed concept mappings
  and graph-coverage reporting.
- Education Resource Selector with 16 approved resources and
  three draft learning-activity templates.
- Executable tests for all 78 competency questions, four additional
  controls and supporting workflow checks.
- Source snapshots, input templates, examples and validation reports.

### Changed

- Replaced the earlier ontology layout with the modular ontology
  and four supporting tools, preserving repository history.
- Added portable documentation and local import resolution.

### Known limitations

- Draft release under review towards iCARE Onto Version 1.
- A date-datatype compatibility finding affects OWL 2 DL conformance
  of the fuller participant example; details accompany the validation.
- Learning-activity templates require review before participant use.



## [0.1.0] – 2025-12-22

### Added

- Initial modular structure (user, clinical, lifestyle, devices)
- Core survivorship concepts for AYA care

### Notes

- Initial draft release; breaking changes expected.
