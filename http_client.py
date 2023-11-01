import argparse
import ssl
import socket
import validators
# from parser import *
from http_request import *
from http_response import *

METHODS = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE',
           'CONNECT']


class HttpClient:
    def __init__(self, url):
        self.host, self.port = HttpClient.extract_data_from_url(url)
        self.socket = socket.socket()
        if self.port == 443:
            self.socket = ssl.wrap_socket(self.socket)
        self.socket.connect((self.host, self.port))
        self.request = None
        self.reply = None

    def connect(self):
        ...

    @staticmethod
    def get_host(url: str):
        parsed_url = urlparse(url)
        if not validators.hostname(parsed_url.hostname):
            raise UrlError(f'Invalid hostname: {parsed_url.hostname}')
        return parsed_url.hostname

    @staticmethod
    def get_port(url: str):
        parsed_url = urlparse(url)
        if parsed_url.port:
            return parsed_url.port
        if parsed_url.scheme == 'https':
            return 443
        if parsed_url.scheme == 'http':
            return 80
        raise UrlError(f'Unsupported protocol: {parsed_url.scheme}')


if __name__ == '__main__':
    hogwarts_url = input()
    client = HttpClient(hogwarts_url)

    response = client.send_request('GET', hogwarts_url)

    response.save('response.txt')

    # parser = argparse.ArgumentParser()
    # parser.add_argument('method', type=str, choices=METHODS,
    #                     help='HTTP Request Method')
    # parser.add_argument('url', type=str,
    #                     help='URL address of the destination point')
