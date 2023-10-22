class HttpResponse:
    def __init__(self, response: bytes):
        self.response = response
        self.status_code = self.extract_status_code()
        self.headers = self.extract_headers()
        self.content = self.extract_content()

    def extract_status_code(self) -> int:
        return int(self.response.splitlines()[0].split()[1])

    def extract_headers(self) -> dict:
        headers = {}
        raw_headers = self.response.split(b'\r\n\r\n')[0].splitlines()[1:]
        for raw_header in raw_headers:
            colon_index = raw_header.index(b':')
            headers[raw_header[:colon_index]] = raw_header[colon_index + 2:]
        return headers

    def extract_content(self) -> bytes:
        return b'\r\n\r\n'.join(self.response.split(b'\r\n\r\n')[1:])

    def save(self, filename):
        with open(filename, 'wb') as file:
            file.write(self.response)
