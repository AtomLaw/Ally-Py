'''
Created on Nov 7, 2012

@package: ally http
@copyright: 2011 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Special module that is used in deploying the application.
'''
 
from ..ally.deploy import openSetups
from .prepare import OptionsGateway
from __setup__.ally_plugin.deploy_plugin import openPlugins
from ally.container import ioc
from ally.container.support import entityFor
import application
import logging

# --------------------------------------------------------------------

log = logging.getLogger(__name__)

# --------------------------------------------------------------------

@ioc.start
def addFullAccessIPs():
    assert isinstance(application.options, OptionsGateway), 'Invalid application options %s' % application.options
    if not application.options.addIPs: return
    with openSetups('adding the full access IPs'):
        with openPlugins():
            from gateway.api.gateway import IGatewayService, Custom
            serviceGateway = entityFor(IGatewayService)
            assert isinstance(serviceGateway, IGatewayService)
            
            for ip in application.options.addIPs:
                gateway = Custom()
                gateway.Clients = ['\.'.join(mark.replace('*', '\d+') for mark in ip.split('.'))]
                try: serviceGateway.insert(gateway)
                except: log.info('IP \'%s\' already present', ip)
                else: log.info('IP \'%s\' added', ip)
    
