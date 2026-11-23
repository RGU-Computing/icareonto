# iCARE Onto 1.0.0

Open **`icareonto.ttl`** in Protégé Desktop using **File → Open**. Keep this folder and its subfolders together. The adjacent `catalog-v001.xml` maps imports to local files, so the package can be loaded offline.

This is **version `1.0.0`**, the initial published **iCARE Onto Version 1** baseline. The ontology provides the semantic foundation for AYA cancer survivorship, cardiovascular health, personalised care, educational support and conversational interaction within the MAYA iCARE Health Hub.

The ontology files can be used independently of the development materials. They contain no workbook filenames, worksheet/cell references or mapping-register identifiers. Build provenance and requirements traceability are retained separately in `validation/`. Each ontology header records its technical version and publication status. Publication does not change individual term-review statuses or establish clinical validation; clinical domain review will be completed before the relevant participant-facing pilot use.

## Contents

| Location                    | Content                                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `icareonto.ttl`           | Main ontology importing the 17 modules and approved alignments                                                            |
| `modules/`                | One Turtle file per module, containing its classes, properties, controlled values and concept schemes                     |
| `alignments/approved.ttl` | The three approved semantic alignments, with semantic rationale and external source links                                 |
| `imports/`                | Source-derived SKOS and PROV-O reference subsets, resource metadata declarations, and unchanged official source downloads |
| `catalog-v001.xml`        | Portable local import resolution                                                                                          |
| `scripts/`                | Workbook reader, generator and validators                                                                                 |
| `validation/`             | Build provenance, source reconciliation, term inventory, import map, CQ term checks and OWLAPI/HermiT results             |

In Protégé, inspect **Classes**, **Object properties**, **Data properties**, and **Individuals**. Controlled values are individuals of their module-defined controlled classes and of `skos:Concept`. The 62 concept schemes are also individuals. Imports introduce additional external entities, so Protégé's complete counts can be larger than the local schema counts below. The selected active ontology and imported-entity display settings affect the views.

If an import appears unresolved, select the **local file** option in Protégé's import resolver and select the matching file shown in `catalog-v001.xml`. Do not substitute an online ontology simply because a local module IRI is an HTTP URL. The HTTP entity and ontology IRIs are preserved identifiers; web hosting is not required for this package.

## Coverage and development inputs

- **Ontology source:** `../sources/icareonto_review_workbook_v221126.xlsx`.
- **Approved alignments:** `../sources/icareonto_alignment_mapping_workbook_v301026_4.xlsx`, `Alignment Register` sheet.
- **Competency questions:** `../sources/icareonto_final_consolidated_competency_questions_v5.xlsx`.
- **Output:** 17 modules, 283 local classes, 284 local object properties, 137 local data properties, 304 controlled values and 62 concept schemes.
- **CQ checks:** All 78 consolidated CQs have recognised path terms. No participant instances or executed CQ answers are included.

In the ontology source workbook, the controlled vocabulary detail sheet is the source of value definitions for controlled vocabulary entries and its Module column is used to determine ontology module ownership.

## Modelling decisions (using the ontology source workbook)

1. Existing entity IRIs are preserved. For example, all modules share the existing entity namespace `http://maya-project.eu/icareonto/`; the module worksheet names do not create new entity namespaces.
2. Stable module ontology and entity IRIs are preserved. Version IRIs identify `1.0.0`, separately from those stable IRIs. Development-source revision numbers do not define the ontology version.
3. Named parent relationships become `rdfs:subClassOf`; semicolon-separated parent lists preserve each explicitly named parent. Object and data properties retain their source domains, ranges and XSD datatypes. No cardinalities, inverse relations, closed enumerations or disjointness axioms are inferred from descriptions.
4. Entity definitions use `skos:definition` once. `rdfs:comment` is reserved for distinct explanatory context, such as ontology descriptions and alignment rationale. Labels and alternative labels are preserved. The `metadata#releaseStatus` annotation records publication status; the separate `metadata#reviewStatus` annotation preserves the source review statuses of controlled concepts and semantic alignments. Development provenance is kept outside the ontology: entity source cells in `validation/entity-manifest.tsv`, value source cells in `validation/controlled-value-provenance.tsv`, alignment-register IDs in `validation/alignment-trace.tsv`, and source filenames/hashes in `validation/build-report.json`.
5. Vocabulary categories remain OWL classes subclassing `skos:Concept`. Their values are named individuals, with labels, definitions, scheme membership, source status and explicit broader relationships. The schemes are not OWL classes. Lists are not treated as exhaustive or pairwise-distinct unless future modelling explicitly requires that.
6. Only mappings marked **Approved** in the primary Alignment Register are emitted as semantic axioms. The three current mappings connect Agent, ParticipantKnowledgeGraph and ConsentRecord to PROV-O. Proposed mappings, coding recommendations and all FHIR transformations remain in the workbook. The excluded rows are listed in `validation/excluded-alignments.tsv`.
7. External reference subsets preserve selected named axioms and annotations from the official W3C sources. The SKOS subset excludes unused collection/list constructs. The PROV-O subset includes Agent, Entity, Collection and InstantaneousEvent, their relevant hierarchy and disjointness. They have explicit local ontology IRIs and are labelled as subsets. The full sources are retained unchanged in `imports/skos.rdf` and `imports/prov-o.ttl` but are not imported. This avoids OWL 2 DL profile issues in unrelated full-source constructs and ontology metadata.
8. Dublin Core resource metadata predicates are declared as OWL annotation properties in `imports/metadata.ttl`. They accept the appropriate literal or IRI annotation values. In particular, `dcterms:language` supports language metadata and `dcterms:source` can link an instrument/resource to its evidence source. These declarations are a local usage convention, not a complete import of DCMI or new domain relations.

