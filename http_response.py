class HttpResponse:
    def __init__(self,
                 status_code: int,
                 status_line: str,
                 headers: dict[str, str],
                 content: bytes,
                 ):
        self.status_code: int = status_code
        self.status_line: str = status_line
        self.headers: dict[str, str] = headers
        self.content: bytes = content

    def build_response(self):
        response = [self.status_line.encode()]
        for header, value in self.headers.items():
            response.append(f'{header}: {value}'.encode())
        response.append(b'')
        response.append(self.content)
        return b'\r\n'.join(response)
