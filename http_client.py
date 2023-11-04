import asyncio
from asyncio import StreamReader, StreamWriter
from urllib.parse import urlparse
from collections import deque
from typing import Optional
from loguru import logger
from http_request import HttpRequest
from http_response import HttpResponse
from serializer import Serializer


class UnknownContentError(Exception):
    ...


class HttpClient:
    def __init__(self):
        self.reader: StreamReader = None
        self.writer: StreamWriter = None

        self.cookie_jar: dict[str, dict[str, str]] = Serializer.load_cookies()

        self.requests: deque[tuple[HttpRequest, int | float, str]] = deque()

    async def connect(self, url):
        url = urlparse(url)
        if url.scheme == 'https':
            self.reader, self.writer = await asyncio.open_connection(
                url.hostname, 443, ssl=True
            )
        else:
            self.reader, self.writer = await asyncio.open_connection(
                url.hostname, 80
            )

    async def handle(self):
        consume_task = asyncio.create_task(self.consume())
        done, pending = await asyncio.wait(
            [consume_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

    async def consume(self):
        while True:
            if self.requests:
                request, timeout, path = self.requests.popleft()
                self.add_cookies(request)
                response = await asyncio.wait_for(
                    self.receive_response(request),
                    timeout)
                self.extract_cookies(request, response)
                if path:
                    Serializer.save_response(path, response)
                await asyncio.sleep(1)

    async def receive_response(self, request: HttpRequest) -> HttpResponse:
        await self.send(request)
        status_code, headers, status_line = await self.receive_response_information()
        content = await self.receive_response_content(headers)
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
            logger.info(f'Receiving content: {content}')
            await asyncio.sleep(0.01)
            return content
        if 'Content-Length' in headers:
            content_length = int(headers['Content-Length'])
            content = await self.reader.readexactly(content_length)
            logger.info(f'Receiving content: {content}')
            await asyncio.sleep(0.01)
            return content
        raise UnknownContentError

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

    def request(self,
                method: str,
                url: str,
                headers: Optional[dict[str, str]] = {},
                content: Optional[bytes] = b'',
                timeout: Optional[int | float] = 5,
                path: Optional[str] = '',
                ):
        host = urlparse(url).hostname

        headers = {} if headers else headers

        headers |= {'Host': host,
                    'Connection': 'keep-alive',
                    'Content-Length': f'{len(content)}',
                    }

        request = HttpRequest(url,
                              method=method,
                              headers=headers,
                              data=content,
                              )
        self.requests.append((request, timeout, path))


async def main():
    # url1 = 'https://ulearn.me/Course/BasicProgramming/Praktika_Mediannyy_fil_tr__4597a6db-5f8e-4bad-a435-8755a3cb61b5'
    # url2 = 'https://ulearn.me/Course/cs2/MazeBuilder_9ccc789a-9c35-4757-9194-6154c9f1d503'
    # url1 = 'https://kadm.kmath.ru/news.php'
    # url2 = 'https://kadm.kmath.ru/news.php'
    url1 = url2 = 'https://alexbers.com/'
    # url1 = url2 = 'https://yandex.ru/'
    # url1 = url2 = 'https://developer.mozilla.org/en-US/docs/Glossary/Payload_header'
    # url1 = url2 = 'http://www.china.com.cn/'
    # url1 = url2 = 'http://government.ru/'
    # url1 = url2 = 'https://anytask.org'
    client = HttpClient()
    await client.connect(url1)
    client.request('POST', url2, content=b'aboba', path='post', timeout=3)
    client.request('GET', url1, path='get')
    await client.handle()


if __name__ == '__main__':
    asyncio.run(main())
