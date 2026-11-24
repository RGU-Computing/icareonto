"""Ontology-driven records for the grouped pilot/participant JSON interface.

The input vocabulary is read from the deployed ontology, so classes and
properties are not limited to a manually curated list of clinical fields.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.parse import urlsplit

from rdflib import BNode, Dataset, Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef, XSD
from rdflib.namespace import DCTERMS, SKOS

IC = "https://w3id.org/icareonto/"
META = Namespace(IC + "metadata#")
SH = Namespace("http://www.w3.org/ns/shacl#")
GROUPS = {
    "clinical_profile": "clinical-profile", "cancer_history": "cancer-history",
    "measurements": "measurement-biomarker", "cv_risk": "cv-risk",
    "care_plans": "intervention-careplan", "exercise": "exercise",
    "nutrition": "nutrition", "lifestyle": "lifestyle-behaviour",
    "social_context": "social-context", "education": "knowledge-resource",
    "dialogue": "dialogue", "agents": "agent", "digital_services": "healthhub-service",
    "governance": "provenance-governance", "person_context": "person-role",
    "pilot_context": "pilot", "common": "core",
}


class SectionError(ValueError):
    pass


def term(name, schema, category):
    node = URIRef(name if name.startswith(IC) else IC + name)
    if not str(node).startswith(IC) or (node, RDF.type, category) not in schema:
        raise SectionError(f"Unknown ontology {str(category).split('#')[-1]}: {name}")
    return node


def literal(value, datatype, formats, value_format=None, pattern=None):
    """Require values compatible with the ontology's declared XSD datatype."""
    valid = False
    if datatype == XSD.string:
        valid = isinstance(value, str)
    elif datatype == XSD.decimal:
        if not isinstance(value, bool) and isinstance(value, (str, int, float)):
            try:
                numeric = Decimal(str(value))
                valid = numeric.is_finite() and (not isinstance(value, str) or re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value) is not None)
                if valid:
                    value = format(numeric, "f")
            except InvalidOperation:
                pass
    elif datatype in (XSD.nonNegativeInteger, XSD.positiveInteger):
        valid = isinstance(value, int) and not isinstance(value, bool) and value >= (1 if datatype == XSD.positiveInteger else 0)
    elif datatype == XSD.boolean:
        valid = isinstance(value, bool)
    elif datatype == XSD.dateTime:
        valid = isinstance(value, str) and formats.conforms(value, "date-time")
    elif datatype == XSD.date:
        if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            try:
                date.fromisoformat(value)
                valid = True
            except ValueError:
                pass
    elif datatype == XSD.language:
        valid = isinstance(value, str) and re.fullmatch(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", value) is not None
    elif datatype == XSD.anyURI:
        if isinstance(value, str):
            try:
                parsed = urlsplit(value)
                valid = bool(parsed.scheme and (parsed.netloc or parsed.scheme == "urn" and parsed.path)) and not re.search(r"\s|[<>]", value)
            except ValueError:
                pass
    elif datatype == XSD.duration:
        valid = isinstance(value, str) and re.fullmatch(r"-?P(?=\d|T\d)(?:\d+Y)?(?:\d+M)?(?:\d+D)?(?:T(?=\d)(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?", value) is not None
    # String ranges still carry semantic format constraints in the ontology.
    # Check real calendar dates, not just the YYYY-MM-DD spelling.
    if value_format is not None:
        valid = valid and datatype == XSD.string and isinstance(value, str) and pattern is not None
        valid = valid and re.fullmatch(pattern, value) is not None
        if value_format == "iso-calendar-date" and valid:
            try:
                date.fromisoformat(value)
            except ValueError:
                valid = False
        elif value_format not in ("iso-calendar-date", "iso-duration"):
            valid = False
    if not valid:
        suffix = f" and required format {value_format}" if value_format else ""
        raise SectionError(f"Value {value!r} is incompatible with ontology datatype {datatype}{suffix}")
    result = Literal(value, datatype=datatype)
    if result.value is None:
        raise SectionError(f"Invalid datatype value: {value!r} ({datatype})")
    return result


def add_sections(builder, data, schema, kind, formats):
    """Create all record identities first, then resolve cross-section references."""
    sections = data.get("sections", {})
    base = builder.base
    if kind == "participant":
        root = base + "people/" + data["participant_id"]
        aliases = {
            "$person": URIRef(root), "$site": URIRef(base + "sites/" + data["site_id"]),
            "$study": URIRef(base + "studies/" + data["study_id"]),
            "$enrolment": URIRef(root + "/enrolments/" + data["enrolment"]["id"]),
            "$participant_graph": URIRef(root + "/knowledge-graph"),
            "$source": URIRef(root + "/seed-source"), "$recorded_at": URIRef(root + "/seed-recorded-at"),
        }
    else:
        root = base + "sites/" + data["site"]["id"]
        aliases = {"$site": URIRef(root), "$study": URIRef(base + "studies/" + data["study"]["id"]), "$locale": URIRef(root + "/locale")}
    aliases["$graph"] = builder.graph_iri
    # All IDs are owner-scoped; references across sections remain stable when
    # records move between groups. Group names organise input, not RDF identity.
    records = []
    for group, section in sections.items():
        for record in section.get("records", []):
            identifier = record["id"]
            if identifier in aliases:
                raise SectionError(f"Duplicate section record ID: {identifier}")
            node = URIRef(root + "/records/" + identifier)
            aliases[identifier] = node
            classes = record["type"] if isinstance(record["type"], list) else [record["type"]]
            for cls in classes:
                builder.g.add((node, RDF.type, term(cls, schema, OWL.Class)))
            builder.g.add((node, RDF.type, OWL.NamedIndividual))
            if record.get("label"):
                builder.g.add((node, RDFS.label, Literal(record["label"])))
            if record.get("source"):
                builder.g.add((node, DCTERMS.source, Literal(record["source"])))
            if record.get("recorded_at"):
                builder.g.add((node, DCTERMS.modified, literal(record["recorded_at"], XSD.dateTime, formats)))
            records.append((node, record))

    def reference(value):
        if not isinstance(value, dict):
            raise SectionError("An object property requires {ref: record ID} or {term: ontology value}")
        if set(value) == {"ref"}:
            if value["ref"] not in aliases:
                raise SectionError(f"Unresolved section reference: {value['ref']}")
            return aliases[value["ref"]]
        if set(value) == {"term"}:
            return term(value["term"], schema, OWL.NamedIndividual)
        raise SectionError("An object property requires exactly one ref or term")

    def assertion(subject, name, value):
        node = URIRef(name if name.startswith(IC) else IC + name)
        is_object = (node, RDF.type, OWL.ObjectProperty) in schema
        is_data = (node, RDF.type, OWL.DatatypeProperty) in schema
        if not str(node).startswith(IC) or not (is_object or is_data):
            raise SectionError(f"Unknown ontology property: {name}")
        # Validate property names even when a known property's value is unknown.
        if value is None:
            return
        values = value if isinstance(value, list) else [value]
        for supplied in values:
            if supplied is None:
                continue
            if is_object:
                target = reference(supplied)
            else:
                ranges = list(schema.objects(node, RDFS.range))
                if len(ranges) != 1:
                    raise SectionError(f"Expected one declared datatype for {name}")
                value_format, pattern = property_format(schema, node)
                target = literal(supplied, ranges[0], formats, value_format, pattern)
            builder.g.add((subject, node, target))

    for node, record in records:
        for name, value in record.get("properties", {}).items():
            assertion(node, name, value)
    for section in sections.values():
        for link in section.get("links", []):
            if link["subject"] not in aliases:
                raise SectionError(f"Unresolved section subject: {link['subject']}")
            assertion(aliases[link["subject"]], link["property"], link["object"])


def property_format(schema, prop):
    """Read the deployed constraint so input validation follows the ontology."""
    names, patterns = list(schema.objects(prop, META.valueFormat)), list(schema.objects(prop, META.valuePattern))
    if not names and not patterns:
        return None, None
    if len(names) != 1 or len(patterns) != 1 or str(names[0]) not in ("iso-calendar-date", "iso-duration"):
        raise SectionError(f"Unsupported or incomplete value-format annotation: {prop}")
    if set(schema.objects(prop, RDFS.range)) != {XSD.string}:
        raise SectionError(f"Formatted property must have xsd:string range: {prop}")
    return str(names[0]), str(patterns[0])


def value_shapes(schema):
    """Build portable SHACL constraints for the ontology's formatted strings.

    Calendar arithmetic is deliberately independent of Python's date parser;
    direct RDF imports are checked too, including leap-year exceptions.
    """
    shapes = Graph()
    shapes.bind("sh", SH)
    shapes.bind("xsd", XSD)
    for prop in sorted(set(schema.subjects(META.valueFormat, None)), key=str):
        name, pattern = property_format(schema, prop)
        shape = URIRef(IC + "shapes/" + str(prop).removeprefix(IC) + "Format")
        for pred, obj in [(RDF.type, SH.PropertyShape), (SH.targetSubjectsOf, prop),
                          (SH.path, prop), (SH.datatype, XSD.string),
                          (SH.pattern, Literal(pattern)),
                          (SH.message, Literal(f"Expected a valid {name} string."))]:
            shapes.add((shape, pred, obj))
        # SPARQL regex '$' can match before a final newline. An independent
        # no-whitespace constraint keeps RDF and Python full-match behaviour aligned.
        whitespace = BNode()
        shapes.add((shape, SH["not"], whitespace))
        shapes.add((whitespace, SH.pattern, Literal(r"\s")))
        if name == "iso-calendar-date":
            check = BNode()
            shapes.add((shape, SH.sparql, check))
            shapes.add((check, SH.message, Literal("Calendar date must exist in years 0001–9999.")))
            query = """PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT $this ?value WHERE {
  $this <PROPERTY> ?value .
  BIND(xsd:integer(SUBSTR(STR(?value), 1, 4)) AS ?year)
  BIND(xsd:integer(SUBSTR(STR(?value), 6, 2)) AS ?month)
  BIND(xsd:integer(SUBSTR(STR(?value), 9, 2)) AS ?day)
  BIND((?year / 4 = FLOOR(?year / 4)) &&
       ((?year / 100 != FLOOR(?year / 100)) || (?year / 400 = FLOOR(?year / 400))) AS ?leap)
  BIND(IF(?month = 2, IF(?leap, 29, 28), IF(?month IN (4, 6, 9, 11), 30, 31)) AS ?days)
  FILTER(?year < 1 || ?day > ?days)
}""".replace("PROPERTY", str(prop))
            shapes.add((check, SH.select, Literal(query)))
    return shapes


def jsonld_context(schema, predicates=None):
    context = {"@version": 1.1, "@vocab": IC, "icare": IC, "xsd": str(XSD),
               "owl": str(OWL), "rdfs": str(RDFS), "dcterms": str(DCTERMS),
               "id": "@id", "type": "@type", "label": str(RDFS.label)}
    for node in schema.subjects(RDF.type, OWL.ObjectProperty):
        if str(node).startswith(IC) and (predicates is None or node in predicates):
            context[str(node).removeprefix(IC)] = {"@id": str(node), "@type": "@id"}
    for node in schema.subjects(RDF.type, OWL.DatatypeProperty):
        if str(node).startswith(IC) and (predicates is None or node in predicates):
            ranges = list(schema.objects(node, RDFS.range))
            if len(ranges) == 1:
                context[str(node).removeprefix(IC)] = {"@id": str(node), "@type": str(ranges[0])}
    return context


def jsonld_bytes(graph, schema):
    """Export the same RDF with an inline context and deterministic array order."""
    predicates = {p for _, p, _, _ in graph.quads()} if isinstance(graph, Dataset) else set(graph.predicates())
    value = json.loads(graph.serialize(format="json-ld", context=jsonld_context(schema, predicates), auto_compact=True, use_native_types=False))

    def ordered(item, key=None):
        if isinstance(item, dict):
            return {k: ordered(v, k) for k, v in item.items()}
        if isinstance(item, list):
            result = [ordered(v) for v in item]
            return result if key == "@list" else sorted(result, key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
        return item
    return (json.dumps(ordered(value), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def trig_bytes(dataset):
    """Use explicit RDF terms and stable ordering for repeatable named datasets."""
    blocks = []
    for graph in sorted((g for g in dataset.graphs() if len(g)), key=lambda g: str(g.identifier)):
        triples = sorted(f"    {subject.n3()} {predicate.n3()} {value.n3()} ." for subject, predicate, value in graph)
        blocks.append(graph.identifier.n3() + " {\n" + "\n".join(triples) + "\n}")
    return ("\n\n".join(blocks) + "\n").encode()


def ontology_reference(schema):
    """Expose the deployed field vocabulary to data providers and form builders."""
    def local(node):
        return str(node).removeprefix(IC)
    classes = []
    for node in sorted(set(schema.subjects(RDF.type, OWL.Class)), key=str):
        if str(node).startswith(IC):
            classes.append({"name": local(node), "iri": str(node), "label": str(next(schema.objects(node, RDFS.label), "")),
                            "definition": str(next(schema.objects(node, SKOS.definition), "")),
                            "parents": [local(v) for v in schema.objects(node, RDFS.subClassOf) if isinstance(v, URIRef)]})
    properties = []
    for category in (OWL.ObjectProperty, OWL.DatatypeProperty):
        for node in sorted(set(schema.subjects(RDF.type, category)), key=str):
            if str(node).startswith(IC):
                entry = {"name": local(node), "iri": str(node), "kind": "object" if category == OWL.ObjectProperty else "data",
                                   "label": str(next(schema.objects(node, RDFS.label), "")),
                                   "definition": str(next(schema.objects(node, SKOS.definition), "")),
                                   "domains": [local(v) for v in schema.objects(node, RDFS.domain)],
                                   "ranges": [local(v) for v in schema.objects(node, RDFS.range)]}
                if category == OWL.DatatypeProperty:
                    name, pattern = property_format(schema, node)
                    if name:
                        entry.update(value_format=name, pattern=pattern)
                properties.append(entry)
    values = [{"name": local(n), "iri": str(n), "label": str(next(schema.objects(n, RDFS.label), "")),
               "types": [local(t) for t in schema.objects(n, RDF.type) if str(t).startswith(IC)]}
              for n in sorted(set(schema.subjects(RDF.type, OWL.NamedIndividual)), key=str) if str(n).startswith(IC)]
    return {"section_groups": GROUPS, "classes": classes, "properties": properties, "ontology_values": values}
