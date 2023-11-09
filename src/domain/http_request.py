from urllib.request import Request
from urllib.parse import urlparse


class HttpRequest(Request):
    def build_request(self) -> bytes:
        path = urlparse(self.full_url).path
        path = path if path else '/'
        request = [f'{self.method} {path} HTTP/1.1'.encode()]
        for header, value in self.headers.items():
            request.append(f'{header}: {value}'.encode())
        request.append(b'')
        request.append(self.data)
        return b'\r\n'.join(request)

    def __str__(self):
        return f'{self.method} {self.full_url}'
