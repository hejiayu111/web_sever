import sys
import socket
import threading
import os
import time

from time import gmtime, strftime
from httpframer import HTTPFramer
from httprequest import HTTPRequest
from httpresponse import HTTPResponse


class MyServer:
    def __init__(self, port, doc_root):
        self.port = port
        self.doc_root = doc_root
        self.host = "localhost"

    """
    
    Add your server and handlers here. 
         
    """

    def parse(self, msg):
        request = HTTPRequest()
        # this array hold the three terms at the first line of the request
        fst_line_key = [''] * 3

        # this part makes sure no spaces occurs before GET and after the fist CRLF
        # if there is space, the function flag the format to be false

        # first line end
        fst_line_end = msg.find('\r\n')
        # retrieve first message
        fst_msg = msg[0:fst_line_end]
        # if there are spaces, format is wrong
        if fst_msg != fst_msg.strip():
            request.format = False
        if len(fst_msg.split(' ')) != 3:
            request.format = False

        # this part makes sure the spacing in the "GET /dir Version" format
        # this part checks if the there is extra space in between the three terms
        after_pos = 0
        for i in range(0, 2):
            space_pos = fst_msg.find(' ', after_pos)
            if fst_msg[space_pos + 1] == ' ':
                request.format = False
            # store the first two keys of the first line of the message
            fst_line_key[i] = fst_msg[after_pos:space_pos]
            after_pos = space_pos + 1

        # find out the third key of the first line of the message
        crlf_pos = msg.find('\r\n', after_pos)
        fst_line_key[2] = msg[after_pos:crlf_pos]
        request.function = fst_line_key[0]

        # start with the second line
        after_pos = crlf_pos + 2

        # handle malformed url
        if fst_line_key[1][0] != '/':
            request.format = False

        if fst_line_key[1] != '/' and fst_line_key[1][-1] == '/':
            request.format = False



        # store the information into Request class
        if fst_line_key[1] == '/':
            request.url = '/index.html'
        else:
            request.url = fst_line_key[1]

        request.version = fst_line_key[2]

        while crlf_pos != -1 and after_pos < len(msg):
            crlf_pos = msg.find('\r\n', after_pos)
            line = msg[after_pos:crlf_pos]
            colon = line.find(':')
            if colon == -1 or line[colon - 1] == ' ' or line[colon + 1] != ' ':
                request.format = False
            else:
                after_pos = crlf_pos + 2

        if msg.find('Host:') != -1:
            pos = msg.find('Host:')
            after_pos = msg.find('\r\n', pos)
            request.host = msg[pos + 6: after_pos]
        else:
            request.format = False

        if msg.find('Connection:') != -1:
            pos = msg.find('Connection:')
            after_pos = msg.find('\r\n', pos)
            request.connection = msg[pos + 12: after_pos]
        return request


    def buildResponse(self, request, realpath):
        fileExists = os.path.isfile(realpath)
        response = HTTPResponse()

        if request.connection == 'close':
            response.close = True
        # if request is malformed, code = 400
        if request.format is False:
            response.version = 'HTTP/1.1'
            response.code = 400
            response.code_msg = 'Client Error'
            return response

        # if file does not exist or root escape, code = 404
        elif fileExists is False or \
                (len(realpath) < len(self.doc_root) or realpath[:len(self.doc_root)] != self.doc_root) is True:
            response.version = 'HTTP/1.1'
            response.code = 404
            response.code_msg = 'NOT FOUND'
            return response

        # else, code = 200
        else:
            response.version = 'HTTP/1.1'
            response.code = 200
            response.code_msg = 'OK'
            stat = os.stat(realpath)
            response.lastModified = strftime('%a, %d %b %y %T %z', gmtime(stat.st_mtime))
            response.contentLen = stat.st_size
            lastDotPos = request.url.rfind('.')
            resourceType = request.url[lastDotPos+1:]
            if resourceType == 'jpg':
                response.contentType = 'image/jpeg'
            elif resourceType == 'png':
                response.contentType = 'image/png'
            else:
                response.contentType = 'text/html'

        return response

    def sendResponse(self, conn, response, realpath):
        message = ''
        message += (response.version + ' ')
        message += (str(response.code) + ' ')
        message += (response.code_msg + '\r\n')
        message += 'Server: MyServer 1.0\r\n'
        if response.code == 200:
            message += ('Last-Modified: ' + response.lastModified + '\r\n')
            message += ('Content-Type: ' + response.contentType + '\r\n')
            message += ('Content-Length: ' + str(response.contentLen) + '\r\n')
        if response.close is True:
            message += ('Connection: close\r\n')

        message += '\r\n'
        conn.sendall(message.encode())

        if response.code == 200:
            file = open(realpath, 'rb')
            sent_byte = 0
            length = os.stat(realpath).st_size

            while sent_byte < length:
                num_byte_sent = conn.sendfile(file)
                if num_byte_sent == 0:
                    file.close()
                    sys.exit('send failure')
                sent_byte += num_byte_sent
            file.close()

    def handleTCPClient(self, conn, doc_root):
        framer = HTTPFramer("")
        conn.settimeout(5)
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                framer.append(data.decode('UTF-8'))
            except socket.timeout:
                # handle timeout cases
                if len(framer.buffer) > 0:
                    response = HTTPResponse()
                    response.version = 'HTTP/1.1'
                    response.code = 400
                    response.code_msg = 'Client Error'
                    response.close = True
                    self.sendResponse(conn, response, '/')
                conn.close()
                return

            if framer.is_complete():
                msg = framer.fst_msg()
                framer.pop_msg()
                request = self.parse(msg)

                if doc_root[-1] == '/':
                    doc_root = doc_root[:-1]

                realpath = '/'
                if request.format is True:
                    realpath = os.path.realpath(doc_root + request.url)

                response = self.buildResponse(request, realpath)
                self.sendResponse(conn, response, realpath)
                conn.close()
                return

        conn.close()

    def startServer(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            threads = []
            while True:
                conn, addr = s.accept()
                t = threading.Thread(target=self.handleTCPClient, args=(conn, self.doc_root))
                t.start()
                threads.append(t)


if __name__ == '__main__':
    input_port = int(sys.argv[1])
    input_doc_root = sys.argv[2]
    server = MyServer(input_port, input_doc_root)
    # Add code to start your server here
    server.startServer()



