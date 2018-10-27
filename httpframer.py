class HTTPFramer:

    def __init__(self, buffer):
        self.buffer = buffer

    def append(self, string):
        self.buffer += string
        return

    # this function checks if the byte contain one complete message
    def is_complete(self):
        return self.buffer.find('\r\n\r\n') != -1

    # this function find out the fist complete message if there is one
    def fst_msg(self):
        end = self.buffer.find('\r\n\r\n')
        return self.buffer[0:end+2]

    # this function remove the first complete message from the byte stream
    def pop_msg(self):
        end_of_fst = self.buffer.find('\r\n\r\n')
        self.buffer = self.buffer[end_of_fst + 4::]
        return
