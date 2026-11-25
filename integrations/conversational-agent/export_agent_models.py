#!/usr/bin/env python3
"""Export ontology JSON models, verify bundles and refresh agent-owned copies."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from urllib.request import Request, urlopen
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from rdflib import Graph, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = 'https://w3id.org/icareonto/'
EXPORTER_VERSION = '1.0.0'
FORMAT_VERSION = '1.0.0'
STRUCTURAL = {'model_id', 'title', 'version', 'status', 'source', 'nodes', 'relations', 'taxonomy_groups'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'Duplicate JSON key: ' + key)
            out[key] = value
        return out
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def relative_path(name):
    p = PurePosixPath(name)
    require(not p.is_absolute() and p.parts and all(x not in {'.', '..'} for x in p.parts)
            and '\\' not in name and ':' not in name and p.as_posix() == name,
            'Unsafe bundle path: ' + name)
    return Path(*p.parts)


def input_file(folder, name):
    path = folder / relative_path(name)
    require(path.resolve().is_relative_to(folder.resolve()) and path.is_file() and not path.is_symlink(),
            'Missing or unsafe input: ' + name)
    return path


def snake(name):
    first = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', first).replace('-', '_').lower()


def load_ontology(folder):
    """Resolve bundled imports locally; never dereference the ontology over HTTP."""
    folder = Path(folder).resolve()
    graph = Graph()
    seen = set()
    for entry in ET.parse(folder / 'catalog-v001.xml').getroot():
        if '/releases/' in entry.attrib['name']:
            continue
        path = input_file(folder, entry.attrib['uri'])
        if path not in seen:
            graph.parse(path, format='turtle')
            seen.add(path)
    ontology = URIRef(BASE)
    require((ontology, RDF.type, OWL.Ontology) in graph, 'Canonical ontology IRI is missing')
    version = str(graph.value(ontology, OWL.versionInfo))
    require(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version), 'A released major.minor.patch ontology version is required')
    require(graph.value(ontology, OWL.versionIRI) == URIRef(BASE + 'releases/' + version + '/icareonto'),
            'Ontology version IRI does not match its version')
    fingerprint = digest('\n'.join(sorted(' '.join(t.n3() for t in triple) for triple in to_canonical_graph(graph))).encode())
    return graph, {'iri': BASE, 'version': version, 'version_iri': str(graph.value(ontology, OWL.versionIRI)),
                   'sha256': fingerprint}


def literal(graph, subject, predicate):
    values = sorted(graph.objects(subject, predicate), key=lambda v: (getattr(v, 'language', '') != 'en', str(v)))
    return str(values[0]) if values else ''


def ids_for(iris, overrides):
    # Reserve old IDs even when their terms are removed, so they cannot be reused.
    require(len(set(overrides.values())) == len(overrides), 'Duplicate identifiers in the export profile')
    reserved = {name: iri for iri, name in overrides.items()}
    out = {}
    for iri in sorted(iris, key=str):
        text = str(iri)
        if text.startswith(BASE):
            default = snake(text.removeprefix(BASE))
        else:
            namespace, local = text.rsplit('#', 1) if '#' in text else text.rsplit('/', 1)
            default = 'external_' + digest(namespace.encode())[:8] + '_' + snake(local)
        name = overrides.get(text, default)
        require(re.fullmatch(r'[a-z][a-z0-9_]*', name), 'Invalid agent identifier: ' + name)
        require(name not in reserved or reserved[name] == str(iri), 'Agent identifier collision: ' + name)
        reserved[name] = str(iri)
        out[iri] = name
    return out


def project(graph, ontology, profile, selected=None):
    models = profile['models']
    require(all(re.fullmatch(r'[a-z][a-z0-9_]*', mid) for mid in models), 'Unsafe profile model identifier')
    selected = sorted(selected or models)
    require(set(selected) <= models.keys(), 'Unknown export model')
    objects = {s for s in graph.subjects(RDF.type, OWL.ObjectProperty) if str(s).startswith(BASE)}
    data = {s for s in graph.subjects(RDF.type, OWL.DatatypeProperty) if str(s).startswith(BASE)}
    entities = {s for kind in [OWL.Class, OWL.NamedIndividual] for s in graph.subjects(RDF.type, kind)
                if isinstance(s, URIRef)}
    referenced = {v for prop in objects for field in [RDFS.domain, RDFS.range]
                  for v in graph.objects(prop, field) if isinstance(v, URIRef)}
    for iri in referenced:
        require(not str(iri).startswith(BASE) or (iri, RDF.type, OWL.Class) in graph,
                'Local property endpoint is not a declared class: ' + str(iri))
        entities.add(iri)
    node_ids = ids_for(entities, profile['node_ids'])
    relation_ids = ids_for(objects, profile['relation_ids'])
    data_ids = ids_for(data, {})
    def detail(iri):
        return {'iri': str(iri), 'label': literal(graph, iri, RDFS.label) or str(iri).split('#')[-1].split('/')[-1],
                'definition': literal(graph, iri, SKOS.definition) or literal(graph, iri, RDFS.comment),
                'alternative_labels': sorted(str(v) for v in graph.objects(iri, SKOS.altLabel)),
                'modules': sorted(str(v) for v in graph.objects(iri, RDFS.isDefinedBy)),
                'external': not str(iri).startswith(BASE),
                'review_status': sorted(str(v) for v in graph.objects(iri, URIRef(BASE + 'metadata#reviewStatus'))),
                'deprecated': any(str(v).lower() in {'true', '1'} for v in graph.objects(iri, OWL.deprecated))}
    index = {'entities': {}, 'object_properties': {}, 'data_properties': {}}
    for iri, ident in node_ids.items():
        entry = detail(iri)
        entry.update(kind='individual' if (iri, RDF.type, OWL.NamedIndividual) in graph else 'class',
                     parents=sorted(node_ids[v] for v in graph.objects(iri, RDFS.subClassOf) if v in node_ids),
                     types=sorted(node_ids[v] for v in graph.objects(iri, RDF.type) if v in node_ids),
                     schemes=sorted(str(v) for v in graph.objects(iri, SKOS.inScheme)),
                     broader=sorted(str(v) for v in graph.objects(iri, SKOS.broader)))
        index['entities'][ident] = entry
    for kind, ids in [('object_properties', relation_ids), ('data_properties', data_ids)]:
        for iri, ident in ids.items():
            domains, ranges = list(graph.objects(iri, RDFS.domain)), list(graph.objects(iri, RDFS.range))
            # Multiple OWL domains are intersections, not alternative edges.
            require(len(domains) == len(ranges) == 1 and domains[0] in node_ids and isinstance(ranges[0], URIRef),
                    'Cannot project an anonymous or multiple domain/range: ' + str(iri))
            entry = detail(iri)
            entry['domain'] = node_ids[domains[0]]
            if kind == 'object_properties':
                require(ranges[0] in node_ids, 'Unknown object-property range: ' + str(iri))
                entry['range'] = node_ids[ranges[0]]
            else:
                entry['datatype'] = str(ranges[0])
                entry['value_format'] = literal(graph, iri, URIRef(BASE + 'metadata#valueFormat'))
                entry['value_pattern'] = literal(graph, iri, URIRef(BASE + 'metadata#valuePattern'))
            index[kind][ident] = entry
    result = {}
    for mid in selected:
        spec = models[mid]
        module = BASE + spec['module']
        require(any(module in v['modules'] for v in index['entities'].values()), 'Unknown ontology module: ' + module)
        included = {key for key, value in index['entities'].items() if module in value['modules']}
        edges = {key: value for key, value in index['object_properties'].items() if module in value['modules']}
        literals = {key: value for key, value in index['data_properties'].items() if module in value['modules']}
        included.update(v[key] for v in edges.values() for key in ['domain', 'range'])
        included.update(v['domain'] for v in literals.values())
        # Retain named parents and types needed to interpret cross-module references.
        while True:
            extra = {n for key in included for field in ['parents', 'types'] for n in index['entities'][key][field]}
            if extra <= included:
                break
            included.update(extra)
        groups = []
        for parent in sorted(included):
            for field, interpretation, suffix in [('parents', 'subclass', 'subclasses'), ('types', 'instance', 'instances')]:
                members = sorted(k for k in included if parent in index['entities'][k][field])
                if members:
                    groups.append({'id': parent + '_' + suffix, 'parent': parent, 'members': members,
                                   'interpretation': interpretation, 'confidence': 'high'})
        result[mid] = {'model_id': mid, 'title': spec['title'], 'version': ontology['version'], 'status': 'ontology_export',
                       'source': {'type': 'owl_ontology', 'ontology_iri': BASE, 'module_iri': module,
                                  'ontology_version': ontology['version'], 'ontology_sha256': ontology['sha256']},
                       'model_kinds': ['data_schema'],
                       'nodes': [{'id': k, 'label': index['entities'][k]['label'],
                                  'description': index['entities'][k]['definition'], 'kind': 'entity'} for k in sorted(included)],
                       'relations': [{'id': k, 'label': v['label'], 'from': v['domain'], 'to': v['range'],
                                      'description': v['definition'],
                                      'kind': 'object_property', 'confidence': 'high'} for k, v in sorted(edges.items())],
                       'taxonomy_groups': groups, 'agent_contracts': {}, 'procedure_contracts': [],
                       'memory_bindings': [], 'aliases': [], 'review_notes': []}
    return result, index


def validate_model(model, index):
    nodes = {n['id']: n for n in model['nodes']}
    require(len(nodes) == len(model['nodes']), 'Duplicate node IDs')
    relations = {r['id']: r for r in model['relations']}
    require(len(relations) == len(model['relations']), 'Duplicate relation IDs')
    for key in nodes:
        require(key in index['entities'], 'Node is not declared in the ontology: ' + key)
        require(nodes[key].get('description') == index['entities'][key]['definition'], 'Node description differs from its ontology definition: ' + key)
    for key, relation in relations.items():
        require(key in index['object_properties'], 'Unknown relation: ' + key)
        expected = index['object_properties'][key]
        require(relation.get('description') == expected['definition'], 'Relation description differs from its ontology definition: ' + key)
        require(relation['from'] == expected['domain'] and relation['to'] == expected['range'], 'Relation direction/range differs: ' + key)
        require(relation['from'] in nodes and relation['to'] in nodes, 'Missing relation endpoint')
    for group in model['taxonomy_groups']:
        field = {'subclass': 'parents', 'instance': 'types'}.get(group['interpretation'])
        require(field is not None and group['parent'] in nodes, 'Invalid taxonomy group')
        for member in group['members']:
            require(member in nodes and group['parent'] in index['entities'][member][field], 'Incorrect taxonomy membership')
    return binding_issues(model, index)


def binding_issues(model, index):
    nodes = {n['id'] for n in model['nodes']}
    relations = {r['id'] for r in model['relations']}
    issues = []
    def compatible(node, domain, seen=None):
        seen = set() if seen is None else seen
        if node == domain:
            return True
        if node in seen or node not in index['entities']:
            return False
        seen.add(node)
        return any(compatible(p, domain, seen) for p in index['entities'][node]['parents'])
    for binding in model.get('memory_bindings', []):
        def issue(message):
            issues.append({'model_id': model['model_id'], 'binding': binding.get('path'),
                           'status': binding.get('status'), 'message': message})
        if binding.get('node') not in nodes:
            issue('Binding target is absent from the ontology projection: ' + str(binding.get('node')))
        capture = binding.get('capture', {})
        if binding.get('status') == 'active' and not capture:
            issue('Active binding has no capture contract')
        for prop, relation in capture.get('relation_mappings', {}).items():
            if relation not in relations:
                issue('Capture relation is absent: ' + relation)
            elif not compatible(binding.get('node'), index['object_properties'][relation]['domain']):
                issue('Capture relation domain is incompatible with the binding target: ' + relation)
            if prop not in capture.get('properties_schema', {}).get('properties', {}):
                issue('Capture mapping has no schema property: ' + prop)
        properties = capture.get('properties_schema', {}).get('properties', {})
        for prop in capture.get('identity_fields', []) + capture.get('extension_fields', []):
            if prop not in properties:
                issue('Capture identity/extension field has no schema property: ' + prop)
    return issues


def changes(old, new):
    result = {}
    for field in ['nodes', 'relations', 'taxonomy_groups']:
        a, b = ({x['id']: x for x in model.get(field, [])} for model in [old, new])
        result[field] = {'added': sorted(b.keys() - a.keys()), 'removed': sorted(a.keys() - b.keys()),
                         'modified': sorted(key for key in a.keys() & b.keys() if a[key] != b[key]),
                         'details': {key: {'before': a[key], 'after': b[key]} for key in sorted(a.keys() & b.keys()) if a[key] != b[key]}}
    return result


def index_changes(old, new):
    result = {}
    for section in ['entities', 'object_properties', 'data_properties']:
        a, b = old.get(section, {}), new[section]
        result[section] = {'added': sorted(b.keys() - a.keys()), 'removed': sorted(a.keys() - b.keys()),
                           'modified': sorted(key for key in a.keys() & b.keys() if a[key] != b[key]),
                           'details': {key: {'before': a[key], 'after': b[key]} for key in sorted(a.keys() & b.keys()) if a[key] != b[key]}}
    return result


def atomic_output(output, populate):
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink(), 'Output already exists; use a new directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.agent-export-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'output'
        stage.mkdir()
        value = populate(stage)
        stage.rename(output)
    return value


def export_bundle(output, ontology_dir=ROOT / 'serialisation', profile_path=HERE / 'profile.json', selected=None, previous=None):
    change_path = Path(str(output) + '-changes.json')
    require(not change_path.exists() and not change_path.is_symlink(), 'Change-report output already exists; use a new output name')
    graph, ontology = load_ontology(ontology_dir)
    profile = read_json(profile_path)
    models, index = project(graph, ontology, profile, selected)
    for model in models.values():
        require(not validate_model(model, index), 'Export contains invalid memory bindings')
    licensing = {'original_content_license': str(graph.value(URIRef(BASE), DCTERMS.license)),
                 'creator': sorted(str(v) for v in graph.objects(URIRef(BASE), DCTERMS.creator)),
                 'contributors': sorted(str(v) for v in graph.objects(URIRef(BASE), DCTERMS.contributor)),
                 'rights': literal(graph, URIRef(BASE), DCTERMS.rights),
                 'scope': 'Original ontology-derived fields and index only; imported vocabulary material retains its applicable terms.',
                 'third_party_notices': 'https://github.com/RGU-Computing/icareonto/blob/main/THIRD_PARTY_NOTICES.md'}
    payload = {'ontology': ontology, 'licensing': licensing, 'profile_sha256': digest(canonical(profile)),
               'exporter_version': EXPORTER_VERSION,
               'exporter_sha256': digest(Path(__file__).read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8')),
               'format_version': FORMAT_VERSION, 'models': models, 'index': index}
    bundle_id = digest(canonical(payload))[:24]
    previous_models = {}
    previous_index = {}
    if previous:
        old_manifest, previous_models, previous_index = verify_bundle(previous)
    change_report = {'status': 'PASS', 'compared_with': old_manifest['bundle_id'] if previous else None,
                     'models_added': sorted(models.keys() - previous_models.keys()),
                     'models_removed': sorted(previous_models.keys() - models.keys()),
                     'ontology_index': index_changes(previous_index, index),
                     'models': {mid: changes(previous_models.get(mid, {}), model) for mid, model in models.items()}}
    def write(stage):
        for mid, model in models.items():
            save_json(stage / mid / 'model.json', model)
        save_json(stage / 'ontology-index.json', index)
        # Comparison reports are contextual, not part of immutable bundle identity.
        files = {p.relative_to(stage).as_posix(): digest(p.read_bytes()) for p in sorted(stage.rglob('*.json'))}
        manifest = {'schema_version': FORMAT_VERSION, 'kind': 'icareonto_agent_models', 'status': 'ontology_export',
                    'bundle_id': bundle_id, 'ontology': ontology, 'licensing': licensing,
                    'exporter': {'version': EXPORTER_VERSION, 'sha256': payload['exporter_sha256']},
                    'profile': {'version': profile['profile_version'], 'sha256': payload['profile_sha256']},
                    'models': [{'model_id': mid, 'title': model['title'], 'path': mid + '/model.json'} for mid, model in models.items()],
                    'runtime': {}, 'files': files}
        save_json(stage / 'manifest.json', manifest)
        return {'status': 'PASS', 'bundle_id': bundle_id, 'ontology_version': ontology['version'],
                'models': len(models), 'change_report': change_report}
    result = atomic_output(output, write)
    save_json(change_path, change_report)
    return result


def verify_bundle(folder):
    folder = Path(folder).resolve()
    manifest = read_json(input_file(folder, 'manifest.json'))
    require(manifest.get('kind') == 'icareonto_agent_models' and manifest.get('status') == 'ontology_export', 'Not an authoritative ontology export bundle')
    require(manifest.get('schema_version') == FORMAT_VERSION, 'Unsupported agent export format')
    require(re.fullmatch(r'[a-f0-9]{24}', manifest.get('bundle_id', '')), 'Invalid bundle identifier')
    require(set(manifest['files']) == {'ontology-index.json'} | {entry['model_id'] + '/model.json' for entry in manifest['models']},
            'Bundle file list contains unexpected payloads')
    expected = set(manifest['files']) | {'manifest.json'}
    actual = set()
    for path in folder.rglob('*'):
        require(not path.is_symlink(), 'Bundle cannot contain symlinks')
        if path.is_file():
            actual.add(path.relative_to(folder).as_posix())
    require(actual == expected, 'Bundle inventory does not match its manifest')
    for name, sha in manifest['files'].items():
        require(digest(input_file(folder, name).read_bytes()) == sha, 'Bundle hash mismatch: ' + name)
    index = read_json(input_file(folder, 'ontology-index.json'))
    models = {}
    for entry in manifest['models']:
        mid = entry['model_id']
        require(mid not in models, 'Duplicate model ID in manifest')
        require(entry['path'] == mid + '/model.json', 'Model path differs from its identifier')
        model = read_json(input_file(folder, entry['path']))
        require(mid == model['model_id'], 'Model identifier differs from manifest')
        require(model['source']['ontology_sha256'] == manifest['ontology']['sha256'], 'Model ontology fingerprint differs')
        require(not model.get('agent_contracts') and not model.get('procedure_contracts') and not model.get('memory_bindings'),
                'Authoritative exports cannot contain agent-owned runtime configuration')
        require(not validate_model(model, index), 'Invalid binding in ontology export')
        models[mid] = model
    payload = {'ontology': manifest['ontology'], 'licensing': manifest['licensing'], 'profile_sha256': manifest['profile']['sha256'],
               'exporter_version': manifest['exporter']['version'], 'exporter_sha256': manifest['exporter']['sha256'],
               'format_version': manifest['schema_version'], 'models': models, 'index': index}
    require(digest(canonical(payload))[:24] == manifest['bundle_id'], 'Bundle identifier does not match its content')
    return manifest, models, index


def refresh(agent_models, bundle, output):
    """Produce candidates only; never edit the agent's deployed model directory."""
    agent_models = Path(agent_models).resolve()
    manifest, exported, index = verify_bundle(bundle)
    old_manifest = read_json(input_file(agent_models, 'manifest.json'))
    output = Path(output).absolute()
    require(output.resolve() != agent_models and not agent_models.is_relative_to(output.resolve()), 'Output cannot replace agent inputs')
    report = {'status': 'READY_FOR_AGENT_TESTS', 'bundle_id': manifest['bundle_id'], 'ontology': manifest['ontology'],
              'issues': [], 'models': {}, 'agent_settings_preserved': True,
              'scope': 'Checks structural references; free-text policies and stored-record migration require agent-side tests.'}
    candidates = {}
    entries = []
    for entry in old_manifest['models']:
        mid = entry['model_id']
        old = read_json(input_file(agent_models, entry['path']))
        require(mid in exported, 'Agent model is not present in the selected export: ' + mid)
        new = deepcopy(old)
        new.update({key: deepcopy(value) for key, value in exported[mid].items() if key in STRUCTURAL})
        # All other model fields and the complete runtime manifest remain agent-owned.
        require({k: v for k, v in old.items() if k not in STRUCTURAL} ==
                {k: v for k, v in new.items() if k not in STRUCTURAL}, 'Agent configuration changed unexpectedly')
        report['issues'].extend(validate_model(new, index))
        report['models'][mid] = changes(old, new)
        candidates[mid] = new
        refreshed_entry = deepcopy(entry)
        refreshed_entry.update(title=new['title'], path=mid + '/model.json')
        entries.append(refreshed_entry)
    if report['issues']:
        report['status'] = 'REVIEW_REQUIRED'
    def write(stage):
        # Separate candidate-models from the root report to prevent accidental copying.
        target = stage / 'candidate-models'
        refreshed = deepcopy(old_manifest)
        refreshed['models'] = entries
        refreshed['status'] = report['status'].lower()
        refreshed['ontology_export'] = {'bundle_id': manifest['bundle_id'], 'ontology': manifest['ontology'],
                                       'format_version': manifest['schema_version'], 'index_path': 'ontology-index.json',
                                       'licensing': manifest['licensing']}
        save_json(target / 'manifest.json', refreshed)
        for mid, model in candidates.items():
            save_json(target / mid / 'model.json', model)
        shutil.copyfile(Path(bundle) / 'ontology-index.json', target / 'ontology-index.json')
        save_json(stage / 'refresh-report.json', report)
        return report
    return atomic_output(output, write)


