import json
import os
from http_response import HttpResponse
from http_request import HttpRequest
from urllib.parse import urlparse


class Serializer:
    @staticmethod
    def save_response(path: str, response: HttpResponse):
        with open(path, 'wb') as file:
            file.write(response.build_response())

    @staticmethod
    def get_full_path(request: HttpRequest):
        parsed_url = urlparse(request.full_url)
        host = parsed_url.hostname
        path = parsed_url.path if parsed_url.path else '/'
        full_path = host + path
        return full_path

    @staticmethod
    def load_cookies():
        if not os.path.exists('../cookies.json'):
            return {}
        with open('../cookies.json', 'r', encoding='utf-8') as file:
            return json.load(file)

    @staticmethod
    def dump_cookies(cookie_jar: dict[str, dict[str, str]]):
        with open('../cookies.json', 'w', encoding='utf-8') as file:
            json.dump(cookie_jar, file)
