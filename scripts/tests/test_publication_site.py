"""Test the post-deployment checker against HTTP responses from a built site."""
from email.message import Message
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_publication
import check_publication_site


class Response(io.BytesIO):
    def __init__(self, content, media):
        super().__init__(content)
        self.headers = Message()
        self.headers['Content-Type'] = media


class SiteChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.site = Path(cls.temporary.name) / 'site'
        build_publication.build(cls.site, commit='9' * 40)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def response(self, request, **_):
        relative = request.full_url.removeprefix('https://publication.example/')
        path = self.site / relative
        media = {'.ttl': 'text/turtle', '.rdf': 'application/rdf+xml', '.json': 'application/json'}[path.suffix]
        body = path.read_bytes()
        if relative == 'current/ontology.ttl':
            if getattr(self, 'bad_media', False):
                media = 'text/plain'
            if getattr(self, 'tamper', False):
                body += b'\n'
        return Response(body, media)

    def test_live_checker_loads_both_current_and_archived_import_closures(self):
        with patch.object(check_publication_site, 'urlopen', side_effect=self.response):
            result = check_publication_site.verify_site('https://publication.example/')
        self.assertEqual(result['status'], 'PASS')
        expected = json.loads((self.site / 'education/current/catalogue.json').read_text())
        self.assertEqual(result['resources'], len(expected['records']))
        _, documents = build_publication.ontology_payloads(build_publication.ROOT)
        self.assertEqual(result['rdf_documents_loaded'], 2 * (len(documents) + 3))

    def test_incorrect_rdf_media_type_is_rejected(self):
        self.bad_media = True
        with patch.object(check_publication_site, 'urlopen', side_effect=self.response):
            with self.assertRaisesRegex(ValueError, 'expected text/turtle'):
                check_publication_site.verify_site('https://publication.example/')

    def test_deployed_bytes_must_match_their_manifest(self):
        self.tamper = True
        with patch.object(check_publication_site, 'urlopen', side_effect=self.response):
            with self.assertRaisesRegex(ValueError, 'manifest hash'):
                check_publication_site.verify_site('https://publication.example/')


if __name__ == '__main__':
    unittest.main()
