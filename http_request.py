import validators.url
from urllib.parse import urlparse

METHODS = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE',
           'CONNECT']

GENERAL_HEADERS = ['Cache-Control', 'Connection', 'Date', 'Pragma', 'Trailer',
                   'Transfer-Encoding', 'Upgrade', 'Via', 'Warning']


class MethodError(Exception):
    ...


class UrlError(Exception):
    ...


class HttpRequest:
    def __init__(self):
        self.method: str = 'GET'
        self.abs_path: str = '/'
        self.http_version: str = 'HTTP/1.1'
        self.headers: dict = {}
        self.body: bytes = b''

    def add_method(self, method: str):
        if method.strip().upper() not in METHODS:
            raise MethodError(f'Invalid HTTP request method: {method}')
        self.method = method

    def add_url(self, url: str):
        if not validators.url(url):
            raise UrlError(f'Invalid URL: {url}')
        parsed_url = urlparse(url)
        self.abs_path = parsed_url.path if parsed_url.path else '/'

    def add_headers(self, headers: dict):
        self.headers = headers

    def add_content(self, body: bytes):
        self.body = body

    def build_request(self) -> bytes:
        request = [
            f'{self.method} {self.abs_path} {self.http_version}\r\n'.encode()]
        if len(self.body):
            self.headers['Content-Length'] = len(self.body)
        for header, value in self.headers.items():
            request.append(f'{header}: {value}\r\n'.encode())
        request.append('\r\n'.encode())
        request.append(self.body)
        return b''.join(request)
