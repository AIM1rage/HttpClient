import os.path
import ssl
import socket
import validators
import json
from collections import namedtuple
from urllib.parse import urlparse

METHODS = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE',
           'CONNECT']
HEADERS = ['Accept', 'Accept-Charset', 'Accept-Encoding', 'Accept-Language',
           'Accept-Ranges', 'Age', 'Allow', 'Authorization', 'Cache-Control',
           'Connection', 'Content-Encoding', 'Content-Language',
           'Content-Length',
           'Content-Location', 'Content-MD5', 'Content-Range', 'Content-Type',
           'Date', 'ETag', 'Expect', 'Expires', 'From', 'Host', 'If-Match',
           'If-Modified-Since', 'If-None-Match', 'If-Range',
           'If-Unmodified-Since', 'Last-Modified', 'Location', 'Max-Forwards',
           'Pragma', 'Proxy-Authenticate', 'Proxy-Authorization', 'Range',
           'Referer', 'Retry-After', 'Server', 'TE', 'Trailer',
           'Transfer-Encoding', 'Upgrade', 'User-Agent', 'Vary', 'Via',
           'Warning', 'WWW-Authenticate']


class UrlError(Exception):
    ...


class HttpMethodError(Exception):
    ...


HttpResponse = namedtuple('HttpResponse',
                          ['status_code', 'headers', 'content'])


class HttpConnection:
    def __init__(self):
        self.socket = ssl.wrap_socket(socket.socket())
        self.host = None
        self.port = None
        self.path = None

        if os.path.isfile('cookies.json'):
            with open(r'cookies.json', 'r', encoding='utf-8') as file:
                self.cookies = json.load(file)
        else:
            self.cookies = {}

    def request(self, method, url, headers=None, content=None, timeout=1):
        if method not in METHODS:
            raise HttpMethodError(f'Nonexistent HTTP request method: {method}')
        if not validators.url(url):
            raise UrlError(f'Invalid URL: {url}')
        if headers is None:
            headers = {}
        self.extract_data_from_url(url)
        headers.setdefault('Host', self.host)
        if self.host in self.cookies:
            headers.setdefault('Cookie', self.cookies[self.host])
        # headers.setdefault('User-Agent', 'python')

        request = [f'{method} {self.path} HTTP/1.1\r\n']
        for name, value in headers.items():
            request.append(f'{name}: {value}\r\n')
        request.append('\r\n')

        self.socket.settimeout(timeout)
        self.socket.connect((self.host, self.port))
        self.socket.sendall(''.join(request).encode())

        response = []
        while True:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                response.append(data)
            except socket.timeout:
                break

        response = b''.join(response).decode('utf-8')

        self.socket.close()

        status_code = HttpConnection.extract_status_code(response)
        headers = HttpConnection.extract_headers(response)
        content = HttpConnection.extract_content(response)

        self.set_cookie(headers)

        return HttpResponse(status_code, headers, content)

    def extract_data_from_url(self, url):
        parsed_url = urlparse(url)
        self.host = parsed_url.hostname
        self.port = HttpConnection.get_port(url)
        self.path = parsed_url.path

    def set_cookie(self, headers):
        if 'Set-Cookie' in headers:
            self.cookies[self.host] = headers['Set-Cookie'].split('; ')[0]
        with open(r'cookies.json', 'w', encoding='utf-8') as file:
            json.dump(self.cookies, file)

    @staticmethod
    def get_port(url):
        parsed_url = urlparse(url)
        if parsed_url.port:
            return parsed_url.port
        return 80 if parsed_url.scheme == 'http' else 443

    @staticmethod
    def extract_status_code(response: str) -> int:
        return int(response.splitlines()[0].split()[1])

    @staticmethod
    def extract_headers(response: str) -> dict:
        headers = {}
        raw_headers = response.split('\r\n\r\n')[0].splitlines()[1:]
        for raw_header in raw_headers:
            colon_index = raw_header.index(':')
            headers[raw_header[:colon_index]] = raw_header[colon_index + 2:]
        return headers

    @staticmethod
    def extract_content(response: str) -> str:
        return response.split('\r\n\r\n')[1]


if __name__ == '__main__':
    hogwarts_url = 'https://anytask.org/'
    client = HttpConnection()

    response = client.request('GET', hogwarts_url)
    print(response.status_code)
    print(response.headers)
    print(response.content)
