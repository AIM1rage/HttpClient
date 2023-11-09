import asyncio
from asyncio import StreamReader, StreamWriter

from urllib.parse import urlparse

from typing import Optional, BinaryIO

from prompt_toolkit.shortcuts import ProgressBar
from prompt_toolkit.formatted_text import HTML

from src.domain.http_request import HttpRequest
from src.domain.http_response import HttpResponse
from src.domain.serializer import Serializer

HAVING_BODY_METHODS = ['PUT', 'POST', 'PATCH']
METHODS = ['TRACE', 'GET', 'POST', 'HEAD', 'CONNECT', 'DELETE', 'OPTIONS',
           'PATCH', 'PUT']


class UnknownContentError(Exception):
    ...


class BadRequestError(Exception):
    ...


class HttpClient:
    def __init__(self, progress_bar: Optional[ProgressBar] = None):
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

        response = await self._receive_response(request, timeout)
        self._extract_cookies(request, response)

        await self._configure_connection(response=response)

        if file_response:
            Serializer.save_response(file_response, response)

        await asyncio.sleep(1)
        return response

    async def _receive_response(self,
                                request: HttpRequest,
                                timeout: int | float) -> HttpResponse:
        await asyncio.wait_for(self._send(request), timeout)
        raw_response = []
        status_code, headers, status_line = await asyncio.wait_for(
            self._receive_response_information(raw_response), timeout)
        if request.method != 'HEAD':
            content = await self._receive_response_content(headers,
                                                           raw_response,
                                                           timeout,
                                                           )
        else:
            content = b''
        return HttpResponse(status_code, status_line, headers, content,
                            raw_response,
                            )

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

    async def _receive_response_information(self,
                                            raw_response: list[bytes],
                                            ) -> tuple[
        int, dict[str, str], str]:
        data = await self.reader.readuntil(b'\r\n\r\n')
        raw_response.append(data)
        info = data.decode().lower()
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
                                        headers: dict[str, str],
                                        raw_response: list[bytes],
                                        timeout: int | float,
                                        ) -> bytes:
        if headers.get('transfer-encoding') == 'chunked':
            content = []
            while True:
                chunk_size_data = await self.reader.readuntil(b'\r\n')
                chunk_size = int(chunk_size_data.decode().strip(), base=16)
                if chunk_size == 0:
                    chunk_with_crlf = await self.reader.readuntil(b'\r\n')
                    break
                chunk = await self._download_content(chunk_size, timeout)
                crlf = await self.reader.readuntil(b'\r\n')
                content.append(chunk)
            content = b''.join(content)
            del headers['transfer-encoding']
            headers['content-length'] = str(len(content))
            raw_response.append(content)
            await asyncio.sleep(0.01)
            return content
        if 'content-length' in headers:
            content_length = int(headers['content-length'])
            content = await self._download_content(content_length, timeout)
            raw_response.append(content)
            await asyncio.sleep(0.01)
            return content
        raise UnknownContentError('Unknown response content')

    async def _download_content(self,
                                content_length: int,
                                timeout: int | float,
                                ) -> bytes:
        content = []
        chunk_size = 2 ** 16
        chunks_count = content_length // chunk_size + (
            1 if
            content_length % chunk_size else
            0)
        label = HTML(
            ' <style bg="yellow" fg="black">Downloading content...</style>')
        if self.progress_bar:
            it = self.progress_bar(range(chunks_count),
                                   label=label,
                                   remove_when_done=True,
                                   )
        else:
            it = range(chunks_count)
        for i in it:
            size = (content_length % chunk_size if
                    i == chunks_count - 1 and
                    (content_length % chunk_size) else
                    chunk_size)
            data = await asyncio.wait_for(
                self.reader.readexactly(size), timeout)
            content.append(data)
        return b''.join(content)

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
                'connection') == 'close':
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
        if response.has_header('set-cookie'):
            cookie = response.headers['set-cookie'].split('; ')[0]
            name, value = cookie.split('=')[0], '='.join(cookie.split('=')[1:])
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
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
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
