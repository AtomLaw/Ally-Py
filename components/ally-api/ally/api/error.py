'''
Created on Aug 2, 2013

@package: ally api
@copyright: 2012 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the exceptions that are used in communicating issues in the API.
'''

from ..internationalization import _
from .type import typeFor, Type
from ally.api.operator.type import TypeModel, TypeProperty
from itertools import chain

# --------------------------------------------------------------------

class InputError(Exception):
    '''
    Exception to be raised when the input is invalid.
    '''

    def __init__(self, msg, *items, **data):
        '''
        Initializes the exception based on the items(s).
        
        ex:
            raise InputError('No idea what is wrong %(reason)s', Entity.Id, reason='blame Gabriel')
            # The message is not associated with any type.
            
            raise InputError('Something wrong with the id', Entity.Id) # The message is associated with the entity id.
            
            raise InputError('Something wrong with the id', Entity.Id, 'And with the name', 'Is To long', Entity.Name)
            # The first message is associated with the entity id, and the following two with the entity name.
        
        @param msg: string
            The mandatory message to be associated with the error, optionally with place holders which have the value provided
            in the data
        @param items: arguments[string|Type reference]
            Other item(s) that compose this input error, they can be messages optionally with place holders which have the value 
            provided in the data or type references linking all the previous messages with a type.
        '''
        assert isinstance(msg, str), 'Invalid message %s' % msg
        
        self.data = data
        self.messageByType = {}
        msgs = [msg]
        for item in items:
            if isinstance(item, str): msgs.append(item)
            else:
                typ = typeFor(item)
                assert isinstance(typ, Type), 'Invalid type %s' % typ
                assert msgs, 'Please provide messages for type %s' % typ
                self.messageByType[typ] = msgs
                msgs = []
        self.messages = msgs
        
        super().__init__()
        
    def __str__(self):
        '''
        @see: Exception.__str__
        '''
        message = []
        message.extend(msg % self.data for msg in self.messages)
        for typ, msgs in self.messageByType.items():
            message.append(str(typ))
            message.extend('\t%s' % (msg % self.data) for msg in msgs)
        return '\n'.join(message)
        
# --------------------------------------------------------------------

class IdError(InputError):
    '''
    Exception to be raised when a model id is invalid.
    '''
    
    def __init__(self, *items, **data):
        '''
        Initializes the invalid id exception based on the items(s).
        @see: InputError.__init__
        '''
        if items:
            for k, item in enumerate(items):
                if not isinstance(item, str):
                    typ = typeFor(item)
                    if isinstance(typ, TypeModel):
                        assert isinstance(typ, TypeModel)
                        assert isinstance(typ.propertyId, TypeProperty), \
                        'Invalid property id % for model %s' % (typ.propertyId, typ)
                        items = chain(items[:k], (typ.propertyId,), items[k + 1:])
                    break
        super().__init__(_('Unknown identifier'), *items, **data)
