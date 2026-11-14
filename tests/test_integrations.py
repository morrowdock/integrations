import hashlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from morrowdock_integrations import validate, build_item, provenance, verification, sha256, coverage
from morrowdock_integrations.client import Client
from morrowdock_integrations.mock import make_server
from tools.check_changelog import entries, needs_changelog

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'contract/examples'


def fixture():
    return json.loads((EXAMPLES / 'valid/material.json').read_text())


def semantic_cases():
    for entry in json.loads((ROOT / 'tests/semantic-cases.json').read_text()):
        value = fixture() if entry['base'] == 'item' else json.loads((ROOT / 'tests/fixtures/request.json').read_text())
        for path, replacement in entry['changes']:
            parent = value
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = copy.deepcopy(replacement)
        yield entry, value


def example_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f'examples/{name}/run.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContractTests(unittest.TestCase):
    def test_shared_verdicts(self):
        for entry in json.loads((EXAMPLES / 'manifest.json').read_text()):
            with self.subTest(file=entry['file']):
                value = json.loads((EXAMPLES / entry['file']).read_text())
                try:
                    validate(value)
                    valid = True
                except ValueError as error:
                    valid = False
                    self.assertIn(entry['expectedError'].split(':')[0], str(error))
                js = subprocess.run(['node', 'bin/validate.js', str(EXAMPLES / entry['file'])], capture_output=True)
                self.assertEqual(valid, entry['valid'])
                self.assertEqual(js.returncode, 0 if valid else 1)

    def test_shared_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.json'
            for entry, value in semantic_cases():
                with self.subTest(case=entry['name']):
                    path.write_text(json.dumps(value))
                    if entry['valid']:
                        validate(value)
                    else:
                        with self.assertRaisesRegex(ValueError, 'semantic:'):
                            validate(value)
                    js = subprocess.run(['node', 'bin/validate.js', str(path)], capture_output=True)
                    self.assertEqual(js.returncode, 0 if entry['valid'] else 1)

    def test_schema_copies(self):
        for path in (ROOT / 'contract').glob('*.schema.json'):
            self.assertEqual(path.read_bytes(), (ROOT / 'morrowdock_integrations/schemas' / path.name).read_bytes())

    def test_helpers(self):
        item = build_item(kind='material', course='TEST 101', title='Fixture', summary='Fixture only',
                          source=provenance('manual'), verification={'/title': verification('verified', 'fixture')},
                          synthetic=True, coverage=coverage('partial', 'One fixture'))
        self.assertEqual(item['syntheticScope']['realAcademicFacts'], False)
        with tempfile.NamedTemporaryFile() as stream:
            stream.write(b'fixture'); stream.flush()
            self.assertEqual(sha256(stream.name), hashlib.sha256(b'fixture').hexdigest())

    def test_unknown_and_request(self):
        for value in ({}, [], {'schema': 'unknown'}, {'schema': []}):
            with self.assertRaises(ValueError):
                validate(value)
        with self.assertRaises(ValueError):
            build_item(kind='ai-draft', course='TEST 101', title='Fixture', summary='Fixture',
                       source=provenance('agent'), verification={'/title': verification('verified', 'fixture')},
                       synthetic=True, state={'submission': 'submitted'})

    def test_cli(self):
        for file, code in [('valid/material.json', 0), ('invalid/material.json', 1), ('missing.json', 1)]:
            result = subprocess.run([os.sys.executable, '-m', 'morrowdock_integrations', 'validate', str(EXAMPLES / file)], capture_output=True)
            self.assertEqual(result.returncode, code)


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'MORROWDOCK_TOKEN': 'synthetic-local-test'})
        self.env.start()
        self.server = make_server(os.environ['MORROWDOCK_TOKEN'])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.client = Client(self.url)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.env.stop()

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.md'
            path.write_text('Synthetic TEST 101')
            attachment = self.client.upload(path, 'text/markdown')
            item = fixture(); item['attachments'] = [attachment]
            self.assertEqual(self.client.send(item)['id'], item['id'])
        requests = self.client.requests()
        self.assertEqual(len(requests), 1)
        answer = fixture(); answer.update(kind='answer', id='00000000-0000-4000-8000-000000000022', inReplyTo=requests[0]['id'])
        self.client.answer(requests[0]['id'], answer)
        self.assertEqual(self.client.requests(), [])
        self.assertEqual(self.client.status()['items'], 2)
        with self.assertRaises(RuntimeError):
            self.client.answer(requests[0]['id'], answer)

    def test_relay_semantics(self):
        for entry, value in semantic_cases():
            if entry['base'] == 'item' and not entry['valid']:
                with self.subTest(case=entry['name']):
                    # Raw transport bypasses the SDK's local validator.
                    with self.assertRaises(RuntimeError):
                        self.client._call('POST', '/v1/items', value)
        self.assertEqual(self.client.status()['items'], 0)

    def test_unknown_request_reference(self):
        for kind in ('material', 'answer'):
            item = fixture(); item.update(kind=kind, inReplyTo='00000000-0000-4000-8000-000000000099')
            with self.assertRaises(RuntimeError): self.client.send(item)
        self.assertEqual(self.client.status()['items'], 0)
        item['inReplyTo'] = self.client.requests()[0]['id']
        self.client.send(item)
        self.assertEqual(self.client.status()['items'], 1)

    def test_supersedes_identity(self):
        original = fixture(); original['source']['agent'] = 'synthetic-agent'
        revision = copy.deepcopy(original)
        revision.update(id='00000000-0000-4000-8000-000000000022', supersedes=original['id'], version=2)
        with self.assertRaises(RuntimeError): self.client.send(revision)
        self.client.send(original)
        for agent in ('another-synthetic-agent', '', None):
            wrong = copy.deepcopy(revision)
            if agent is None:
                del wrong['source']['agent']
            else:
                wrong['source']['agent'] = agent
            with self.assertRaises(RuntimeError): self.client.send(wrong)
        self.assertEqual(self.client.status()['items'], 1)
        self.client.send(revision)
        self.assertEqual(self.client.status()['items'], 2)

    def test_missing_agents_do_not_establish_identity(self):
        original = fixture(); self.client.send(original)
        revision = copy.deepcopy(original)
        revision.update(id='00000000-0000-4000-8000-000000000022', supersedes=original['id'], version=2)
        with self.assertRaises(RuntimeError): self.client.send(revision)
        self.assertEqual(self.client.status()['items'], 1)

    def test_auth(self):
        with patch.dict(os.environ, {'MORROWDOCK_TOKEN': 'wrong-synthetic-value'}):
            with self.assertRaisesRegex(RuntimeError, '^Relay request failed$'):
                Client(self.url).status()

    def test_pre_send_validation(self):
        item = fixture(); del item['source']
        with patch.object(self.client, '_call') as call:
            with self.assertRaises(ValueError): self.client.send(item)
            call.assert_not_called()

    def test_hash_mismatch(self):
        metadata = dict(name='fixture.md', mime='text/markdown', size=1, sha256='0' * 64)
        upload = self.client._call('POST', '/v1/uploads', metadata)
        with self.assertRaises(RuntimeError):
            self.client._call('PUT', '/v1/uploads/' + upload['uploadId'], b'x', binary=True)

    def test_relay_validation(self):
        item = fixture(); item['synthetic'] = False; del item['syntheticScope']
        item['verification']['/title']['method'] = 'other'
        with self.assertRaises(RuntimeError): self.client._call('POST', '/v1/items', item)
        item = fixture(); item['extra'] = True
        with self.assertRaises(RuntimeError): self.client._call('POST', '/v1/items', item)
        item = fixture(); item['attachments'] = [dict(uploadId='a' * 32, name='x', mime='text/plain', size=1, sha256='0' * 64)]
        with self.assertRaises(RuntimeError): self.client.send(item)

    def test_answer_identity(self):
        request_id = self.client.requests()[0]['id']
        answer = fixture(); answer.update(kind='answer', inReplyTo=request_id)
        with self.assertRaises(ValueError):
            self.client.answer('00000000-0000-4000-8000-000000000099', answer)
        request = self.client.requests()[0]
        request.update(status='answered')
        with self.assertRaises(ValueError): validate(request)
        request.update(answeredBy=[answer['id']])
        validate(request)

    def test_duplicate_item(self):
        item = fixture()
        self.client.send(item)
        with self.assertRaises(RuntimeError): self.client.send(item)
        self.assertEqual(self.client.status()['items'], 1)

    def test_no_remote_http_or_redirect(self):
        for url in ('http://example.invalid', 'https://user:pass@example.invalid', 'https://example.invalid?secret=x'):
            with self.assertRaises(ValueError): Client(url)
        from morrowdock_integrations.client import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, None, None, None, None))

    def test_folder(self):
        module = example_module('folder-integration')
        seen = set()
        folder = ROOT / 'examples/folder-integration/demo'
        module.scan(folder, self.client, seen)
        module.scan(folder, self.client, seen)
        self.assertEqual(self.client.status()['items'], 1)

    def test_ics(self):
        module = example_module('ics-integration')
        text = (ROOT / 'examples/ics-integration/demo.ics').read_text()
        items = list(module.parse(text))
        self.assertEqual([i['kind'] for i in items], ['exam', 'assignment'])
        for item in items:
            self.assertNotEqual(item['dates']['due'], item['dates']['availableUntil'])
            self.client.send(item)
        with self.assertRaises(ValueError): list(module.parse(text.replace('DTSTART:', 'DTSTART;TZID=Unknown:')))
        no_due = text.replace('X-MORROWDOCK-DUE:20261201T150000Z\n', '')
        self.assertNotIn('due', list(module.parse(no_due))[0]['dates'])


