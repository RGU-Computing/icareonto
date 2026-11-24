"""Publication checks exercise preserved releases, import pinning and failed updates."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_publication as publication


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.parent = Path(cls.temporary.name)
        cls.site = cls.parent / 'first'
        cls.result = publication.build(cls.site, commit='1' * 40)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(dir=self.parent))
        self.addCleanup(shutil.rmtree, self.folder)

    def test_complete_term_documents_are_equivalent(self):
        folder = self.site / 'current'
        turtle = Graph().parse(folder / 'ontology.ttl')
        xml = Graph().parse(folder / 'ontology.rdf')
        self.assertTrue(isomorphic(turtle, xml))
        self.assertEqual(set(turtle.subjects(RDF.type, OWL.Ontology)), {URIRef(publication.BASE)})
        self.assertFalse(list(turtle.triples((None, OWL.imports, None))))
        _, documents = publication.ontology_payloads(publication.ROOT)
        expected = Graph()
        for _, graph in documents.values():
            expected += graph
        for header in set(expected.subjects(RDF.type, OWL.Ontology)) - {URIRef(publication.BASE)}:
            expected.remove((header, None, None))
        expected.remove((None, OWL.imports, None))
        self.assertTrue(isomorphic(expected, turtle))

    def test_every_archived_ontology_import_stays_in_its_version(self):
        version = self.result['ontology_version']
        folder = self.site / 'releases' / version
        graphs = list(folder.rglob('*.ttl'))
        self.assertGreater(len(graphs), 20)
        for path in graphs:
            for iri in Graph().parse(path).objects(None, OWL.imports):
                prefix = publication.BASE + 'releases/' + version + '/'
                self.assertTrue(str(iri).startswith(prefix))
                self.assertTrue((folder / (str(iri).removeprefix(prefix) + '.ttl')).is_file())

    def test_educational_archive_pins_ontology_and_graph_imports(self):
        folder = self.site / 'education/releases' / self.result['catalogue_release']
        entry = Graph().parse(folder / 'dataset.ttl')
        imports = set(entry.objects(None, OWL.imports))
        self.assertEqual(imports, {URIRef(publication.BASE + 'education/releases/' + folder.name + '/' + name)
                                  for name in ['catalogue.ttl', 'activity-templates.ttl']})
        catalogue = Graph().parse(folder / 'catalogue.ttl')
        self.assertIn(URIRef(publication.BASE + 'releases/' + self.result['ontology_version'] + '/icareonto'),
                      set(catalogue.objects(None, OWL.imports)))

    def test_republishing_preserves_existing_archive_bytes(self):
        output = self.folder / 'second'
        result = publication.build(output, self.site, commit='2' * 40)
        self.assertEqual(result['ontology_snapshot'], 'retained')
        self.assertEqual(result['catalogue_snapshot'], 'retained')
        for relative in ['releases', 'education/releases']:
            for path in (self.site / relative).rglob('*'):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (output / path.relative_to(self.site)).read_bytes())

    def test_modified_published_version_is_rejected_atomically(self):
        previous = self.folder / 'previous'
        shutil.copytree(self.site, previous)
        release = previous / 'releases' / self.result['ontology_version']
        path = release / 'core.ttl'
        graph = Graph().parse(path)
        graph.add((URIRef(publication.BASE + 'Participant'), RDFS.comment, Literal('A changed released definition')))
        graph.serialize(path, format='turtle')
        manifest = json.loads((release / 'manifest.json').read_text())
        manifest['files'] = publication.file_hashes(release)
        publication.save_json(release / 'manifest.json', manifest)
        output = self.folder / 'failed'
        with self.assertRaisesRegex(ValueError, 'Use a new release identity'):
            publication.build(output, previous, commit='3' * 40)
        self.assertFalse(output.exists())
        self.assertIn('A changed released definition', path.read_text())

    def test_new_release_keeps_earlier_snapshots(self):
        previous, stage = self.site, self.folder / 'site'
        stage.mkdir()
        publication.preserve_archives(previous, stage)
        _, documents = publication.ontology_payloads(publication.ROOT)
        # Version substitution simulates a new source release without editing the package.
        old_version = self.result['ontology_version']
        major, minor, _ = map(int, old_version.split('.'))
        new_version = f'{major}.{minor + 1}.0'
        updated = {}
        for iri, (name, graph) in documents.items():
            new = Graph()
            for s, p, o in graph:
                if p == OWL.versionInfo:
                    o = Literal(new_version)
                elif p == OWL.versionIRI:
                    o = URIRef(str(o).replace('/' + old_version + '/', '/' + new_version + '/'))
                new.add((s, p, o))
            updated[iri] = name, new
        candidate = self.folder / 'candidate'
        publication.ontology_snapshot(candidate, updated, new_version, '4' * 40, True)
        publication.install_snapshot(candidate, stage / 'releases' / new_version)
        self.assertEqual({p.name for p in (stage / 'releases').iterdir()}, {old_version, new_version})
        for path in (previous / 'releases' / old_version).rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (stage / path.relative_to(previous)).read_bytes())

    def test_missing_or_corrupt_previous_site_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Previous publication is missing'):
            publication.build(self.folder / 'output', self.folder / 'missing', commit='5' * 40)
        previous = self.folder / 'corrupt'
        shutil.copytree(self.site, previous)
        (previous / 'releases' / self.result['ontology_version'] / 'core.ttl').write_text('corrupt')
        with self.assertRaisesRegex(ValueError, 'integrity failure'):
            publication.build(self.folder / 'output', previous, commit='5' * 40)
        self.assertFalse((self.folder / 'output').exists())

    def test_symlinks_cannot_enter_published_archive(self):
        previous = self.folder / 'previous'
        shutil.copytree(self.site, previous)
        (previous / 'releases' / self.result['ontology_version'] / 'link').symlink_to(self.site / 'index.html')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            publication.build(self.folder / 'output', previous, commit='6' * 40)

    def test_missing_historical_release_cannot_be_silently_dropped(self):
        previous = self.folder / 'previous'
        shutil.copytree(self.site, previous)
        shutil.rmtree(previous / 'releases' / self.result['ontology_version'])
        with self.assertRaisesRegex(ValueError, 'history is incomplete'):
            publication.build(self.folder / 'output', previous, commit='6' * 40)
        self.assertFalse((self.folder / 'output').exists())

    def test_existing_output_and_repository_are_protected(self):
        with self.assertRaisesRegex(ValueError, 'Output already exists'):
            publication.build(self.site, commit='7' * 40)
        with self.assertRaisesRegex(ValueError, 'cannot replace the repository'):
            publication.build(publication.ROOT, commit='7' * 40)
        self.assertTrue((publication.ROOT / 'README.md').is_file())

    def test_json_resource_metadata_is_preserved(self):
        release = self.result['catalogue_release']
        original = publication.ROOT / 'education/data/catalogue/releases' / release / 'catalogue.json'
        for relative in ['education/current', 'education/releases/' + release]:
            self.assertEqual(original.read_bytes(), (self.site / relative / 'catalogue.json').read_bytes())

    def test_previous_ontology_version_cannot_replace_current(self):
        previous = self.folder / 'previous'
        shutil.copytree(self.site, previous)
        path = previous / 'publication.json'
        active = json.loads(path.read_text())
        active['ontology_version'] = str(int(active['ontology_version'].split('.')[0]) + 1) + '.0.0'
        publication.save_json(path, active)
        with self.assertRaisesRegex(ValueError, 'older ontology version'):
            publication.build(self.folder / 'output', previous, commit='8' * 40)

    def test_new_catalogue_keeps_earlier_metadata(self):
        stage = self.folder / 'site'
        stage.mkdir()
        publication.preserve_archives(self.site, stage)
        old = self.result['catalogue_release']
        candidate = self.folder / 'candidate'
        shutil.copytree(self.site / 'education/releases' / old, candidate)
        manifest = json.loads((candidate / 'manifest.json').read_text())
        manifest['release_id'] = 'a' * 24
        publication.save_json(candidate / 'manifest.json', manifest)
        publication.install_snapshot(candidate, stage / 'education/releases' / ('a' * 24))
        self.assertEqual({p.name for p in (stage / 'education/releases').iterdir()}, {old, 'a' * 24})
        for path in (self.site / 'education/releases' / old).iterdir():
            self.assertEqual(path.read_bytes(), (stage / path.relative_to(self.site)).read_bytes())


if __name__ == '__main__':
    unittest.main()
