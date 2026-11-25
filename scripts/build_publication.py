#!/usr/bin/env python3
"""Build the public RDF distribution, retaining immutable release snapshots."""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from rdflib import Dataset, Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://w3id.org/icareonto/'
VERSION = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+')
CATALOGUE_ID = re.compile(r'[a-f0-9]{24}')
sys.path.insert(0, str(ROOT / 'education/scripts'))
import education_resources as education
sys.path.insert(0, str(ROOT / 'integrations/conversational-agent'))
import export_agent_models as agent_exporter


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def file_hashes(folder):
    """Hash publication payloads; the manifest never hashes itself."""
    result = {}
    for path in sorted(folder.rglob('*')):
        require(not path.is_symlink(), 'Publication snapshots cannot contain symlinks')
        if path.is_file() and path != folder / 'manifest.json':
            result[path.relative_to(folder).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def verify_snapshot(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    require(manifest['files'] == file_hashes(folder), 'Published snapshot integrity failure: ' + folder.name)
    return manifest


def same_payload(left, right):
    """Compare RDF semantics, allowing harmless serializer ordering differences."""
    if set(file_hashes(left)) != set(file_hashes(right)):
        return False
    for name in file_hashes(left):
        a, b = left / name, right / name
        if a.read_bytes() == b.read_bytes():
            continue
        if a.suffix == '.trig':
            da, db = Dataset().parse(a, format='trig'), Dataset().parse(b, format='trig')
            ga = {g.identifier: g for g in da.graphs()}
            gb = {g.identifier: g for g in db.graphs()}
            if ga.keys() != gb.keys() or not all(isomorphic(ga[k], gb[k]) for k in ga):
                return False
        elif a.suffix not in {'.ttl', '.rdf'} or not isomorphic(Graph().parse(a), Graph().parse(b)):
            return False
    return True


def install_snapshot(candidate, destination):
    """An existing release is reused byte-for-byte or rejected, never overwritten."""
    if destination.exists():
        verify_snapshot(destination)
        require(same_payload(candidate, destination),
                'Published release content changed: ' + destination.name + '. Use a new release identity.')
        return 'retained'
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidate, destination)
    return 'added'


def write_graph(folder, name, graph, rdfxml=False):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=path, format='turtle')
    if rdfxml:
        graph.serialize(destination=path.with_suffix('.rdf'), format='xml')


def rewrite_imports(graph, mapping):
    result = Graph()
    for prefix, namespace in graph.namespaces():
        result.bind(prefix, namespace)
    for s, p, o in graph:
        result.add((s, p, mapping.get(o, o) if p == OWL.imports else o))
    return result


def ontology_payloads(root):
    """Flatten the portable import catalogue into predictable published paths."""
    documents = {}
    for entry in ET.parse(root / 'serialisation/catalog-v001.xml').getroot():
        iri = entry.attrib['name']
        if iri.startswith(BASE + 'releases/'):
            continue
        require(iri.startswith(BASE), 'Unexpected ontology document IRI')
        name = iri.removeprefix(BASE) or 'icareonto'
        require(re.fullmatch(r'(imports/)?[a-z][a-z0-9-]*', name), 'Unsafe ontology document path')
        path = (root / 'serialisation' / entry.attrib['uri']).resolve()
        require(path.is_relative_to((root / 'serialisation').resolve()), 'Ontology import escapes serialisation')
        documents[iri] = (name + '.ttl', Graph().parse(path))
    entry = documents[BASE][1]
    version = str(entry.value(URIRef(BASE), OWL.versionInfo))
    require(VERSION.fullmatch(version), 'Publication requires a stable major.minor.patch ontology version')
    require(entry.value(URIRef(BASE), OWL.versionIRI) == URIRef(BASE + 'releases/' + version + '/icareonto'),
            'Ontology version IRI does not match its version')
    for _, graph in documents.values():
        for target in graph.objects(None, OWL.imports):
            require(str(target) in documents, 'Unresolved publication import: ' + str(target))
    return version, documents


def ontology_snapshot(folder, documents, version, commit, archived):
    mapping = {URIRef(iri): URIRef(BASE + 'releases/' + version + '/' + name.removesuffix('.ttl'))
               for iri, (name, _) in documents.items()} if archived else {}
    combined = Graph()
    for _, (name, graph) in sorted(documents.items()):
        write_graph(folder, name, rewrite_imports(graph, mapping))
        combined += graph
    # A complete term document has one ontology header and no unresolved imports.
    for ontology in set(combined.subjects(RDF.type, OWL.Ontology)) - {URIRef(BASE)}:
        combined.remove((ontology, None, None))
    combined.remove((None, OWL.imports, None))
    write_graph(folder, 'ontology.ttl', combined, rdfxml=True)
    save_json(folder / 'manifest.json', {'kind': 'ontology', 'version': version,
              'source_commit': commit, 'files': file_hashes(folder)})


