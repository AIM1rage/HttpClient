import asyncio
from asyncio import StreamReader, StreamWriter

from urllib.parse import urlparse

from typing import Optional, BinaryIO

from prompt_toolkit.shortcuts import ProgressBar

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
    def __init__(self, progress_bar=Optional[ProgressBar]):
        self.reader: StreamReader = None
        self.writer: StreamWriter = None

        self.verbose: int = 1
        self.progress_bar = progress_bar

        self.cookie_jar: dict[str, dict[str, str]] = Serializer.load_cookies()

        self.last_connection: tuple[str, int] = None
        self.is_connected: bool = False

    async def _connect(self, url: str):
        host, port, ssl = Serializer.extract_host_port_ssl(url)
        self.reader, self.writer = await asyncio.open_connection(
            host, port, ssl=ssl
        )
        self.last_connection = (host, port)
        self.is_connected = True

    async def _get_response(self,
                            request: HttpRequest,
                            timeout: int | float,
                            file_response: BinaryIO,
                            ) -> HttpResponse:
        self._add_cookies(request)

        await self._configure_connection(request=request)

        response = await asyncio.wait_for(
            self._receive_response(request),
            timeout)
        self._extract_cookies(request, response)

        await self._configure_connection(response=response)

        if file_response:
            Serializer.save_response(file_response, response)

        await asyncio.sleep(1)
        return response

    async def _receive_response(self, request: HttpRequest) -> HttpResponse:
        await self._send(request)
        status_code, headers, status_line = await self._receive_response_information()
        if request.method != 'HEAD':
            content = await self._receive_response_content(headers)
        else:
            content = b''
        return HttpResponse(status_code, status_line, headers, content)

    async def _send(self, request: HttpRequest):
        print(f'Sending request: {request.build_request()}')
        while True:
            try:
                self.writer.write(request.build_request())
                await self.writer.drain()
                break
            except (ConnectionError,
                    ConnectionResetError,
                    ConnectionAbortedError,
                    ConnectionRefusedError,
                    ):
                await self._connect(request.full_url)
        await asyncio.sleep(0.01)

    async def _receive_response_information(self) -> tuple[
        int, dict[str, str], str]:
        info = (await asyncio.wait_for(self.reader.readuntil(b'\r\n\r\n'),
                                       10)).decode()
        status_line = info.split('\r\n')[0]
        status_code = int(status_line.split()[1])
        headers = {line.split(':')[0]: ':'.join(line.split(':')[1:]).strip()
                   for line
                   in info.split('\r\n')[1:-2]}
        print(f'Receiving status code: {status_code}')
        print(f'Receiving headers: {headers}')
        await asyncio.sleep(0.01)
        return status_code, headers, status_line

    async def _receive_response_content(self,
                                        headers: dict[str, str]) -> bytes:
        if headers.get('Transfer-Encoding') == 'chunked':
            content = []
            while True:
                chunk_size = (
                    await self.reader.readuntil(b'\r\n')).decode().strip()
                chunk_size = int(chunk_size, base=16)
                chunk = await self.reader.readexactly(chunk_size)
                crlf = await self.reader.readuntil(b'\r\n')
                if self.verbose:
                    print(f'Receiving chunk sized {chunk_size}: {chunk}')
                if chunk_size == 0:
                    break
                content.append(chunk)
            content = b''.join(content)
            del headers['Transfer-Encoding']
            headers['Content-Length'] = str(len(content))
            if self.verbose:
                print(
                    f'Receiving content: \n{Serializer.try_decode_utf_8(content)}')
            await asyncio.sleep(0.01)
            return content
        if 'Content-Length' in headers:
            content_length = int(headers['Content-Length'])
            content = await self.reader.readexactly(content_length)
            if self.verbose:
                print(
                    f'Receiving content: \n{Serializer.try_decode_utf_8(content)}')
            await asyncio.sleep(0.01)
            return content
        raise UnknownContentError('Unknown response content')

    async def _configure_connection(self,
                                    request: HttpRequest = None,
                                    response: HttpResponse = None):
        if request is not None:
            host, port, _ = Serializer.extract_host_port_ssl(request.full_url)
            if not self.is_connected:
                await self._connect(request.full_url)
                return
            if self.is_connected and (host, port) != self.last_connection:
                await self.close()
                await self._connect(request.full_url)
                return
        if response is not None and response.headers.get(
                'Connection') == 'close':
            await self.close()
            return

    async def close(self):
        if self.is_connected:
            self.is_connected = False
            self.writer.close()
            await self.writer.wait_closed()

    def _add_cookies(self, request: HttpRequest):
        full_path = Serializer.get_full_path(request)
        if full_path in self.cookie_jar:
            cookies = []
            for name, value in self.cookie_jar[full_path].items():
                cookies.append(f'{name}={value}')
            request.add_header('Cookie', ', '.join(cookies))

    def _extract_cookies(self, request: HttpRequest, response: HttpResponse):
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
                      file_content: Optional[BinaryIO] = None,
                      timeout: Optional[int | float] = 5,
                      file_response: Optional[BinaryIO] = None,
                      verbose: Optional[int | bool] = 1,
                      ) -> HttpResponse:
        host = urlparse(url).hostname
        headers = headers if headers else {}
        content = file_content.read() if file_content else b''
        self.verbose = verbose

        headers |= {'Host': host,
                    'Connection': 'keep-alive',
                    'Content-Length': str(len(content)),
                    }

        if method.upper() not in METHODS:
            raise BadRequestError(f'Invalid method {method}')

        if file_content and method.upper() not in HAVING_BODY_METHODS:
            raise BadRequestError(
                f"Request with specified method ({method}) doesn't have body")

        request = HttpRequest(url,
                              method=method.upper(),
                              headers=headers,
                              data=content,
                              )

        return await self._get_response(request, timeout, file_response)
