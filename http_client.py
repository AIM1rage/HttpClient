import argparse
import ssl
import socket
import validators
from parser import *
from http_request import *
from http_response import *

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


class HttpConnection:
    def __init__(self, url, timeout=3):
        self.host, self.port = HttpConnection.extract_data_from_url(url)
        self.socket = socket.socket()
        if self.port == 443:
            self.socket = ssl.wrap_socket(self.socket)
        self.socket.settimeout(timeout)
        self.socket.connect((self.host, self.port))
        self.request = None
        self.reply = None

    def send_request(self, method, url, headers=None, content=b''):
        if headers is None:
            headers = {}

        headers.setdefault('Host', self.host)
        # headers.setdefault('Connection', 'close')
        # headers.setdefault('User-Agent', 'python')

        request = HttpRequest().add_method(
            method).add_url(
            url).add_headers(
            headers).add_content(
            content)

        self.socket.sendall(request.build_request())

        response = []
        while True:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                response.append(data)
            except socket.timeout:
                break

        response = b''.join(response)

        # self.socket.close()

        return HttpResponse(response)

    @staticmethod
    def extract_data_from_url(url):
        return urlparse(url).hostname, HttpConnection.get_port(url)

    @staticmethod
    def get_port(url):
        parsed_url = urlparse(url)
        if parsed_url.port:
            return parsed_url.port
        return 80 if parsed_url.scheme == 'http' else 443


if __name__ == '__main__':
    hogwarts_url = input()
    client = HttpConnection(hogwarts_url)

    response = client.send_request('POST', hogwarts_url, content=b'Hello, world!')

    response.save('response.txt')

    # parser = argparse.ArgumentParser()
    # parser.add_argument('method', type=str, choices=METHODS,
    #                     help='HTTP Request Method')
    # parser.add_argument('url', type=str,
    #                     help='URL address of the destination point')
