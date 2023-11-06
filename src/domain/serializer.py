import json
import os
from typing import BinaryIO
from src.domain.http_response import HttpResponse
from src.domain.http_request import HttpRequest
from urllib.parse import urlparse


class Serializer:
    @staticmethod
    def try_decode_utf_8(content: bytes) -> str | bytes:
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            return content

    @staticmethod
    def extract_host_port_ssl(url: str) -> tuple[str, int, bool]:
        url = urlparse(url)
        if url.scheme == 'http':
            return url.hostname, 80, False
        else:
            return url.hostname, 443, True

    @staticmethod
    def save_response(file_response: BinaryIO, response: HttpResponse):
        file_response.write(response.build_response())

    @staticmethod
    def get_full_path(request: HttpRequest):
        parsed_url = urlparse(request.full_url)
        host = parsed_url.hostname
        path = parsed_url.path if parsed_url.path else '/'
        full_path = host + path
        return full_path

    @staticmethod
    def load_cookies():
        if not os.path.exists('data/cookies.json'):
            return {}
        with open('data/cookies.json', 'r', encoding='utf-8') as file:
            return json.load(file)

    @staticmethod
    def dump_cookies(cookie_jar: dict[str, dict[str, str]]):
        with open('data/cookies.json', 'w', encoding='utf-8') as file:
            json.dump(cookie_jar, file)
