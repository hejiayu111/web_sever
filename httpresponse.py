class HTTPResponse:
    def __init__(self):
        self.version = None
        self.code = None
        self.code_msg = None
        self.server = 'MyServer v1.0'
        self.lastModified = None
        self.contentType = None
        self.contentLen = None
        self.close = False
