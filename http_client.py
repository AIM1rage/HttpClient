import sys
import ssl
import socket
import validators
import pickle
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


class HttpResponse:
    def __init__(self, status_code, headers, content, text):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.text = text

    def save(self, filename):
        with open(filename, 'wb') as file:
            file.write(self.text)


class HttpConnection:
    def __init__(self):
        self.socket = ssl.wrap_socket(socket.socket())
        self.host = None
        self.port = None
        self.path = None
        self.text = None

        try:
            with open(r'cookies.pickle', 'rb') as file:
                self.cookies = pickle.load(file)
        except Exception:
            self.cookies = {}

    def request(self, method, url, headers=None, content='', timeout=1):
        if method not in METHODS:
            raise HttpMethodError(f'Nonexistent HTTP request method: {method}')
        if not validators.url(url):
            raise UrlError(f'Invalid URL: {url}')
        if headers is None:
            headers = {}
        self.extract_data_from_url(url)
        headers.setdefault('Host', self.host)
        headers.setdefault('Connection', 'close')
        # headers.setdefault('User-Agent', 'python')

        if self.host in self.cookies:
            headers.setdefault('Cookie', '; '.join(self.cookies[self.host]))

        request = [f'{method} {self.path} HTTP/1.1\r\n']
        for name, value in headers.items():
            request.append(f'{name}: {value}\r\n')
        request.append('\r\n')
        request.append(content)

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

        self.text = b''.join(response)

        self.socket.close()

        status_code = HttpConnection.extract_status_code(self.text)
        headers = HttpConnection.extract_headers(self.text)
        content = HttpConnection.extract_content(self.text)

        self.set_cookie(headers)

        return HttpResponse(status_code, headers, content, self.text)

    def extract_data_from_url(self, url):
        parsed_url = urlparse(url)
        self.host = parsed_url.hostname
        self.port = HttpConnection.get_port(url)
        self.path = parsed_url.path

    def set_cookie(self, headers):
        if 'Set-Cookie' in headers:
            self.cookies.setdefault(
                self.host, set()).add(headers['Set-Cookie'].split('; ')[0])
        with open(r'cookies.pickle', 'wb') as file:
            pickle.dump(self.cookies, file)

    @staticmethod
    def get_port(url):
        parsed_url = urlparse(url)
        if parsed_url.port:
            return parsed_url.port
        return 80 if parsed_url.scheme == 'http' else 443

    @staticmethod
    def extract_status_code(response: bytes) -> int:
        return int(response.splitlines()[0].split()[1])

    @staticmethod
    def extract_headers(response: bytes) -> dict:
        headers = {}
        raw_headers = response.split(b'\r\n\r\n')[0].decode(
            'utf-8').splitlines()[1:]
        for raw_header in raw_headers:
            colon_index = raw_header.index(':')
            headers[raw_header[:colon_index]] = raw_header[colon_index + 2:]
        return headers

    @staticmethod
    def extract_content(response: bytes) -> str:
        return b'\r\n\r\n'.join(response.split(b'\r\n\r\n')[1:]).decode('utf-8')


def ask_yes_no(question):
    while True:
        answer = input(f'{question} [y/n]')
        if answer not in ('y', 'n'):
            print('Invalid answer')
            print(f'Given {answer}')
            continue
        return answer == 'y'


if __name__ == '__main__':
    # hogwarts_url = 'https://urgu.org/150'
    # client = HttpConnection()
    #
    # response = client.request('GET', hogwarts_url, content='key=value')
    # print(response.status_code)
    # print(response.headers)
    # print(response.content)
    #
    # response.save('response.txt')

    while True:
        while True:
            method = input('Enter METHOD: ')
            if method not in METHODS:
                print(f'Incorrect METHOD: {method}')
            else:
                break

        while True:
            url = input('Enter full URL: ')
            if not validators.url(url):
                print(f'Incorrect URL: {url}')
            else:
                break

        headers_count = int(input('Enter headers\' COUNT: '))
        if headers_count:
            print('Enter your headers in format SOME_HEADER: SOME_VALUE')
        headers = {}
        for _ in range(headers_count):
            header, value = input().split()
            headers[header] = value

        to_have_content = ask_yes_no('Do you need BODY?')
        content = ''
        if to_have_content:
            content = input()

        client = HttpConnection()
        response = client.request(method, url, headers, content)
        print(response.status_code)
        print(response.headers)
        print(response.content)
        print(f'Your cookies: {client.cookies}')

        to_save_response = ask_yes_no('Do you want to SAVE response?')
        if to_save_response:
            filename = input('Enter your FILENAME/FILEPATH: ')
            response.save(filename)

        to_continue = ask_yes_no('Continue?')
        if not to_continue:
            break