## Validation results

The iCARE Onto package was checked using RDFLib and the OWLAPI 4.5.29/HermiT 1.4.3.456 libraries bundled with Protégé:

- All generated RDF files parse, and their local imports resolve.
- The OWLAPI imports closure contains 22 ontology documents.
- The local OWL signature contains 283 classes, 284 object properties, 137 data properties and 366 named individuals (304 values plus 62 schemes).
- The complete packaged imports closure passes the OWL 2 DL profile check with **zero violations**.
- HermiT reports the ontology **consistent**, with **zero unsatisfiable named classes**, using its default datatype settings.
- Independent source reconciliation checks the saved declarations, labels, definitions, data ranges, vocabulary entries, ownership, catalogue targets and RDF/XML round-trips.

Calendar dates and durations use `xsd:string`, preserving the supplied precision without introducing a time or timezone. `diagnosisDate` requires a real `YYYY-MM-DD` calendar date; `intervalDuration`, `estimatedCompletionTime` and `serviceUseDuration` require ISO duration expressions such as `P7D` or `PT30M`. The `metadata#valueFormat` and `metadata#valuePattern` annotations identify these constraints in the deployed ontology. The KG Instantiator applies input and SHACL validation, including Gregorian leap-year rules, and exports reusable shapes in `instantiation/reference/value-formats.shacl.ttl`. OWL reasoning treats these values as strings; calendar/duration calculations belong in consuming applications. See [the datatype policy and migration guide](../instantiation/reports/DATATYPE_COMPATIBILITY.md). OWL domains and ranges express inference, not form-validation constraints.

## Regeneration

From the repository root, create and activate a Python environment as described in the [installation guide](../README.md). The serialiser dependencies and build commands are:

```bash
python -m pip install -r serialisation/scripts/requirements.txt
python serialisation/scripts/serialise_ontology.py
python serialisation/scripts/check_outputs.py
```

The generator is offline once RDFLib is installed and the bundled import source files are present. It overwrites generated files within `serialisation/`, so regenerate from the workbook rather than maintaining independent edits in Turtle. Update the source workbook or generator conventions first, then rebuild.

The optional OWLAPI/HermiT launcher requires a compatible Protégé application bundle containing Java 11 `jjs`. Its location is supplied explicitly; the results are written to `serialisation/validation/owlapi-report.json`:

```bash
python serialisation/scripts/validate_with_protege.py --protege-app /path/to/Protege.app
```

`ICARE_PROTEGE_APP` can supply the bundle location instead of the command-line option. This launcher supports a bundle with a `Contents/` directory and the required Java runtime; it does not support all operating-system distributions or newer Java runtimes. For other installations, profile and reasoner checks can be run in Protégé or with another compatible OWLAPI validation tool.

The generator also accepts `--ontology`, `--alignments`, `--cqs`, `--output`, `--version` and `--release`. `--version` controls ontology version metadata and version IRIs; `--release` records the build date in the development report. For a separate output location, first copy the two unchanged external source files into that location's `imports/` directory.

## External source provenance

Official W3C source files retrieved on 30 October 2026:

- SKOS: https://www.w3.org/2009/08/skos-reference/skos.rdf
- PROV-O: https://www.w3.org/ns/prov-o.ttl

Reference documentation:

- SKOS: https://www.w3.org/TR/skos-reference/
- PROV-O: https://www.w3.org/TR/prov-o/
- Dublin Core Terms: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- Protégé local imports: https://protegewiki.stanford.edu/wiki/Importing_Ontologies_in_P41

Original iCARE Onto ontology content is licensed under CC BY 4.0; the generator and checking software are MIT-licensed. Generated headers record `dcterms:license`, `dcterms:creator`, `dcterms:contributor` and `dcterms:rights` for the original ontology, modules, metadata vocabulary and alignment assertions. Robert Gordon University is identified as creator, MAYA consortium partners are acknowledged as contributors, and the copyright notice concerns their respective contributions. Rebuilding preserves these annotations. See [licensing and attribution](../LICENSE.md).

The original external downloads retain their copyright and licensing notices. The source-derived subset files retain relevant term documentation and identify their source; they must not be represented as the full W3C ontologies or relicensed as original iCARE Onto material. See [third-party notices](../THIRD_PARTY_NOTICES.md).
