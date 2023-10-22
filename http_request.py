from urllib.parse import urlparse

METHODS = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE',
           'CONNECT']


class HttpMethodError(Exception):
    ...


class HttpRequest:
    def __init__(self):
        self.method = 'GET'
        self.path = '/'
        self.version = 'HTTP/1.1'
        self.headers = {}
        self.content = b''

    def add_method(self, method: str):
        if method.strip().upper() not in METHODS:
            raise HttpMethodError(f'Wrong HTTP request method: {method}')
        self.method = method
        return self

    def add_url(self, url: str):
        parsed_url = urlparse(url)
        self.path = parsed_url.path if parsed_url.path else '/'
        return self

    def add_version(self, version: str):
        self.version = version
        return self

    def add_headers(self, headers: dict):
        self.headers |= headers
        return self

    def add_content(self, content: bytes):
        self.content = content
        return self

    def build_request(self) -> bytes:
        request = [f'{self.method} {self.path} {self.version}\r\n'.encode()]
        if len(self.content):
            self.headers['Content-Length'] = len(self.content)
        for header, value in self.headers.items():
            request.append(f'{header}: {value}\r\n'.encode())
        request.append('\r\n'.encode())
        request.append(self.content)
        return b''.join(request)
