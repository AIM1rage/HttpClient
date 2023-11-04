import asyncio
from asyncio import StreamReader, StreamWriter
from urllib.parse import urlparse
from collections import deque
from typing import Optional, AsyncIterator
from loguru import logger
from src.http_request import HttpRequest
from src.http_response import HttpResponse
from src.serializer import Serializer

HAVING_BODY_METHODS = ['PUT', 'POST', 'PATCH']
METHODS = ['TRACE', 'GET', 'POST', 'HEAD', 'CONNECT', 'DELETE', 'OPTIONS',
           'PATCH', 'PUT']


class UnknownContentError(Exception):
    ...


class BadRequestError(Exception):
    ...


class HttpClient:
    def __init__(self):
        self.reader: StreamReader = None
        self.writer: StreamWriter = None

        self.cookie_jar: dict[str, dict[str, str]] = Serializer.load_cookies()

        self.last_connection: tuple[str, int] = None
        self.is_connected: bool = False

    async def connect(self, url: str):
        host, port, ssl = HttpClient.extract_host_port_ssl(url)
        self.reader, self.writer = await asyncio.open_connection(
            host, port, ssl=ssl
        )
        self.last_connection = (host, port)
        self.is_connected = True

    async def get_response(self,
                           request: HttpRequest,
                           timeout: int | float,
                           path: str,
                           ) -> HttpResponse:
        self.add_cookies(request)

        await self.configure_connection(request=request)

        response = await asyncio.wait_for(
            self.receive_response(request),
            timeout)
        self.extract_cookies(request, response)

        await self.configure_connection(response=response)

        if path:
            Serializer.save_response(path, response)

        await asyncio.sleep(1)
        return response

    async def receive_response(self, request: HttpRequest) -> HttpResponse:
        await self.send(request)
        status_code, headers, status_line = await self.receive_response_information()
        if request.method != 'HEAD':
            content = await self.receive_response_content(headers)
        else:
            content = b''
        return HttpResponse(status_code, status_line, headers, content)

    async def send(self, request: HttpRequest):
        logger.info(f'Sending request: {request.build_request()}')
        self.writer.write(request.build_request())
        await self.writer.drain()
        await asyncio.sleep(0.01)

    async def receive_response_information(self) -> tuple[
        int, dict[str, str], str]:
        info = (await asyncio.wait_for(self.reader.readuntil(b'\r\n\r\n'),
                                       10)).decode()
        status_line = info.split('\r\n')[0]
        status_code = int(status_line.split()[1])
        headers = {line.split(':')[0]: ':'.join(line.split(':')[1:]).strip()
                   for line
                   in info.split('\r\n')[1:-2]}
        logger.info(f'Receiving status code: {status_code}')
        logger.info(f'Receiving headers: {headers}')
        await asyncio.sleep(0.01)
        return status_code, headers, status_line

    async def receive_response_content(self, headers: dict[str, str]) -> bytes:
        if headers.get('Transfer-Encoding') == 'chunked':
            content = []
            while True:
                chunk_size = (
                    await self.reader.readuntil(b'\r\n')).decode().strip()
                chunk_size = int(chunk_size, base=16)
                chunk = await self.reader.readexactly(chunk_size)
                crlf = await self.reader.readuntil(b'\r\n')
                logger.info(f'Receiving chunk sized {chunk_size}: {chunk}')
                if chunk_size == 0:
                    break
                content.append(chunk)
            content = b''.join(content)
            del headers['Transfer-Encoding']
            headers['Content-Length'] = str(len(content))
            logger.info(f'Receiving content: ...')
            await asyncio.sleep(0.01)
            return content
        if 'Content-Length' in headers:
            content_length = int(headers['Content-Length'])
            content = await self.reader.readexactly(content_length)
            logger.info(f'Receiving content: ...')
            await asyncio.sleep(0.01)
            return content
        raise UnknownContentError

    async def configure_connection(self,
                                   request: HttpRequest = None,
                                   response: HttpResponse = None):
        if request is not None:
            host, port, _ = HttpClient.extract_host_port_ssl(request.full_url)
            if not self.is_connected:
                await self.connect(request.full_url)
                return
            if self.is_connected and (host, port) != self.last_connection:
                await self.close()
                await self.connect(request.full_url)
                return
        if response is not None and response.headers['Connection'] == 'close':
            self.is_connected = False
            await self.close()
            return

    async def close(self):
        self.is_connected = False
        self.writer.close()
        await self.writer.wait_closed()

    @staticmethod
    def extract_host_port_ssl(url: str) -> tuple[str, int, bool]:
        url = urlparse(url)
        if url.scheme == 'https':
            return url.hostname, 443, True
        else:
            return url.hostname, 80, False

    def add_cookies(self, request: HttpRequest):
        full_path = Serializer.get_full_path(request)
        if full_path in self.cookie_jar:
            cookies = []
            for name, value in self.cookie_jar[full_path].items():
                cookies.append(f'{name}={value}')
            request.add_header('Cookie', ', '.join(cookies))

    def extract_cookies(self, request: HttpRequest, response: HttpResponse):
        full_path = Serializer.get_full_path(request)
        if response.has_header('Set-Cookie'):
            cookie = response.headers['Set-Cookie'].split('; ')[0]
            name, value = cookie.split('=')
            self.cookie_jar.setdefault(full_path, {})[name] = value
            Serializer.dump_cookies(self.cookie_jar)

    async def request(self,
                      method: str,
                      url: str,
                      headers: Optional[dict[str, str]] = {},
                      content: Optional[bytes] = b'',
                      timeout: Optional[int | float] = 5,
                      path: Optional[str] = '',
                      ) -> HttpResponse:
        host = urlparse(url).hostname

        headers = {} if headers else headers

        headers |= {'Host': host,
                    'Connection': 'keep-alive',
                    'Content-Length': str(len(content)),
                    }

        if method.upper() not in METHODS:
            raise BadRequestError(f'Invalid method {method}')

        if content and method.upper() not in HAVING_BODY_METHODS:
            raise BadRequestError(
                f"Request with specified method ({method}) doesn't have body")

        request = HttpRequest(url,
                              method=method.upper(),
                              headers=headers,
                              data=content
                              )

        return await self.get_response(request, timeout, path)


async def main():
    # url1 = 'https://ulearn.me/Course/BasicProgramming/Praktika_Mediannyy_fil_tr__4597a6db-5f8e-4bad-a435-8755a3cb61b5'
    url2 = 'https://ulearn.me/Course/cs2/MazeBuilder_9ccc789a-9c35-4757-9194-6154c9f1d503'
    # url1 = 'https://kadm.kmath.ru/news.php'
    # url2 = 'https://kadm.kmath.ru/news.php'
    # url1 = url2 = 'https://alexbers.com/'
    # url1 = url2 = 'https://yandex.ru/'
    # url1 = url2 = 'https://developer.mozilla.org/en-US/docs/Glossary/Payload_header'
    # url1 = url2 = 'http://www.china.com.cn/'
    # url1 = url2 = 'http://government.ru/'
    url1 = 'https://urgu.org/151'
    # url1 = url2 = 'https://www.example.com'
    client = HttpClient()
    # await client.connect(url1)
    for method in HAVING_BODY_METHODS:
        await client.request(method, url2,
                             content=b'aboba',
                             path=f'{method}.txt',
                             timeout=3)
    for method in (m for m in METHODS if m not in HAVING_BODY_METHODS):
        await client.request(method, url1,
                             path=f'{method}.txt',
                             timeout=3)
    await client.close()


if __name__ == '__main__':
    asyncio.run(main())