class ChangelogTests(unittest.TestCase):
    base = '## [Unreleased]\n### Added\n- Old entry.\n'

    def test_new_entry(self):
        self.assertFalse(needs_changelog(['README.md', 'CHANGELOG.md'], base_text=self.base, head_text=self.base + '- New entry.\n'))

    def test_preserve_old(self):
        self.assertTrue(needs_changelog(['CHANGELOG.md'], base_text=self.base, head_text=self.base.replace('Old', 'New')))

    def test_comments_fences_categories(self):
        for suffix in ('<!--\n- Hidden\n-->', '```\n- Hidden\n```', '~~~\n- Hidden\n~~~ trailing\n- Still hidden', '### Other\n- Hidden', '## [1.0.0]\n### Added\n- Released'):
            self.assertTrue(needs_changelog(['CHANGELOG.md'], base_text=self.base, head_text=self.base + suffix))

    def test_closing_fence(self):
        self.assertEqual(entries('## [Unreleased]\n### Added\n```\n- hidden\n```  \n- visible'), {'visible'})


class DCOTests(unittest.TestCase):
    def test_matching_author(self):
        from tools.check_dco import main
        for trailer, expected in [('Signed-off-by: Fixture Author <fixture@example.invalid>\n', 0), ('', 1),
                                  ('Signed-off-by: Other <other@example.invalid>\n', 1)]:
            with patch('tools.check_dco.subprocess.check_output', side_effect=[
                'a' * 40 + '\n', 'Fixture Author <fixture@example.invalid>\n', 'Message\n', trailer
            ]):
                self.assertEqual(main('b' * 40, 'a' * 40), expected)

    def test_invalid_commit(self):
        from tools.check_dco import main
        with self.assertRaises(ValueError): main('main', 'HEAD')


