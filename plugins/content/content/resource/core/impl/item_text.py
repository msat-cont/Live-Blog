'''
Created on Nov 13, 2013

@package: content
@copyright: 2013 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Mugur Rus

Implementation for text item handler.
'''

from content.base.core.spec import IItemHandler
from sql_alchemy.support.util_service import SessionSupport, insertModel,\
    updateModel
from ally.container.support import setup
from content.resource.api.item_text import ItemText, CLASS_TEXT
from content.base.api.item import Item
from content.resource.core.impl.item_resource import TYPE_RESOURCE
from content.resource.meta.item_text import ItemTextMapped

# --------------------------------------------------------------------

@setup(IItemHandler, name='itemTextHandler')
class ItemTextHandlerAlchemy(SessionSupport, IItemHandler):
    '''
    Handler for text item processing.
    '''

    def register(self, models):
        '''
        Implementation for @see IItemHandler.register
        '''
        assert isinstance(models, set), 'Invalid models set %s' % models
        models.add(ItemText)
    
    def insert(self, item, content=None):
        '''
        Implementation for @see IItemHandler.insert
        '''
        assert isinstance(item, Item), 'Invalid item %s' % item
        # TODO: set the content
        if item.Type == TYPE_RESOURCE and ItemText.Class in item and item.Class == CLASS_TEXT:
            return insertModel(ItemTextMapped, item).GUID

    def update(self, item, content=None):
        '''
        Implementation for @see IItemHandler.update
        '''
        assert isinstance(item, Item), 'Invalid item %s' % item
        # TODO: set the content
        if item.Type == TYPE_RESOURCE and ItemText.Class in item and item.Class == CLASS_TEXT:
            updateModel(ItemTextMapped, item)
            return True
        return False

    def delete(self, item):
        '''
        Implementation for @see IItemHandler.delete
        '''
        assert isinstance(item, Item), 'Invalid item %s' % item
        return True
