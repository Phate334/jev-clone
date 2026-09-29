import unittest
from unittest.mock import patch

from jev import AsyncTypeSafeClient, TypeSafeClient
from jev.errors import JevError


class ConfigurationTests(unittest.TestCase):
    @patch.dict('os.environ', {}, clear=True)
    def test_defaults_and_automatic_detection_cache(self):
        client = TypeSafeClient()
        self.assertEqual(client.model, 'local-judge')
        with patch.object(client._backend, '_request', return_value={
            'data': [{'id': 'other', 'owned_by': 'unknown'},
                     {'id': 'local-judge', 'owned_by': 'llamacpp'}]
        }) as request:
            self.assertEqual(client._backend._detect(client.model), 'llama')
            self.assertEqual(client._backend._detect(client.model), 'llama')
            request.assert_called_once_with('GET', '/v1/models')

    @patch.dict('os.environ', {
        'JEV_MODEL': 'proxy-model', 'TYPESAFE_DEFAULT_MODEL': 'old-model',
        'JEV_BASE_URL': 'https://proxy.example/prefix/v1',
        'OPENAI_BASE_URL': 'https://old.example/v1',
        'JEV_API_KEY': 'new-key', 'OPENAI_API_KEY': 'old-key',
        'JEV_BACKEND': 'vllm',
    }, clear=True)
    def test_environment_priority_and_explicit_backend_skips_discovery(self):
        for cls in (TypeSafeClient, AsyncTypeSafeClient):
            client = cls()
            self.assertEqual(client.model, 'proxy-model')
            self.assertEqual(client._backend.base_url, 'https://proxy.example/prefix')
            self.assertEqual(client._backend.api_key, 'new-key')
            with patch.object(client._backend, '_request', side_effect=AssertionError('Unexpected discovery')), \
                 patch.object(client._backend, '_score_vllm', return_value='scored') as score:
                self.assertEqual(client._backend._score(client.model, [], ['A']), 'scored')
                score.assert_called_once_with('proxy-model', [], ['A'])
        client = TypeSafeClient(model='explicit', backend='llamacpp',
                                base_url='https://explicit.example/v1', api_key='')
        self.assertEqual(client.model, 'explicit')
        self.assertEqual(client._backend.base_url, 'https://explicit.example')
        self.assertEqual(client._backend.api_key, '')
        with patch.object(client._backend, '_request', side_effect=AssertionError('Unexpected discovery')), \
             patch.object(client._backend, '_score_llama', return_value='scored'):
            self.assertEqual(client._backend._score('explicit', [], ['A']), 'scored')
        self.assertEqual(TypeSafeClient(backend='auto')._backend.backend, 'auto')
        with patch.object(client, '_run', side_effect=RuntimeError('captured')) as run:
            with self.assertRaises(RuntimeError):
                client.system_one('state', {'q': {'type': 'noul'}}, model='per-call')
            self.assertEqual(run.call_args.args[0]['model'], 'per-call')

    @patch.dict('os.environ', {
        'TYPESAFE_DEFAULT_MODEL': 'legacy', 'OPENAI_BASE_URL': 'https://old.example/v1',
        'OPENAI_API_KEY': 'old-key',
    }, clear=True)
    def test_legacy_environment(self):
        client = TypeSafeClient()
        self.assertEqual(client.model, 'legacy')
        self.assertEqual(client._backend.base_url, 'https://old.example')
        self.assertEqual(client._backend.api_key, 'old-key')

    @patch.dict('os.environ', {'JEV_BACKEND': 'unsupported'}, clear=True)
    def test_invalid_backend_fails_before_network(self):
        with self.assertRaises(JevError):
            TypeSafeClient()
        self.assertEqual(TypeSafeClient(backend='vllm')._backend.backend, 'vllm')


if __name__ == '__main__':
    unittest.main()
