'''
Created on May 18, 2013

@package: superdesk desk
@copyright: 2013 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Ioan v. Pocol

Contains the SQL alchemy implementation for card API.
'''

from ..api.card import ICardService
from ..meta.card import CardMapped
from ally.container.ioc import injected
from ally.container.support import setup
from ally.support.sqlalchemy.util_service import buildLimits, buildQuery
from ally.api.extension import IterPart
from sql_alchemy.impl.entity import EntityServiceAlchemy
from sqlalchemy.sql.expression import not_, func
from superdesk.desk.meta.card import CardTaskStatusMapped
from superdesk.desk.meta.task_status import TaskStatusMapped
from superdesk.desk.meta.task_type import TaskTypeTaskStatusMapped
from superdesk.desk.meta.desk import DeskTaskTypeMapped
from superdesk.desk.api.card import QCard
from sqlalchemy.orm.exc import NoResultFound
from ally.exception import InputError

# --------------------------------------------------------------------

@injected
@setup(ICardService, name='cardService')
class CardServiceAlchemy(EntityServiceAlchemy, ICardService):
    '''
    Implementation for @see: ICardService
    '''

    def __init__(self):
        '''
        Construct the  service.
        '''
        EntityServiceAlchemy.__init__(self, CardMapped, QCard)
        
    def insert(self, card): 
        if not card.OrderIndex:
            card.OrderIndex = self.session().query(func.max(CardMapped.OrderIndex)).one()[0]
        
        if not card.OrderIndex:
            card.OrderIndex = 0
            
        card.OrderIndex =  card.OrderIndex + 1   
            
        return EntityServiceAlchemy.insert(self, card)        
     
    def getByDesk(self, deskId, offset=None, limit=None, detailed=False, q=None):
        '''
        @see: ICardService.getAll
        '''   
        sql = self.session().query(CardMapped)
        sql = sql.filter(CardMapped.Desk == deskId)
        if q:     
            sql = buildQuery(sql, q, CardMapped)
        entities = buildLimits(sql, offset, limit).all()
        if detailed: return IterPart(entities, sql.count(), offset, limit)

        return entities    

    def getStatuses(self, cardId, offset=None, limit=None, detailed=False):
        '''
        @see: ICardService.getStatuses
        '''
        sql = self.session().query(TaskStatusMapped).join(CardTaskStatusMapped)
        sql = sql.filter(CardTaskStatusMapped.card == cardId)
        entities = buildLimits(sql, offset, limit).all()
        if detailed: return IterPart(entities, sql.count(), offset, limit)

        return entities

    def getUnassignedStatuses(self, cardId, offset=None, limit=None, detailed=False):
        '''
        @see: ICardService.getUnassignedStatuses
        '''
        
        deskId = self.session().query(CardMapped).filter(CardMapped.Id == cardId).one().Desk
        
        sqlDesk = self.session().query(TaskTypeTaskStatusMapped.taskStatus)
        sqlDesk = sqlDesk.join(DeskTaskTypeMapped, TaskTypeTaskStatusMapped.taskType == DeskTaskTypeMapped.taskType)
        sqlDesk = sqlDesk.filter(DeskTaskTypeMapped.desk == deskId)
        
        sqlCard = self.session().query(CardTaskStatusMapped.taskStatus)
        sqlCard = sqlCard.filter(CardTaskStatusMapped.card == cardId)
        
        sql = self.session().query(TaskStatusMapped)
        sql = sql.filter(TaskStatusMapped.id.in_(sqlDesk.subquery()))
        sql = sql.filter(not_(TaskStatusMapped.id.in_(sqlCard.subquery())))

        entities = buildLimits(sql, offset, limit).all()
        if detailed: return IterPart(entities, sql.count(), offset, limit)

        return entities

    def attachTaskStatus(self, cardId, taskStatusKey):
        '''
        @see ICardService.attachUser
        '''      
        taskStatusId = self._statusId(taskStatusKey)
          
        sql = self.session().query(CardTaskStatusMapped)
        sql = sql.filter(CardTaskStatusMapped.card == cardId)
        sql = sql.filter(CardTaskStatusMapped.taskStatus == taskStatusId)
        if sql.count() == 1: return

        cardTaskStatus = CardTaskStatusMapped()
        cardTaskStatus.card = cardId
        cardTaskStatus.taskStatus = taskStatusId

        self.session().add(cardTaskStatus)
        self.session().flush((cardTaskStatus,))

    def detachTaskStatus(self, cardId, taskStatusKey):
        '''
        @see ICardService.detachTaskStatus
        '''
        taskStatusId = self._statusId(taskStatusKey)
        
        sql = self.session().query(CardTaskStatusMapped)
        sql = sql.filter(CardTaskStatusMapped.card == cardId)
        sql = sql.filter(CardTaskStatusMapped.taskStatus == taskStatusId)
        count_del = sql.delete()

        return (0 < count_del)
    
    def moveUp(self, cardId):
        '''
        @see ICardService.moveUp
        '''
        pass
        
    def moveDown(self, cardId):
        '''
        @see ICardService.moveDown
        '''
        pass
    
    def _statusId(self, key):
        '''
        Provides the task status id that has the provided key.
        '''
        try:
            sql = self.session().query(TaskStatusMapped.id).filter(TaskStatusMapped.Key == key)
            return sql.one()[0]
        except NoResultFound:
            raise InputError('Invalid task status %(status)s') % dict(status=key)
        