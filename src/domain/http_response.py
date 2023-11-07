class HttpResponse:
    def __init__(self,
                 status_code: int,
                 status_line: str,
                 headers: dict[str, str],
                 content: bytes,
                 raw_response: list[bytes],
                 ):
        self.status_code: int = status_code
        self.status_line: str = status_line
        self.headers: dict[str, str] = headers
        self.content: bytes = content
        self.raw_response: list[bytes] = raw_response

    def has_header(self, header):
        return header in self.headers

    def build_response(self):
        return b''.join(self.raw_response)
