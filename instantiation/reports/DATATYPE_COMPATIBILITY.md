# Calendar-date and duration compatibility in version 0.2.0

The earlier populated diagnosis-date profile finding is resolved in ontology 0.2.0. The authoritative source specifies strings for calendar dates and durations, and the regenerated ontology carries explicit value-format annotations. This preserves the supplied precision without adding an unknown time or timezone. The ontology's review status remains Draft toward the initial iCARE Onto Version 1 project baseline.

## Representation and validation

| Property | Module | RDF datatype and accepted representation |
|---|---|---|
| `diagnosisDate` | cancer-history | `xsd:string`; an existing Gregorian calendar date in `YYYY-MM-DD` format, years 0001–9999 |
| `intervalDuration` | core | `xsd:string`; an ISO duration expression, for example `P7D` |
| `estimatedCompletionTime` | knowledge-resource | `xsd:string`; an ISO duration expression, for example `PT10M` |
| `serviceUseDuration` | healthhub-service | `xsd:string`; an ISO duration expression, for example `PT15M` |

The deployed `metadata#valueFormat` and `metadata#valuePattern` annotations identify each format. The JSON input reference includes them, and the input validator reads them from the ontology. SHACL shapes generated from the same annotations also check direct RDF imports. Calendar validity is checked using Python's date parser and, independently, SHACL-SPARQL calendar arithmetic, including Gregorian century/leap-year rules. A spelling pattern alone is not considered sufficient calendar validation.

The duration profile accepts ordered integer year/month/day components and hour/minute/second components, with fractional seconds; a whole-week expression such as `P2W` is also accepted. A leading minus sign remains accepted, as in the earlier lexical duration policy. Empty components, mixed week/calendar expressions, decimal commas, fractional non-second components and free text are rejected. Applications may impose narrower nonnegative or fixed-unit business rules when required. Months and years are retained as calendar units, not silently converted to a fixed number of seconds.

These are string-valued data properties in OWL. The format annotations are descriptive metadata; input and SHACL checks enforce the formats. Date arithmetic, temporal ordering and duration calculations belong to consuming applications. Real instants continue to use the ontology's existing `xsd:dateTime` properties.

## Checked evidence

The validation run on 22 November 2026 used the full clinical participant example and [a dedicated temporal input](../examples/participant-es-temporal.json), together with their pilot. The latter populates the calendar date and all three duration properties. Its seven-day interval has explicitly supplied start and end timepoints.

| Check | Result |
|---|---|
| Input structure, ontology terms, types and SHACL | Pass |
| Valid calendar dates, invalid dates and leap-year exceptions | Pass |
| All three duration formats and malformed-value rejection | Pass |
| Legacy `xsd:date` / `xsd:duration` RDF literal rejection | Pass |
| Failed duration update leaves existing outputs unchanged | Pass |
| Exact strings and datatypes through Turtle / JSON-LD round-trip | Pass |
| Named-graph JSON-LD / TriG equivalence | Pass |
| OWLAPI, populated clinical and temporal imports closure | 26 documents; zero OWL 2 DL profile violations |
| HermiT, same closure | Consistent; zero unsatisfiable named classes |

See [the 38 grouped-record checks](SECTION_CHECKS.md), [machine-readable results](section-checks.json) and [the populated examples' OWLAPI/HermiT report](temporal-owlapi-report.json). These are technical results for fictional inputs, not clinical validation.

## Reproduction

Use a fresh output directory, generating the shared pilot first. The directory below is an example; choose another if it already contains a different deployment.

```bash
python instantiation/kg-instantiator.py pilot --input instantiation/examples/pilot-es-demo.json --output instantiation/generated/temporal-check
python instantiation/kg-instantiator.py participant --input instantiation/examples/participant-es-full.json --output instantiation/generated/temporal-check
python instantiation/kg-instantiator.py participant --input instantiation/examples/participant-es-temporal.json --output instantiation/generated/temporal-check
python instantiation/scripts/check_sections.py
python serialisation/scripts/validate_with_protege.py --protege-app /path/to/Protege.app --output instantiation/generated/temporal-check --ontology-file instantiation/generated/temporal-check/dataset.ttl --report instantiation/generated/temporal-check/validation/owlapi-report.json
```

[Reusable SHACL shapes](../reference/value-formats.shacl.ttl) can also be applied to RDF without using the JSON input reader. Regenerate these and the input reference with `python instantiation/scripts/export_input_reference.py` after a source-model change.

## Migrating earlier data

1. Retain a versioned backup of existing graphs and their source records.
2. Keep existing date and duration values in JSON. The values are already strings; no time needs adding. Regenerate pilot records first and then all affected participants into a fresh output deployment, retaining the same identifiers and base IRI.
3. Validate the regenerated graphs and compare their identifiers, relationships and date/duration lexical values before adopting them. Do not combine unmigrated owner graphs with the new ontology: the generator validates the complete managed graph set and will reject old typed values.
4. If only RDF is available, explicitly migrate these four predicates from `xsd:date` / `xsd:duration` literals to validated `xsd:string` values. Check each original value first. Values outside this profile, such as timezone-qualified dates, need an explicit conversion decision rather than silent truncation. Preserve the original information in the migration record.
5. Refresh consuming-service datatype assumptions, ontology-dependent mappings and educational catalogue fingerprints. Refresh current graphs while retaining historical releases as historical records.

All four property IRIs remain unchanged. Archived 0.1.0-draft graphs retain their original datatypes and version context; this policy does not rewrite history or suppress a profile result.

Standards: [OWL 2 datatype maps](https://www.w3.org/TR/owl2-syntax/#Datatype_Maps) and [SHACL string constraints](https://www.w3.org/TR/shacl/#PatternConstraintComponent).