def education_snapshot(folder, source, version, commit, archived):
    release = source['release_id']
    directory = Path(source['release_directory'])
    names = {'education/graphs/resources': 'catalogue.ttl',
             'education/graphs/activities': 'activity-templates.ttl', 'education/dataset': 'dataset.ttl'}
    mapping = {URIRef(BASE): URIRef(BASE + 'releases/' + version + '/icareonto')}
    mapping.update({URIRef(BASE + iri): URIRef(BASE + 'education/releases/' + release + '/' + name)
                    for iri, name in names.items()})
    dataset = Dataset()
    for iri, name in names.items():
        graph = Graph().parse(directory / name)
        if archived:
            graph = rewrite_imports(graph, mapping)
            graph.add((URIRef(BASE + iri), OWL.versionIRI,
                       URIRef(BASE + 'education/releases/' + release + '/' + name)))
        write_graph(folder, name, graph, rdfxml=True)
        for triple in graph:
            dataset.graph(URIRef(BASE + iri)).add(triple)
    dataset.serialize(destination=folder / 'dataset.trig', format='trig')
    shutil.copyfile(directory / 'catalogue.json', folder / 'catalogue.json')
    # This is a web distribution manifest, separate from the operational loader package.
    save_json(folder / 'manifest.json', {'kind': 'education', 'release_id': release,
              'ontology_version': version, 'source_commit': commit,
              'files': file_hashes(folder)})


def preserve_archives(previous, stage):
    if previous is None:
        return
    active = json.loads((previous / 'publication.json').read_text())
    for relative, pattern, key in [('releases', VERSION, 'preserved_ontology_releases'),
                                  ('education/releases', CATALOGUE_ID, 'preserved_catalogue_releases')]:
        parent = previous / relative
        require(parent.is_dir(), 'A previously published archive directory is missing')
        require(not parent.is_symlink(), 'Archive root cannot be a symlink')
        require(set(active[key]) == {p.name for p in parent.iterdir()},
                'Previously published release history is incomplete')
        for folder in parent.iterdir():
            require(folder.is_dir() and not folder.is_symlink() and pattern.fullmatch(folder.name),
                    'Unexpected archived release path')
            verify_snapshot(folder)
        shutil.copytree(parent, stage / relative)
    # Existing deployments gain this new resource category without losing older RDF archives.
    parent = previous / 'agent-models/releases'
    known = active.get('preserved_agent_bundles')
    if known is None:
        require(not parent.exists(), 'Agent archives exist without a publication inventory')
    else:
        require(parent.is_dir() and not parent.is_symlink(), 'Agent archive directory is missing or unsafe')
        require(set(known) == {p.name for p in parent.iterdir()}, 'Agent export history is incomplete')
        for folder in parent.iterdir():
            require(folder.is_dir() and not folder.is_symlink() and CATALOGUE_ID.fullmatch(folder.name), 'Unsafe agent archive path')
            agent_exporter.verify_bundle(folder)
        shutil.copytree(parent, stage / 'agent-models/releases')


def landing_page(stage, version, catalogue_id, agent_bundle):
    versions = sorted(p.name for p in (stage / 'releases').iterdir())
    links = ''.join('<li><a href="releases/' + escape(v) + '/ontology.ttl">' + escape(v) + '</a></li>' for v in versions)
    html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>iCARE Onto — published resources</title></head><body>