def download(url, output, expected_id=None):
    """Fetch only manifest-listed files over HTTPS and verify before installing."""
    url = url.rstrip('/') + '/'
    require(urlparse(url).scheme == 'https' and not urlparse(url).query and not urlparse(url).fragment,
            'Use an HTTPS bundle-directory URL without a query or fragment')
    def fetch(name):
        relative_path(name)
        with urlopen(Request(url + name, headers={'Accept': 'application/json'}), timeout=30) as response:
            require(urlparse(response.geturl()).scheme == 'https', 'Bundle redirected away from HTTPS')
            return response.read()
    raw = fetch('manifest.json')
    manifest = json.loads(raw)
    require(manifest.get('kind') == 'icareonto_agent_models', 'Unexpected downloaded manifest')
    require(not expected_id or manifest['bundle_id'] == expected_id, 'Downloaded bundle is not the pinned identifier')
    def write(stage):
        (stage / 'manifest.json').write_bytes(raw)
        for name, sha in manifest['files'].items():
            data = fetch(name)
            require(digest(data) == sha, 'Downloaded file failed its hash: ' + name)
            path = stage / relative_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        checked, _, _ = verify_bundle(stage)
        return {'status': 'PASS', 'bundle_id': checked['bundle_id'], 'models': len(checked['models'])}
    return atomic_output(output, write)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('export', help='Build ontology-only JSON model files')
    p.add_argument('--ontology-dir', type=Path, default=ROOT / 'serialisation')
    p.add_argument('--profile', type=Path, default=HERE / 'profile.json')
    p.add_argument('--model', action='append', help='Limit output to these model IDs; repeat to select several')
    p.add_argument('--previous', type=Path, help='Earlier authoritative export for a change report')
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('verify', help='Verify bundle inventory, hashes and structural references')
    p.add_argument('--bundle', type=Path, required=True)
    p = sub.add_parser('refresh', help='Prepare candidate agent models without changing original inputs')
    p.add_argument('--agent-models', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('download', help='Download and verify a published bundle')
    p.add_argument('--url', required=True)
    p.add_argument('--expected-id', help='Pin the required bundle identifier')
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'export':
        result = export_bundle(args.output, args.ontology_dir, args.profile, args.model, args.previous)
        result.pop('change_report')
        result['change_report_path'] = str(args.output) + '-changes.json'
    elif args.command == 'verify':
        manifest, models, _ = verify_bundle(args.bundle)
        result = {'status': 'PASS', 'bundle_id': manifest['bundle_id'], 'models': len(models)}
    elif args.command == 'refresh':
        result = refresh(args.agent_models, args.bundle, args.output)
        result = {key: value for key, value in result.items() if key != 'models'}
        result['report_path'] = str(args.output / 'refresh-report.json')
    else:
        result = download(args.url, args.output, args.expected_id)
    print(json.dumps(result, indent=2))
    return 2 if result['status'] == 'REVIEW_REQUIRED' else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error)}), file=sys.stderr)
        raise SystemExit(1)
