#!/usr/bin/env python3
"""Verify the deployed site's media types, RDF documents and import closure."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from rdflib import Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL

BASE = 'https://w3id.org/icareonto/'


def verify_site(base_url):
    base_url = base_url.rstrip('/') + '/'
    if urlparse(base_url).scheme != 'https':
        raise ValueError('The published base URL must use HTTPS')
    checked = {}
    def fetch(relative, media):
        url = base_url + relative
        if url in checked:
            return checked[url]
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={'Accept': media}), timeout=30) as response:
                    actual = response.headers.get_content_type()
                    if actual != media:
                        raise ValueError(f'{url} has media type {actual}; expected {media}')
                    data = response.read()
                checked[url] = data
                return data
            except (HTTPError, URLError):
                if attempt == 2:
                    raise
                time.sleep(3)
    active = json.loads(fetch('publication.json', 'application/json'))
    turtle = Graph().parse(data=fetch('current/ontology.ttl', 'text/turtle'), format='turtle')
    xml = Graph().parse(data=fetch('current/ontology.rdf', 'application/rdf+xml'), format='xml')
    if not isomorphic(turtle, xml):
        raise ValueError('Deployed Turtle and RDF/XML exports differ')
    if str(turtle.value(URIRef(BASE), OWL.versionInfo)) != active['ontology_version']:
        raise ValueError('Deployed ontology does not match the active version')
    resources = json.loads(fetch('education/current/catalogue.json', 'application/json'))
    names = {'education/graphs/resources': 'education/current/catalogue.ttl',
             'education/graphs/activities': 'education/current/activity-templates.ttl',
             'education/dataset': 'education/current/dataset.ttl'}
    def document(iri):
        if not iri.startswith(BASE):
            raise ValueError('Unexpected publication import: ' + iri)
        path = iri.removeprefix(BASE)
        if path.startswith('releases/'):
            return path + '.ttl'
        if path.startswith('education/releases/'):
            return path
        if path in names:
            return names[path]
        return 'current/' + (path or 'icareonto') + '.ttl'
    pending = ['current/icareonto.ttl', 'education/current/dataset.ttl',
               'releases/' + active['ontology_version'] + '/icareonto.ttl',
               'education/releases/' + active['catalogue_release'] + '/dataset.ttl']
    visited = set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        graph = Graph().parse(data=fetch(relative, 'text/turtle'), format='turtle')
        visited.add(relative)
        pending.extend(document(str(iri)) for iri in graph.objects(None, OWL.imports))
    for folder in ['current', 'releases/' + active['ontology_version'], 'education/current',
                   'education/releases/' + active['catalogue_release']]:
        manifest = json.loads(fetch(folder + '/manifest.json', 'application/json'))
        if manifest.get('version', active['ontology_version']) != active['ontology_version'] or \
                manifest.get('release_id', active['catalogue_release']) != active['catalogue_release']:
            raise ValueError('Deployed manifest does not match the active publication')
        for name, expected in manifest['files'].items():
            url = base_url + folder + '/' + name
            if url in checked and hashlib.sha256(checked[url]).hexdigest() != expected:
                raise ValueError('Deployed document failed its manifest hash: ' + url)
    return {'status': 'PASS', 'base_url': base_url, 'ontology_version': active['ontology_version'],
            'catalogue_release': active['catalogue_release'], 'resources': len(resources['records']),
            'rdf_documents_loaded': len(visited), 'http_documents_checked': len(checked),
            'w3id_service': 'Not checked; this check verifies the publication host independently'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://rgu-computing.github.io/icareonto/')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify_site(args.base_url)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