<h1>iCARE Onto</h1><p>Semantic resources supporting cancer survivorship, cardiovascular health and personalised education.</p>
<p>Namespace: <a href="https://w3id.org/icareonto/">https://w3id.org/icareonto/</a></p>
<p>Current ontology: VERSION. <a href="current/ontology.ttl">Complete Turtle</a> ·
<a href="current/ontology.rdf">RDF/XML</a> · <a href="current/icareonto.ttl">Modular entry point</a></p>
<h2>Preserved ontology releases</h2><ul>RELEASES</ul>
<h2>Educational catalogue</h2><p>Current catalogue: CATALOGUE.
<a href="education/current/catalogue.json">JSON metadata</a> ·
<a href="education/current/catalogue.ttl">Turtle metadata</a> ·
<a href="education/current/dataset.ttl">Dataset entry point</a></p>
<p>Linked educational publications retain their providers’ terms. Inclusion does not establish suitability for every participant or site.</p>
<h2>Conversational-agent ontology models</h2>
<p><a href="agent-models/current/manifest.json">Current JSON manifest</a> ·
<a href="agent-models/current/ontology-index.json">Identifiers and definitions</a> ·
<a href="agent-models/releases/AGENT_BUNDLE/manifest.json">Pinned export manifest</a></p>
<p>These exports contain ontology structure. Agent memory bindings and behavioural settings must be preserved when refreshing an existing agent.
<a href="https://github.com/RGU-Computing/icareonto/tree/main/integrations/conversational-agent">Export and refresh instructions</a></p>
<p><a href="https://github.com/RGU-Computing/icareonto">Documentation and source repository</a> ·
<a href="LICENSE.md">Licensing</a> · Contact: <a href="mailto:maya.eu@rgu.ac.uk">maya.eu@rgu.ac.uk</a></p>
</body></html>
'''
    (stage / 'index.html').write_text(html.replace('VERSION', escape(version)).replace('RELEASES', links).replace('CATALOGUE', escape(catalogue_id)).replace('AGENT_BUNDLE', escape(agent_bundle)), encoding='utf-8')


def build(output, previous=None, root=ROOT, commit=None):
    output, root = output.resolve(), root.resolve()
    previous = previous.resolve() if previous is not None else None
    require(output != root and not root.is_relative_to(output), 'Output cannot replace the repository or its parent')
    require(not output.exists(), 'Output already exists; choose a new build directory')
    require(previous is None or (previous != output and not previous.is_relative_to(output)), 'Previous publication must be separate from output')
    require(previous is None or (previous.is_dir() and (previous / 'publication.json').is_file()),
            'Previous publication is missing or is not a published site; refusing to discard release history')
    if commit is None:
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    require(re.fullmatch(r'[0-9a-f]{40}', commit), 'A full source commit identifier is required')
    version, documents = ontology_payloads(root)
    # The loader validates source hashes, the catalogue manifest and ontology fingerprint.
    source = education.load_release(root / 'education/data/catalogue')
    require(CATALOGUE_ID.fullmatch(source['release_id']), 'Unsafe catalogue release identifier')
    require(source['ontology_sha256'] == education.load_schema(root / 'serialisation')[2],
            'Catalogue does not match the current ontology; regenerate it before publication')
    if previous is not None:
        active = json.loads((previous / 'publication.json').read_text())
        require(tuple(map(int, version.split('.'))) >= tuple(map(int, active['ontology_version'].split('.'))),
                'An older ontology version cannot replace the current release')
        require(source['release_id'] == active['catalogue_release'] or
                not (previous / 'education/releases' / source['release_id']).exists(),
                'An earlier catalogue cannot replace the current release; curate and publish a new snapshot')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.publication-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'site'
        stage.mkdir()
        preserve_archives(previous, stage)
        ontology_snapshot(stage / 'current', documents, version, commit, False)
        education_snapshot(stage / 'education/current', source, version, commit, False)
        candidate = Path(temporary) / 'ontology'
        ontology_snapshot(candidate, documents, version, commit, True)
        ontology_status = install_snapshot(candidate, stage / 'releases' / version)
        candidate = Path(temporary) / 'education'
        education_snapshot(candidate, source, version, commit, True)
        education_status = install_snapshot(candidate, stage / 'education/releases' / source['release_id'])
        previous_agent = previous / 'agent-models/current' if previous is not None and (previous / 'agent-models/current').is_dir() else None
        agent_result = agent_exporter.export_bundle(stage / 'agent-models/current', root / 'serialisation',
                                                    root / 'integrations/conversational-agent/profile.json', previous=previous_agent)
        agent_id = agent_result['bundle_id']
        agent_status = install_snapshot(stage / 'agent-models/current', stage / 'agent-models/releases' / agent_id)
        for name in ['LICENSE.md', 'LICENSES', 'THIRD_PARTY_NOTICES.md']:
            src, dst = root / name, stage / name
            shutil.copytree(src, dst) if src.is_dir() else shutil.copyfile(src, dst)
        (stage / '.nojekyll').touch()
        landing_page(stage, version, source['release_id'], agent_id)
        report = {'status': 'PASS', 'ontology_version': version, 'catalogue_release': source['release_id'],
                  'source_commit': commit, 'ontology_snapshot': ontology_status, 'catalogue_snapshot': education_status,
                  'agent_bundle_id': agent_id, 'agent_snapshot': agent_status,
                  'preserved_agent_bundles': sorted(p.name for p in (stage / 'agent-models/releases').iterdir()),
                  'preserved_ontology_releases': sorted(p.name for p in (stage / 'releases').iterdir()),
                  'preserved_catalogue_releases': sorted(p.name for p in (stage / 'education/releases').iterdir())}
        save_json(stage / 'publication.json', report)
        # Rename only after every integrity and immutability check has succeeded.
        stage.rename(output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/site')
    parser.add_argument('--previous', type=Path, help='Existing gh-pages tree; required after the first publication')
    parser.add_argument('--source-commit', help='Full commit identifier; defaults to the current checkout')
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.previous, commit=args.source_commit), indent=2))
