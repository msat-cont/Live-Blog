'''
Created on July 10, 2012

@package: ally authentication
@copyright: 2012 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Mugur Rus

Provides authentication register function.
'''

# --------------------------------------------------------------------

from ally.container import ioc, support
from ally.core.authentication.api.authentication import IAuthenticate
from __plugin__.ally_authentication_http.authentication import registerAuthentication

# --------------------------------------------------------------------

@ioc.start
def register():
    registerAuthentication(support.entityFor(IAuthenticate))