class EmailPolicyTests(unittest.TestCase):
    def test_fixture_addresses(self):
        from tools.check_emails import fixture_emails_allowed
        for directory in ('tests', 'examples', 'contract/examples'):
            for path in (ROOT / directory).rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    self.assertTrue(fixture_emails_allowed(path.read_text()), str(path))

    def test_metadata_only_exceptions(self):
        from tools.check_emails import AUTHOR, COAUTHOR, fixture_emails_allowed, metadata_allowed
        self.assertTrue(fixture_emails_allowed('learner@example.invalid'))
        self.assertFalse(fixture_emails_allowed(AUTHOR))
        self.assertFalse(fixture_emails_allowed(COAUTHOR))
        message = 'Change\n\nSigned-off-by: ' + AUTHOR + '\nCo-Authored-By: ' + COAUTHOR + '\n'
        self.assertTrue(metadata_allowed(AUTHOR, AUTHOR, message))
        self.assertFalse(metadata_allowed(AUTHOR, AUTHOR, 'Mention ' + COAUTHOR))
        self.assertFalse(metadata_allowed(COAUTHOR, AUTHOR, message))
        self.assertFalse(metadata_allowed(AUTHOR, AUTHOR, 'Signed-off-by: ' + COAUTHOR))


if __name__ == '__main__':
    unittest.main()
