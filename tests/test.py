import asyncio
import unittest
from src.http_client import HttpClient
from src.http_client import METHODS, HAVING_BODY_METHODS


class HttpClientTest(unittest.TestCase):
    def test_client_has_cookie(self):
        asyncio.run(self.test_async_client_has_cookie())

    async def test_async_client_has_cookie(self):
        client = HttpClient()
        url = 'https://anytask.org/'
        client.request('GET', url)
        client.close()
        async for _ in client.get_responses():
            ...
        self.assertIn('anytask.org/', client.cookie_jar)

    def test_all_methods_work(self):
        asyncio.run(self.test_async_all_methods_work())

    async def test_async_all_methods_work(self):
        client = HttpClient()
        url = 'https://urgu.org/150'
        for method in HAVING_BODY_METHODS:
            client.request(method, url,
                           content=b'aboba',
                           timeout=3)
        for method in (m for m in METHODS if m not in HAVING_BODY_METHODS):
            client.request(method, url,
                           timeout=3)
        client.close()
        responses = [response async for response in client.get_responses()]
        self.assertEqual(len(METHODS), len(responses))


if __name__ == '__main__':
    unittest.main()
