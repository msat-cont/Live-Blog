'''
Created on Mar 13, 2012

@package: internationalization
@copyright: 2012 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Mugur Rus

Implementation for the PO file management.
'''

from babel.messages.catalog import Catalog
from internationalization.api.message import IMessageService
from ally.container import wire
from ally.container.ioc import injected
from internationalization.core.spec import IPOFileManager
from genericpath import isdir, isfile
import os
from internationalization.api.source import ISourceService, QSource
from introspection.api.component import Component
from introspection.api.plugin import Plugin
from ally.api.type import Iter
from internationalization.api.message import Message
from babel.messages.pofile import read_po, write_po
from os.path import join
from time import localtime, strptime
from io import StringIO

# --------------------------------------------------------------------

@injected
class POFileManagerDB(IPOFileManager):
    '''
    Implementation for @see: IPOFileManager
    '''

    messageService = IMessageService; wire.entity('messageService')

    sourceService = ISourceService; wire.entity('sourceService')

    locale_dir_path = str; wire.config('locale_dir_path', doc=
                                       'The locale repository path')

    def __init__(self):
        assert isinstance(self.messageService, IMessageService), 'Invalid message service %s' % self.messageService
        assert isinstance(self.sourceService, ISourceService), 'Invalid source file service %s' % self.sourceService
        assert isinstance(self.locale_dir_path, str), 'Invalid locale directory %s' % self.locale_dir_path
        if not isdir(self.locale_dir_path) or not os.access(self.locale_dir_path, os.W_OK):
            raise Exception('Unable to access the repository directory %s' % self.locale_dir_path)

    def poFileTimestamp(self, locale, component, plugin):
        '''
        @see: IPOFileManager.poFileTimestamp
        '''
        path = self._poFilePath(locale, component, plugin)
        if not isfile(path):
            return None
        fileMTime = localtime(os.stat(path).st_mtime)
        lastMsgTimestamp = strptime(self._messagesLastModified(component, plugin))
        if fileMTime >= lastMsgTimestamp:
            return fileMTime
        else:
            return lastMsgTimestamp

    def getGlobalPOFile(self, locale):
        '''
        @see: IPOFileManager.getGlobalPOFile
        '''
        keys = self.messageService.getMessages()
        return self._buildPOFile(locale, keys)

    def getComponentPOFile(self, component, locale):
        '''
        @see: IPOFileManager.getComponentPOFile
        '''
        keys = self.messageService.getComponentMessages(component)
        exceptionsCatalog = self._readPOFile(self._poFilePath(locale, component), locale)
        return self._buildPOFile(locale, keys, exceptionsCatalog)

    def getPluginPOFile(self, plugin, locale):
        '''
        @see: IPOFileManager.getPluginPOFile
        '''
        keys = self.messageService.getPluginMessages(plugin)
        exceptionsCatalog = self._readPOFile(self._poFilePath(locale, plugin=plugin), locale)
        return self._buildPOFile(locale, keys, exceptionsCatalog)

    def updateGlobalPOFile(self, poFile, locale):
        '''
        @see: IPOFileManager.updateGlobalPOFile
        '''
        keys = self.messageService.getMessages()
        templateCatalog = self._buildCatalog(keys, locale)
        self._updatePOFile(self._poFilePath(locale), poFile, templateCatalog, locale)

    def updateComponentPOFile(self, poFile, component, locale):
        '''
        @see: IPOFileManager.updateComponentPOFile
        '''
        exceptionsCatalog = self._readPOFile(self._poFilePath(locale, component), locale)

        keys = self.messageService.getComponentMessages(component)
        templateCatalog = self._buildCatalog(keys, locale)
        for msg in exceptionsCatalog:
            templateCatalog.delete(msg.id, msg.context)

        self._updatePOFile(self._poFilePath(locale), poFile, templateCatalog, locale)
        self._updatePOFile(self._poFilePath(locale, component), poFile, exceptionsCatalog, locale)

    def updatePluginPOFile(self, poFile, plugin, locale):
        '''
        @see: IPOFileManager.updatePluginPOFile
        '''
        exceptionsCatalog = self._readPOFile(self._poFilePath(locale, plugin=plugin), locale)

        keys = self.messageService.getPluginMessages(plugin)
        templateCatalog = self._buildCatalog(keys, locale)
        for msg in exceptionsCatalog:
            templateCatalog.delete(msg.id, msg.context)

        self._updatePOFile(self._poFilePath(locale), poFile, templateCatalog, locale)
        self._updatePOFile(self._poFilePath(locale, plugin=plugin), poFile, exceptionsCatalog, locale)

    def _updatePOFile(self, path:str, newPOFile, templateCatalog:Catalog, locale:str):
        '''
        Update a PO file from the given file like object.

        @param path: str
            The path of the PO file to be updated
        @param newPOFile: file like object
            The PO file containing the updates
        @param templateCatalog: Catalog
            Catalog containing allowed keys. Keys not existent in this catalog
            will be discarded from the PO file.
        '''
        catalog = self._readPOFile(path, locale)
        newCatalog = read_po(newPOFile, locale)
        for msg in newCatalog:
            if msg not in templateCatalog:
                newCatalog.delete(msg.id, msg.context)
        catalog.update(newCatalog)
        with open(path) as globalPo:
            write_po(globalPo, catalog)

    def _buildPOFile(self, locale:str=None, keys:Iter(Message)=Iter(Message),
                     exceptionsCat:Catalog=Catalog()):
        '''
        Builds a PO file from the given file (as file object) to read from, for the
        given locale, using the given template (keys) and exceptions catalog.
        Messages not in the keys list will be discarded while messages from the
        exceptions catalog will overwrite the messages with the same keys that
        existed in the given PO file.
        
        @param locale: str
            The locale code
        @param keys: Iter(Message)
            The keys used to filter the messages. Only keys from this list will
            be kept in the catalog.
        @param exceptionsCat: Catalog
            Messages that override the generic translations.
        @return: file like object
            File like object that contains the PO file content
        '''
        globalCatalog = self._readPOFile(self._poFilePath(locale), locale)
        for msg in exceptionsCat:
            globalCatalog.add(msg.id, msg.string, msg.locations, msg.flags, msg.auto_comments,
                              msg.user_comments, msg.previous_id, msg.lineno, msg.context)
        templateCatalog = self._buildCatalog(keys, locale)
        globalCatalog.update(templateCatalog)
        fileObj = StringIO()
        write_po(fileObj)
        return fileObj

    def _readPOFile(self, path:str, locale:str=None) -> Catalog:
        '''
        Read the file pointed to by the given path into a catalog.

        @param path: str
        @param locale: str
            The locale code
        '''
        if not isfile(path):
            return Catalog()
        with path as fObj:
            return read_po(fObj, locale)

    def _poFileName(self, locale:str=None, component:Component.Id=None, plugin:Plugin.Id=None):
        '''
        Returns the name of the PO file corresponding to the given locale and/or
        component / plugin. If no component of plugin was specified it returns the
        name of the global PO file.
        
        @param locale: str
            The locale code
        @param component: Component.Id
        @param plugin: Plugin.Id
        '''
        fileLocale = '_' + locale if locale else ''
        if component:
            return 'component_' + component + fileLocale + '.po'
        elif plugin:
            return 'plugins' + plugin + fileLocale + '.po'
        else:
            return 'global' + fileLocale + '.po'

    def _poFilePath(self, locale:str=None, component:Component.Id=None, plugin:Plugin.Id=None):
        '''
        Returns the path to the internal PO file corresponding to the given locale and / or
        component / plugin. If no component of plugin was specified it returns the
        name of the global PO file.
        
        @param locale: str
            The locale code
        @param component: Component.Id
        @param plugin: Plugin.Id
        '''
        return join(self.locale_dir_path, self._poFileName(locale, component, plugin))

    def _messagesLastModified(self, component:Component.Id=None, plugin:Plugin.Id=None):
        '''
        Returns the timestamp of the last modified message from the messages table.

        @param component: Component.Id
            Filters by component
        @param plugin: Plugin.Id
            Filters by plugin
        @return: timestamp
        '''
        q = QSource()
        q.lastModified.orderDesc()
        if component:
            q.component = component
        elif plugin:
            q.plugin = plugin
        sources = self.sourceService.getAll(0, 1, q)
        if sources:
            return sources[0].LastModified
        return None

    def _buildCatalog(self, messages, locale:str=None) -> Catalog:
        '''
        Builds a catalog from the given messages list.
        
        @param messages: list of Message entities
        @param locale: str
            The locale code
        @return: Catalog
        '''
        assert isinstance(messages, Iter(Message)) or isinstance(messages, tuple), \
                'Invalid messages list %s' % messages
        catalog = Catalog(locale)
        if isinstance(messages, Iter(Message)):
            messages = (messages,)
        for grp in messages:
            for msg in grp:
                assert isinstance(msg, Message), 'Invalid message %s in list' % msg
                msgId = msg.Singular if not msg.Plural else (msg.Singular,) + msg.Plural
                catalog.add(id=msgId, locations=((msg.Source.Path, msg.LineNumber),), flags=(),
                            auto_comments=(msg.Comments), user_comments=(), context=msg.Context)
        return catalog
