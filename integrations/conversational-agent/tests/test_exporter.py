"""Test real ontology projection and protected agent refresh behaviour."""
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from rdflib import URIRef, Literal
from rdflib.namespace import RDFS, SKOS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_agent_models as exporter


class AgentExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temporary.name)
        cls.bundle = cls.folder / 'bundle'
        exporter.export_bundle(cls.bundle)
        cls.manifest, cls.models, cls.index = exporter.verify_bundle(cls.bundle)
        cls.graph, cls.ontology = exporter.load_ontology(exporter.ROOT / 'serialisation')
        cls.profile = exporter.read_json(exporter.HERE / 'profile.json')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.work = Path(tempfile.mkdtemp(dir=self.folder))
        self.addCleanup(shutil.rmtree, self.work)

    def agent(self, missing=False):
        folder = self.work / 'agent'
        model = deepcopy(self.models['clinical_profile'])
        model['agent_contracts'] = {'supervisor': {'inject': 'Only relevant personal context'}}
        model['procedure_contracts'] = [{'id': 'policy_owned_by_agent', 'required_steps': ['preserve this instruction']}]
        model['custom_agent_setting'] = {'nested': [1, 2, 3]}
        model['memory_bindings'] = [{'path': 'clinical_profile.medications',
                                    'node': 'missing_record' if missing else 'medication_record', 'status': 'active',
                                    'capture': {'properties_schema': {'type': 'object', 'properties': {'name': {'type': 'string'}}},
                                                'relation_mappings': {'name': 'medication_record_records_medication'},
                                                'identity_fields': ['name'], 'update_mode': 'supersede'}}]
        exporter.save_json(folder / 'clinical_profile/model.json', model)
        manifest = {'schema_version': 'agent-custom-schema', 'runtime': {'memory_policy': {'allow_inference': False},
                     'agent_defaults': {'health_rag': ['clinical_profile']}}, 'custom_setting': ['preserve'],
                    'models': [{'model_id': 'clinical_profile', 'path': 'clinical_profile/model.json', 'agent_priority': 3}]}
        exporter.save_json(folder / 'manifest.json', manifest)
        return folder, manifest, model

    def test_all_modules_and_complete_local_signature_are_exported(self):
        expected = exporter.read_json(exporter.ROOT / 'serialisation/validation/build-report.json')
        self.assertEqual(len(self.models), len(self.profile['models']))
        local = [v for v in self.index['entities'].values() if not v['external']]
        self.assertEqual(sum(v['kind'] == 'class' for v in local), expected['schema_counts']['Class'])
        self.assertEqual(sum(v['kind'] == 'individual' for v in local), expected['controlled_values'] + expected['concept_schemes'])
        self.assertEqual(len(self.index['object_properties']), expected['schema_counts']['ObjectProperty'])
        self.assertEqual(len(self.index['data_properties']), expected['schema_counts']['DatatypeProperty'])
        for model in self.models.values():
            self.assertFalse(model['memory_bindings'])
            self.assertFalse(model['agent_contracts'])
            self.assertFalse(model['procedure_contracts'])
            self.assertFalse(exporter.validate_model(model, self.index))

    def test_stable_active_binding_identifiers_use_canonical_properties(self):
        prop = self.index['object_properties']['clinical_condition_record_records_condition']
        self.assertEqual(prop['iri'], exporter.BASE + 'conditionRecordRecordsCondition')
        self.assertEqual(prop['domain'], 'clinical_condition_record')
        self.assertEqual(prop['range'], 'clinical_condition')
        self.assertEqual(self.index['object_properties']['cancer_treatment_record_has_treatment_period']['range'], 'time_interval')

    def test_controlled_values_are_instances_not_subclasses(self):
        value = self.index['entities']['brief_information']
        self.assertEqual(value['kind'], 'individual')
        self.assertIn('information_detail_level_value', value['types'])
        self.assertFalse(value['parents'])
        groups = self.models['person_role']['taxonomy_groups']
        self.assertTrue(any(g['interpretation'] == 'instance' and 'brief_information' in g['members'] for g in groups))

    def test_datatypes_definitions_and_iris_are_available_in_sidecar(self):
        self.assertEqual(self.index['data_properties']['interval_duration']['datatype'], 'http://www.w3.org/2001/XMLSchema#string')
        self.assertTrue(self.index['data_properties']['interval_duration']['value_pattern'])
        self.assertTrue(self.index['entities']['person']['definition'])
        self.assertEqual(self.index['entities']['person']['iri'], exporter.BASE + 'Person')

    def test_model_nodes_and_relations_include_the_ontology_descriptions(self):
        for model in self.models.values():
            for node in model['nodes']:
                entry = self.index['entities'][node['id']]
                self.assertEqual(node['description'], entry['definition'])
                if not entry['external'] and entry['kind'] == 'class':
                    self.assertTrue(node['description'])
            for relation in model['relations']:
                self.assertEqual(relation['description'], self.index['object_properties'][relation['id']]['definition'])
                self.assertTrue(relation['description'])

    def test_descriptions_cannot_drift_from_the_canonical_source(self):
        model = deepcopy(self.models['clinical_profile'])
        model['nodes'][0]['description'] = 'An unsupported description.'
        with self.assertRaisesRegex(ValueError, 'Node description differs'):
            exporter.validate_model(model, self.index)
        model = deepcopy(self.models['clinical_profile'])
        model['relations'][0]['description'] = 'An unsupported relation meaning.'
        with self.assertRaisesRegex(ValueError, 'Relation description differs'):
            exporter.validate_model(model, self.index)

    def test_generation_is_byte_deterministic(self):
        output = self.work / 'second'
        result = exporter.export_bundle(output)
        self.assertEqual(result['bundle_id'], self.manifest['bundle_id'])
        for path in self.bundle.rglob('*.json'):
            self.assertEqual(path.read_bytes(), (output / path.relative_to(self.bundle)).read_bytes())

    def test_selected_modules_keep_referenced_entities(self):
        output = self.work / 'selected'
        exporter.export_bundle(output, selected=['clinical_profile'])
        _, models, _ = exporter.verify_bundle(output)
        self.assertEqual(set(models), {'clinical_profile'})
        ids = {n['id'] for n in models['clinical_profile']['nodes']}
        self.assertIn('measurement_event', ids)

    def test_refresh_preserves_all_agent_settings_and_original_inputs(self):
        folder, manifest, model = self.agent()
        original = {p.relative_to(folder): p.read_bytes() for p in folder.rglob('*.json')}
        output = self.work / 'refreshed'
        result = exporter.refresh(folder, self.bundle, output)
        self.assertEqual(result['status'], 'READY_FOR_AGENT_TESTS')
        new = exporter.read_json(output / 'candidate-models/clinical_profile/model.json')
        for key in model.keys() - exporter.STRUCTURAL:
            self.assertEqual(new[key], model[key])
        new_manifest = exporter.read_json(output / 'candidate-models/manifest.json')
        self.assertEqual(new_manifest['runtime'], manifest['runtime'])
        self.assertEqual(new_manifest['schema_version'], manifest['schema_version'])
        self.assertEqual(new_manifest['models'][0]['agent_priority'], 3)
        for path, data in original.items():
            self.assertEqual((folder / path).read_bytes(), data)

    def test_missing_binding_target_requires_review_without_deactivation(self):
        folder, _, _ = self.agent(missing=True)
        output = self.work / 'candidate'
        result = exporter.refresh(folder, self.bundle, output)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertTrue(result['issues'])
        new = exporter.read_json(output / 'candidate-models/clinical_profile/model.json')
        self.assertEqual(new['memory_bindings'][0]['status'], 'active')

    def test_missing_capture_relation_requires_review(self):
        _, _, model = self.agent()
        model['relations'] = [r for r in model['relations'] if r['id'] != 'medication_record_records_medication']
        self.assertTrue(any('Capture relation is absent' in i['message'] for i in exporter.validate_model(model, self.index)))

    def test_binding_cannot_use_a_property_with_incompatible_domain(self):
        _, _, model = self.agent()
        model['memory_bindings'][0]['capture']['relation_mappings']['name'] = 'clinical_condition_record_records_condition'
        issues = exporter.validate_model(model, self.index)
        self.assertTrue(any('incompatible' in i['message'] for i in issues))

    def test_definition_changes_appear_in_change_report(self):
        graph = deepcopy(self.graph)
        person = URIRef(exporter.BASE + 'Person')
        graph.set((person, SKOS.definition, Literal('Updated formal definition for the test.')))
        _, changed = exporter.project(graph, self.ontology, self.profile)
        result = exporter.index_changes(self.index, changed)
        self.assertEqual(result['entities']['modified'], ['person'])

    def test_label_change_keeps_the_existing_entity_id(self):
        graph = deepcopy(self.graph)
        graph.set((URIRef(exporter.BASE + 'Person'), RDFS.label, Literal('Updated person label', lang='en')))
        models, index = exporter.project(graph, self.ontology, self.profile)
        self.assertEqual(index['entities']['person']['iri'], exporter.BASE + 'Person')
        node = next(n for n in models['person_role']['nodes'] if n['id'] == 'person')
        self.assertEqual(node['label'], 'Updated person label')

    def test_property_direction_changes_are_rejected(self):
        model = deepcopy(self.models['clinical_profile'])
        relation = model['relations'][0]
        relation['from'], relation['to'] = relation['to'], relation['from']
        with self.assertRaisesRegex(ValueError, 'direction/range differs'):
            exporter.validate_model(model, self.index)

    def test_corrupt_payload_is_rejected(self):
        folder = self.work / 'corrupt'
        shutil.copytree(self.bundle, folder)
        (folder / 'clinical_profile/model.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            exporter.verify_bundle(folder)

    def test_extra_files_and_symlinks_are_rejected(self):
        folder = self.work / 'extra'
        shutil.copytree(self.bundle, folder)
        (folder / 'unexpected.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            exporter.verify_bundle(folder)
        (folder / 'unexpected.json').unlink()
        (folder / 'link').symlink_to(self.bundle / 'manifest.json')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            exporter.verify_bundle(folder)

    def test_manifest_cannot_smuggle_extra_payloads_under_a_pinned_id(self):
        folder = self.work / 'extra-payload'
        shutil.copytree(self.bundle, folder)
        payload = folder / 'unexpected.py'
        payload.write_text('This is not an ontology payload.')
        manifest = exporter.read_json(folder / 'manifest.json')
        manifest['files']['unexpected.py'] = exporter.digest(payload.read_bytes())
        exporter.save_json(folder / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'unexpected payloads'):
            exporter.verify_bundle(folder)

    def test_pinned_identifier_covers_manifest_provenance(self):
        folder = self.work / 'modified'
        shutil.copytree(self.bundle, folder)
        manifest = exporter.read_json(folder / 'manifest.json')
        manifest['ontology']['version'] = '9.9.9'
        exporter.save_json(folder / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'identifier does not match'):
            exporter.verify_bundle(folder)

    def test_complex_property_constraints_do_not_become_alternative_edges(self):
        graph = deepcopy(self.graph)
        graph.add((URIRef(exporter.BASE + 'personHasRole'), RDFS.domain, URIRef(exporter.BASE + 'ClinicalRecord')))
        with self.assertRaisesRegex(ValueError, 'multiple domain/range'):
            exporter.project(graph, self.ontology, self.profile)

    def test_undeclared_local_range_is_not_invented_as_a_class(self):
        graph = deepcopy(self.graph)
        graph.set((URIRef(exporter.BASE + 'personHasRole'), RDFS.range, URIRef(exporter.BASE + 'MissingClass')))
        with self.assertRaisesRegex(ValueError, 'not a declared class'):
            exporter.project(graph, self.ontology, self.profile)

    def test_profile_cannot_create_duplicate_ids_or_escape_output(self):
        profile = deepcopy(self.profile)
        profile['node_ids'][exporter.BASE + 'ClinicalRecord'] = 'person'
        with self.assertRaisesRegex(ValueError, 'Duplicate identifiers'):
            exporter.project(self.graph, self.ontology, profile)
        profile = deepcopy(self.profile)
        profile['models']['../outside'] = {'module': 'core', 'title': 'Invalid'}
        with self.assertRaisesRegex(ValueError, 'Unsafe profile'):
            exporter.project(self.graph, self.ontology, profile)

    def response(self, request, **_):
        class Response(io.BytesIO):
            def geturl(self):
                return 'https://models.example/'
        path = request.full_url.removeprefix('https://models.example/')
        return Response((self.bundle / path).read_bytes())

    def test_download_checks_the_pinned_bundle_before_installation(self):
        output = self.work / 'download'
        with patch.object(exporter, 'urlopen', side_effect=self.response):
            result = exporter.download('https://models.example/', output, self.manifest['bundle_id'])
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(exporter.verify_bundle(output)[0]['bundle_id'], self.manifest['bundle_id'])

    def test_wrong_pin_and_unsafe_urls_leave_no_output(self):
        output = self.work / 'failed'
        with patch.object(exporter, 'urlopen', side_effect=self.response):
            with self.assertRaisesRegex(ValueError, 'pinned identifier'):
                exporter.download('https://models.example/', output, 'a' * 24)
        self.assertFalse(output.exists())
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            exporter.download('http://models.example/', output)
        with self.assertRaisesRegex(ValueError, 'Unsafe bundle path'):
            exporter.relative_path('../escape.json')

    def test_output_cannot_overwrite_an_existing_agent_directory(self):
        folder, _, _ = self.agent()
        with self.assertRaisesRegex(ValueError, 'cannot replace agent inputs'):
            exporter.refresh(folder, self.bundle, folder)


if __name__ == '__main__':
    unittest.main()
