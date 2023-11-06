import asyncio
import unittest
from src.domain.http_client import HttpClient
from src.domain.http_client import METHODS, HAVING_BODY_METHODS


class HttpClientTest(unittest.TestCase):
    def test_client_has_cookie(self):
        asyncio.run(self.test_async_client_has_cookie())

    async def test_async_client_has_cookie(self):
        client = HttpClient()
        url = 'https://anytask.org/'
        response = await client.request('GET', url)
        await client.close()
        self.assertIn('anytask.org/', client.cookie_jar)

    def test_all_methods_work(self):
        asyncio.run(self.test_async_all_methods_work())

    async def test_async_all_methods_work(self):
        client = HttpClient()
        url = 'https://urgu.org/150'
        responses = []
        for method in HAVING_BODY_METHODS:
            with open('test_content.txt', 'rb') as file_content:
                responses.append(await client.request(method, url,
                                                      file_content=file_content,
                                                      timeout=3))
        for method in (m for m in METHODS if m not in HAVING_BODY_METHODS):
            responses.append(await client.request(method, url,
                                                  timeout=3))
        await client.close()
        self.assertEqual(len(METHODS), len(responses))


if __name__ == '__main__':
    unittest.main()
