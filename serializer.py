from http_response import HttpResponse


class Serializer:
    @staticmethod
    def save_response(path: str, response: HttpResponse):
        with open(path, 'wb') as file:
            file.write(response.build_response())
