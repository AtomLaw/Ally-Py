'''
Created on Aug 24, 2012

@package: ally core
@copyright: 2011 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the parsing chain processors.
'''

from ally.container.ioc import injected
from ally.core.impl.processor.base import ErrorResponse, addError
from ally.core.spec.codes import ENCODING_UNKNOWN
from ally.core.spec.resources import Converter
from ally.design.processor.assembly import Assembly
from ally.design.processor.attribute import requires, defines
from ally.design.processor.branch import Branch
from ally.design.processor.context import Context
from ally.design.processor.execution import Chain, Processing, CONSUMED
from ally.design.processor.handler import HandlerBranching
import codecs

# --------------------------------------------------------------------

class Invoker(Context):
    '''
    The invoker context.
    '''
    # ---------------------------------------------------------------- Required
    decodingContent = requires(Context)
    
class Request(Context):
    '''
    The request context.
    '''
    # ---------------------------------------------------------------- Required
    invoker = requires(Context)
    arguments = requires(dict)
    converterContent = requires(Converter)

class RequestContent(Context):
    '''
    The request content context.
    '''
    # ---------------------------------------------------------------- Required
    type = requires(str)
    charSet = requires(str)

class ResponseContent(Context):
    '''
    The response context.
    '''
    # ---------------------------------------------------------------- Required
    type = requires(str)

class TargetContent(Context):
    '''
    The target context.
    '''
    # ---------------------------------------------------------------- Defined
    arguments = defines(dict, doc='''
    @rtype: dictionary{string: object}
    The arguments do decode the content in.
    ''')
    converter = defines(Converter, doc='''
    @rtype: Converter
    The converter to be used for decoding content.
    ''')

# --------------------------------------------------------------------

@injected
class ParsingHandler(HandlerBranching):
    '''
    Implementation for a processor that provides the parsing based on contained parsers. If a parser
    processor is successful in the parsing process it has to stop the chain execution.
    '''

    charSetDefault = str
    # The default character set to be used if none provided for the content.
    parsingAssembly = Assembly
    # The parsers processors, if a processor is successful in the parsing process it has to stop the chain execution.

    def __init__(self, *branches):
        assert isinstance(self.parsingAssembly, Assembly), 'Invalid parsers assembly %s' % self.parsingAssembly
        assert isinstance(self.charSetDefault, str), 'Invalid default character set %s' % self.charSetDefault
        
        branches += (Branch(self.parsingAssembly).
                     included(('decoding', 'Decoding'), ('target', 'Target')).included(),)
        super().__init__(*branches, Invoker=Invoker, requestCnt=RequestContent)

    def process(self, chain, processing, request:Request, response:ErrorResponse, Target:TargetContent, **keyargs):
        '''
        @see: HandlerBranching.process
        
        Parse the request content.
        '''
        assert isinstance(chain, Chain), 'Invalid processors chain %s' % chain
        assert isinstance(processing, Processing), 'Invalid processing %s' % processing
        assert isinstance(request, Request), 'Invalid request %s' % request

        if response.isSuccess is False: return  # Skip in case the response is in error
        if not request.invoker: return
        assert isinstance(request.invoker, Invoker), 'Invalid invoker %s' % request.invoker
        if not request.invoker.decodingContent: return
        
        if request.arguments is None: request.arguments = {}
        target = Target()
        assert isinstance(target, TargetContent), 'Invalid target %s' % target
        target.arguments = request.arguments
        target.converter = request.converterContent
        
        keyargs.update(request=request, response=response, decoding=request.invoker.decodingContent, target=target)
        if self.processParsing(chain, processing, **keyargs):
            # We process the chain without the request content anymore
            chain.arg.requestCnt = None

    def processParsing(self, chain, processing, requestCnt, response, responseCnt, **keyargs):
        '''
        Process the parsing for the provided contexts.
        
        @return: boolean
            True if the parsing has been successfully done on the request content.
        '''
        assert isinstance(processing, Processing), 'Invalid processing %s' % processing
        assert isinstance(requestCnt, RequestContent), 'Invalid request content %s' % requestCnt
        assert isinstance(responseCnt, ResponseContent), 'Invalid response content %s' % responseCnt

        # Resolving the character set
        if requestCnt.charSet:
            try: codecs.lookup(requestCnt.charSet)
            except LookupError: requestCnt.charSet = self.charSetDefault
        else: requestCnt.charSet = self.charSetDefault
        if not requestCnt.type: requestCnt.type = responseCnt.type
        
        keyargs.update(requestCnt=requestCnt, response=response, responseCnt=responseCnt)
        if not Chain(processing, False, **keyargs).execute(CONSUMED): return True
        if response.isSuccess is not False:
            ENCODING_UNKNOWN.set(response)
            addError(response, 'Content type \'%(type)s\' not supported for parsing', type=requestCnt.type)
