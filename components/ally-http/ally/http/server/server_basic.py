'''
Created on Jul 8, 2011

@package: ally http
@copyright: 2012 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the basic web server based on the python build in http server (this type of server will only run on a single
thread serving requests one at a time).
'''

from ally.container.ioc import injected
from ally.design.processor import Processing, Assembly, ONLY_AVAILABLE, \
    CREATE_REPORT, Chain
from ally.http.spec.server import RequestHTTP, ResponseHTTP, RequestContentHTTP, \
    ResponseContentHTTP, HTTP_GET, HTTP_POST, HTTP_PUT, HTTP_DELETE, HTTP_OPTIONS, \
    HTTP
from ally.support.util_io import readGenerator, IInputStream
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qsl
import logging

# --------------------------------------------------------------------

log = logging.getLogger(__name__)

# --------------------------------------------------------------------

class RequestHandler(BaseHTTPRequestHandler):
    '''
    The server class that handles the HTTP requests.
    '''
    
    def __init__(self, request, client_address, server):
        '''
        Create the request.
        '''
        assert isinstance(server, BasicServer), 'Invalid server %s' % server
        self.server_version = server.serverVersion
        super().__init__(request, client_address, server)

    def do_GET(self):
        self._process(HTTP_GET)

    def do_POST(self):
        self._process(HTTP_POST)

    def do_PUT(self):
        self._process(HTTP_PUT)

    def do_DELETE(self):
        self._process(HTTP_DELETE)

    def do_OPTIONS(self):
        self._process(HTTP_OPTIONS)

    # ----------------------------------------------------------------

    def _process(self, method):
        proc = self.server.processing
        assert isinstance(proc, Processing), 'Invalid processing %s' % proc
        
        request, requestCnt = proc.ctx.request(), proc.ctx.requestCnt()
        assert isinstance(request, RequestHTTP), 'Invalid request %s' % request
        assert isinstance(requestCnt, RequestContentHTTP), 'Invalid request content %s' % requestCnt
        
        url = urlparse(self.path)
        request.scheme, request.uri = HTTP, url.path.lstrip('/')
        request.parameters = parse_qsl(url.query, True, False)

        request.method = method
        request.headers = dict(self.headers)
        requestCnt.source = self.rfile

        chain = Chain(proc)
        chain.process(request=request, requestCnt=requestCnt).doAll()

        response, responseCnt = chain.arg.response, chain.arg.responseCnt
        assert isinstance(response, ResponseHTTP), 'Invalid response %s' % response
        assert isinstance(responseCnt, ResponseContentHTTP), 'Invalid response content %s' % responseCnt

        assert isinstance(response.status, int), 'Invalid response status code %s' % response.status
        if ResponseHTTP.headers in response:
            for name, value in response.headers.items(): self.send_header(name, value)

        if ResponseHTTP.text in response: self.send_response(response.status, response.text or response.code)
        else: self.send_response(response.status)

        self.end_headers()

        if responseCnt.source is not None:
            if isinstance(responseCnt.source, IInputStream): source = readGenerator(responseCnt.source)
            else: source = responseCnt.source

            for bytes in source: self.wfile.write(bytes)

    # ----------------------------------------------------------------

    def log_message(self, format, *args):
        # TODO: see for a better solution for this, check for next python release
        # This is a fix: whenever a message is logged there is an attempt to find some sort of host name which
        # creates a big delay whenever the request is made from a non localhost client.
        assert log.debug(format, *args) or True

# --------------------------------------------------------------------

@injected
class BasicServer(HTTPServer):
    '''
    The basic server.
    '''
    
    serverVersion = str
    # The server version name
    serverHost = str
    # The server address host
    serverPort = int
    # The server port
    requestHandlerFactory = RequestHandler
    # The factory that provides request handlers, takes as arguments the server, request socket
    # and client address.
    assembly = Assembly
    # The assembly used for resolving the requests
    
    def __init__(self):
        '''
        Construct the server.
        '''
        assert isinstance(self.serverVersion, str), 'Invalid server version %s' % self.serverVersion
        assert isinstance(self.serverHost, str), 'Invalid server host %s' % self.serverHost
        assert isinstance(self.serverPort, int), 'Invalid server port %s' % self.serverPort
        assert callable(self.requestHandlerFactory), 'Invalid request handler factory %s' % self.requestHandlerFactory
        assert isinstance(self.assembly, Assembly), 'Invalid assembly %s' % self.assembly
        super().__init__((self.serverHost, self.serverPort), self.requestHandlerFactory)

        processing, report = self.assembly.create(ONLY_AVAILABLE, CREATE_REPORT,
                                                  request=RequestHTTP, requestCnt=RequestContentHTTP,
                                                  response=ResponseHTTP, responseCnt=ResponseContentHTTP)
        log.info('Assembly report for server:\n%s', report)
        self.processing = processing

# --------------------------------------------------------------------

def run(server):
    '''
    Run the basic server.
    
    @param server: BasicServer
        The server to run.
    '''
    assert isinstance(server, BasicServer), 'Invalid server %s' % server
    
    try:
        print('=' * 50, 'Started HTTP server...')
        server.serve_forever()
    except KeyboardInterrupt:
        print('=' * 50, '^C received, shutting down server')
        server.server_close()
    except:
        log.exception('=' * 50 + ' The server has stooped')
        try: server.server_close()
        except: pass
