'''
Created on Nov 24, 2011

@package: Newscoop
@copyright: 2011 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the configurations for the processors used in handling the request.
'''

from . import server_pattern_rest
from ..ally_core.converter import contentNormalizer, converterPath
from ..ally_core.processor import handlersResources, methodInvoker, converter, \
    handlersExplainError, requestTypes, parameters, invokingHandler
from ..ally_core.resource_manager import resourcesManager
from ally.container import ioc
from ally.core.http.impl.processor.formatting import FormattingProviderHandler
from ally.core.http.impl.processor.header import HeaderStandardHandler
from ally.core.http.impl.processor.meta_filter import MetaFilterHandler
from ally.core.http.impl.processor.uri import URIHandler
from ally.core.spec.server import Processor, Processors
import re

# --------------------------------------------------------------------
# Creating the processors used in handling the request

@ioc.entity
def uri() -> Processor:
    b = URIHandler()
    b.resourcesManager = resourcesManager()
    b.converterPath = converterPath()
    return b

@ioc.config
def read_from_params():
    '''If true will also read header values that are provided as query parameters'''
    return True

@ioc.entity
def headerStandard() -> Processor:
    b = HeaderStandardHandler()
    b.readFromParams = read_from_params()
    return b

@ioc.entity
def handlersFetching():
    return [methodInvoker(), requestTypes(), parameters(), invokingHandler()]

@ioc.entity
def metaFilter() -> Processor:
    b = MetaFilterHandler()
    b.resourcesManager = resourcesManager()
    b.normalizer = contentNormalizer()
    b.fetching = Processors(*handlersFetching())
    b.readFromParams = read_from_params()
    return b

@ioc.entity
def formattingProvider() -> Processor:
    b = FormattingProviderHandler()
    b.readFromParams = read_from_params()
    return b

# ---------------------------------

@ioc.before(handlersExplainError)
def updateHandlersExplainError():
    handlersExplainError().insert(0, headerStandard())

# ---------------------------------

@ioc.before(handlersResources)
def updateHandlersResources():
    rscH = handlersResources()
    rscH.insert(rscH.index(methodInvoker()), headerStandard())
    rscH.insert(rscH.index(headerStandard()), uri())
    rscH.insert(rscH.index(methodInvoker()), formattingProvider())
    rscH.insert(rscH.index(converter()), metaFilter())

@ioc.entity
def pathProcessors():
    return [(re.compile(server_pattern_rest()), Processors(*handlersResources()))]