'''
Created on Jun 18, 2011

@package: ally core
@copyright: 2012 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Module containing specifications for the resources tree.
'''

from ally.api.type import Type, Input
import abc
import re

# --------------------------------------------------------------------

class Path:
    '''
    Provides the path container.
    The path is basically a immutable collection of matches. 
    '''

    def __init__(self, resourcesLocator, matches, node=None):
        '''
        Initializes the path.

        @param resourcesLocator: IResourcesLocator
            The resource locator that generated the path.
        @param matches: list[Match]
            The list of matches that represent the path.
        @param node: Node
            The node represented by the path, if None it means that the path is incomplete.
        '''
        assert isinstance(resourcesLocator, IResourcesLocator), 'Invalid resources locator %s' % resourcesLocator
        assert isinstance(matches, list), 'Invalid matches list %s' % matches
        assert node is None or isinstance(node, Node), 'Invalid node % can be None' % node
        if __debug__:
            for match in matches: assert isinstance(match, Match), 'Invalid match %s' % match
        self.resourcesLocator = resourcesLocator
        self.matches = matches
        self.node = node

    def findGetModel(self, typeModel):
        '''
        @see: IResourcesLocator.findGetModel
        
        Finds the path for the first Node that provides a get resource for the type model. The search is made based
        on this path. First this path Node and is children's are searched for the get method if not found it will
        go to the Nodes parent and make the search there, so forth and so on.
        
        @param typeModel: TypeModel
            The type model to search the get for.
        @return: PathExtended|None
            The extended path pointing to the desired get method, attention some updates might be necessary on 
            the path to be available. None if the path could not be found.
        '''
        return self.resourcesLocator.findGetModel(self, typeModel)

    def findGetAllAccessible(self):
        '''
        @see: IResourcesLocator.findGetAllAccessible
        
        Finds all GET paths that can be directly accessed without the need of any path update based on this path,
        basically all paths that can be directly related to this path without any additional information.
        
        @return: list[PathExtended]
            A list of PathExtended from the provided from path that are accessible, empty list if none found.
        '''
        return self.resourcesLocator.findGetAllAccessible(self)

    def toArguments(self, invoker):
        '''
        Provides the list of arguments contained in this path.
        In order to establish for how are the arguments an invoker needs to be provided.
        Lets say that path 'Publication/1' leads to a getById(id) but the path 'Publication/1/Section'
        leads to a getAllSection(publicationId) that is why the invoker is needed since the name of the argument
        will change depending on the invoker.
        
        @param invoker: Invoker
            The invoker to construct arguments for.
        @return: dictionary
            Return the dictionary of arguments of this path the key is the name of the argument, can be empty list
            if there are no arguments.
        '''
        args = {}
        for match in self.matches:
            assert isinstance(match, Match)
            match.asArgument(invoker, args)
        return args

    def update(self, obj, objType):
        '''
        Updates all the matches in the path with the provided value. This method looks like a render method 
        expecting value and type, this because the path is actually a renderer for the paths elements.
        
        @param obj: object
            The object value to update with.
        @param objType: Type
            The object type.
        @return: boolean
            True if at least a match has a successful update, false otherwise.
        '''
        sucess = False
        for match in self.matches:
            assert isinstance(match, Match)
            sucess |= match.update(obj, objType)
        return sucess

    def isValid(self):
        '''
        Checks if the path is valid, this means that the path will provide valid paths elements.
        
        @return: boolean
            True if the path can provide the paths, false otherwise.
        '''
        if self.node is not None:
            valid = True
            for match in self.matches:
                assert isinstance(match, Match)
                valid &= match.isValid()
            return valid
        return False

    def toPaths(self, converterPath):
        '''
        Converts the matches into path elements.
        
        @param converterPath: ConverterPath
            The converter path to use in constructing the paths elements.
        @return: list[string]
            A list of strings representing the paths elements, or None if the path elements cannot be obtained.
        @raise AssertionError:
            If the path cannot be represented, check first the 'isValid' method.
        '''
        assert isinstance(converterPath, ConverterPath), 'Invalid converter path %s' % converterPath
        paths = []
        for k in range(0, len(self.matches)):
            match = self.matches[k]
            assert isinstance(match, Match)
            path = match.toPath(converterPath, k == 0, k == len(self.matches) - 1)
            if path is not None:
                if isinstance(path, list):
                    paths.extend(path)
                paths.append(path)
        return paths

    def clone(self):
        '''
        Clones the path and all match content, any action on the cloned path will node affect the original path.
        
        @return: Path
            The cloned path.
        '''
        return Path(self.resourcesLocator, [match.clone() for match in self.matches], self.node)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.matches == other.matches
        return False

    def __str__(self):
        return '<%s[%s]>' % (self.__class__.__name__, '/'.join(str(match) for match in self.matches))

class PathExtended(Path):
    '''
    The extended path will be directly linked with the matches of the parent path. The basic idea is that if the
    parent path gets updated than also all the paths that extend it will be updated.
    The extended path can only be constructed base on a valid path (has to have a node) and also it needs to be
    valid (to have a node for it self).
    @see: Path
    '''

    def __init__(self, parent, matches, node, index=None):
        '''
        @see: Path.__init__
        
        @param parent: Path
            The parent path that is extended.
        @param index: integer|None 
            The index in the parent path from which this path is extended, None will consider all the matches from
            the parent path.
        '''
        assert isinstance(parent, Path), 'Invalid parent path %' % parent
        assert isinstance(parent.node, Node), 'Invalid parent path node %' % parent.node
        assert isinstance(node, Node), 'Invalid node %' % node
        if index is None:
            index = len(parent.matches)
        else:
            assert isinstance(index, int), 'Invalid index %s' % index
            assert index >= 0 and index <= len(parent.matches), \
            'Invalid index %s, needs to be greater than 0 and less than the parent matches' % index
        self.parent = parent
        self.index = index
        self.matchesOwned = matches
        all = parent.matches[:index]
        all.extend(matches)
        super().__init__(parent.resourcesLocator, all, node)

    def clone(self):
        '''
        @see: Path.clone
        '''
        return PathExtended(self.parent.clone(), [match.clone() for match in self.matchesOwned], self.node, self.index)

# --------------------------------------------------------------------

class AssembleError(Exception):
    '''
    Exception thrown whenever there is an assembly problem.
    '''

class IAssembler(metaclass=abc.ABCMeta):
    '''
    This class needs to be extended.
    Provides support for assembling the calls in the node structure.
    '''

    @abc.abstractmethod
    def knownModelHints(self):
        '''
        Provides the known model hints for the assembler.
        
        @return: dictionary{string:string}|None
            A dictionary containing as a key the allowed hint name and as a value the hint description. 
        '''

    @abc.abstractmethod
    def knownCallHints(self):
        '''
        Provides the known call hints for the assembler.
        
        @return: dictionary{string:string}|None
            A dictionary containing as a key the allowed hint name and as a value the hint description. 
        '''

    @abc.abstractmethod
    def assemble(self, root, invokers):
        '''
        Resolve in the provided root node the invokers, this means that the assembler needs to find a way of 
        mapping the invokers to a resource request path in the node structure contained in the root node 
        provided. If the assembler is able to resolve a invoker or invokers it has to remove them from the list.
        
        @param root: Node
            The root node to assemble the invokers to.
        @param invokers: list[Invoker]
            The list of invokers to be assembled, the list needs to have the resolved invokers removed.
        '''

# --------------------------------------------------------------------

class Normalizer:
    '''
    Provides the normalization for key type strings, like the ones used in paths and content key names.
    '''

    regex_check = re.compile('([a-z_A-Z0-9]+)')

    def normalize(self, name):
        '''
        Normalizes the provided string value as seen fit by the converter.
        The main condition is that the normalized has to be the same for the same value.
        
        @param name: string
            The string value to be normalized.
        @return: string
            The normalized string.
        '''
        assert isinstance(name, str), 'Invalid string name %s' % name
        assert self.regex_check.match(name), 'Invalid name %s' % name
        return name

class Converter:
    '''
    Provides the conversion of primitive types to strings in vice versa.
    The converter provides basic conversion, please extend for more complex or custom transformation.
    '''

    def asString(self, objValue, objType):
        '''
        Converts the provided object to a string. First it will detect the type and based on that it will call
        the corresponding convert method.
        
        @param objValue: object
            The value to be converted to string.
        @param objType: Type
            The type of object to convert the string to.
        @return: string
            The string form of the provided value object.
        '''
        assert isinstance(objType, Type), 'Invalid object type %s' % objType
        assert objValue is not None, 'Provide an object value'
        return str(objValue)

    def asValue(self, strValue, objType):
        '''
        Parses the string value into an object value depending on the provided object type.
        
        @param strValue: string
            The string representation of the object to be parsed.
        @param objType: Type
            The type of object to which the string should be parsed.
        @raise ValueError: In case the parsing was not successful.
        '''
        assert isinstance(objType, Type), 'Invalid object type %s' % objType
        if strValue is None: return None
        if objType.isOf(str):
            return strValue
        if objType.isOf(int):
            return int(strValue)
        if objType.isOf(float):
            return float(strValue)
        if objType.isOf(bool):
            return strValue.strip().lower() == 'true'
        raise AssertionError('Invalid object type %r for converter' % objType)

class ConverterPath(Normalizer, Converter):
    '''
    Provides normalization and conversion for path elements.
    '''

# --------------------------------------------------------------------

class Match(metaclass=abc.ABCMeta):
    '''
    Provides a matched path entry.
    '''

    def __init__(self, node):
        '''
        Constructs a match.
        
        @param node: Node
            The Node node of the match.
        '''
        assert isinstance(node, Node), 'Invalid node %s' % node
        self.node = node

    @abc.abstractmethod
    def asArgument(self, invoker, args):
        '''
        Populates in the provided dictionary of arguments, the key represents the argument name.
        In order to establish for how are the arguments an invoker needs to be provided.
        Lets say that path 'Publication/1' leads to a getById(id) but the path 'Publication/1/Section'
        leads to a getAllSection(publicationId) that is why the invoker is needed since the name of the argument
        will change depending on the invoker.
        
        @param invoker: Invoker
            The invoker to construct arguments for.
        @param args: dictionary
            The dictionary where the argument(s) name and value(s) of this match will be populated.
        '''

    @abc.abstractmethod
    def update(self, obj, objType):
        '''
        Updates the match represented value. This method looks like a render method expecting value and type,
        this because the match is actually a renderer for path elements.
        
        @param obj: object
            The object value to update with.
        @param objType: Type|Model
            The object type.
        @return: boolean
            True if the updated was successful, false otherwise.
        '''

    @abc.abstractmethod
    def isValid(self):
        '''
        Checks if the match is valid, this means that the match will provide a valid path element.
        
        @return: boolean
            True if the match can provide a path, false otherwise.
        '''

    @abc.abstractmethod
    def toPath(self, converterPath, isFirst, isLast):
        '''
        Converts the match into a path or paths elements.
        
        @param converterPath: ConverterPath
            The converter path to use in constructing the path(s) elements.
        @param isFirst: boolean
            A flag indicating that this is the first match in the full path. This flag might be used by some matchers
            to make a different path representation.
        @param isLast: boolean
            A flag indicating that this is the last match in the full path. This flag might be used by some matchers
            to make a different path representation.
        @return: string|list
            A string or list of strings representing the path element.
        @raise AssertionError:
            If the path cannot be represented, check first the 'isValid' method.
        '''

    @abc.abstractmethod
    def clone(self):
        '''
        Clones the match and all content related to it.
        
        @return: Match
            The cloned match.
        '''

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.node == other.node
        return False

class InvokerInfo:
    '''
    Provides the information for an invoker function. 
    '''

    def __init__(self, name, file, line, doc=None):
        '''
        Construct the info.
        
        @param name: string
            The function name.
        @param file: string
            The absolute file path where the function is defined.
        @param line: integer
            The line number where the function is defined.
        @param doc: string|None
            The documentation associated with the invoker.
        @ivar clazz: class|None
            The class where the function is used from.
        @ivar clazzDefiner: class|None
            The class where the function is actually defined in, this is mostly for inheritance cases.
        '''
        assert isinstance(name, str), 'Invalid name %s' % name
        assert isinstance(file, str), 'Invalid file path %s' % file
        assert isinstance(line, int), 'Invalid line number %s' % line
        assert doc is None or isinstance(doc, str), 'Invalid documentation %s' % doc
        self.name = name
        self.file = file
        self.line = line
        self.doc = doc
        self.clazz = None
        self.clazzDefiner = None

class Invoker(metaclass=abc.ABCMeta):
    '''
    Contains all the data required for accessing a call.
    '''

    def __init__(self, name, method, output, inputs, hints, infoIMPL, infoAPI=None):
        '''
        Constructs an invoker.
        
        @param name: string
            The name for the invoker.
        @param method: integer
            The method for the invoker.
        @param output: Type
            The output type of the invoker.
        @param inputs: list[Input]|tuple(Input)
            The list of Inputs for the invoker, attention not all inputs are mandatory.
        @param hints: dictionary{string, object}
            The hints for the invoker.
        @param infoIMPL: InvokerInfo
            The invoker information for the implementation.
        @param infoAPI: InvokerInfo|None
            The invoker information for the API, if one is available.
        '''
        assert isinstance(name, str), 'Invalid name %s' % name
        assert isinstance(method, int), 'Invalid method %s' % method
        assert isinstance(output, Type), 'Invalid output type %s' % output
        assert isinstance(inputs, (list, tuple)), 'Invalid inputs list %s' % inputs
        assert isinstance(hints, dict), 'Invalid hints %s' % hints
        assert isinstance(infoIMPL, InvokerInfo), 'Invalid invoker information %s' % infoIMPL
        assert infoAPI is None or isinstance(infoAPI, InvokerInfo), 'Invalid invoker information %s' % infoAPI

        mandatory = 0
        for inp in inputs:
            assert isinstance(inp, Input), 'Not an input %s' % input
            if inp.hasDefault: break
            mandatory += 1

        self.name = name
        self.method = method
        self.output = output
        self.inputs = inputs
        self.mandatory = mandatory
        self.hints = hints
        self.infoIMPL = infoIMPL
        self.infoAPI = infoAPI

    @abc.abstractmethod
    def invoke(self, *args):
        '''
        Make the invoking and return the resources.
        
        @param args: arguments
            The arguments to use in invoking.
        '''

    def __str__(self):
        inputs = ['%s%s=%s' % ('defaulted:' if i >= self.mandatory else '', inp.name, inp.type)
                  for i, inp in enumerate(self.inputs)]
        return '<%s[%s %s(%s)]>' % (self.__class__.__name__, self.output, self.name, ', '.join(inputs))

class Node(metaclass=abc.ABCMeta):
    '''
    The resource node provides searches and info for resource request paths. Also provides the ability to 
    acknowledge a path(s) as belonging to the node. All nodes implementations need to be exclusive by nature, 
    meaning that not two nodes should be valid for the same path.
    '''

    def __init__(self, parent, isGroup, order):
        '''
        Constructs a resource node. 
        
        @param parent: Node|None 
            The parent node of this node, can be None if is a root node.
        @param isGroup: boolean 
            True if the node represents a group of models, false otherwise.
        @param order: integer 
            The order index of the node, this will be used in correctly ordering the children's to have a proper
            order when searching for path matching.
        @ivar get: Invoker
            The invoker that provides the data elements fetch, populated by assemblers.
        @ivar insert: Invoker
            The invoker that provides the insert of elements, populated by assemblers.
        @ivar update: Invoker
            The invoker that provides the update of elements, populated by assemblers.
        @ivar delete: Invoker
            The invoker that provides the deletion of elements, populated by assemblers.
        @ivar _childrens: list
            The list of node children's.
        '''
        assert parent is None or isinstance(parent, Node), 'Invalid parent %s, can be None' % parent
        assert isinstance(isGroup, bool), 'Invalid is group flag %s' % isGroup
        assert isinstance(order, int), 'Invalid order %s' % order
        self.parent = parent
        self.isGroup = isGroup
        self.order = order
        self.get = None
        self.insert = None
        self.update = None
        self.delete = None
        self._childrens = []
        if parent is not None: parent.addChild(self)

    def addChild(self, child):
        '''
        Adds a new child node to this node.
        
        @param child: Node
            The new child node to add.
        '''
        assert isinstance(child, Node), 'Invalid child node %s' % child
        assert child.parent is self, 'The child has a different parent %s' % child
        assert child not in self._childrens, 'Already contains children node %s' % child
        self._childrens.append(child)
        self._childrens.sort(key=lambda node: node.order)

    def childrens(self):
        '''
        Provides a list with all the children's of the node.
        
        @return: list
            The list of children nodes.
        '''
        return self._childrens

    @abc.abstractmethod
    def tryMatch(self, converterPath, paths):
        '''
        Override to provide functionality.
        Checks if the path(s) element is a match, in this case the paths list needs to be trimmed of the path
        elements that have been acknowledged by this node.
        
        @param converterPath: ConverterPath
            The converter path to be used in matching the provided path(s).
        @param paths: list[string]
            The path elements list containing strings, this list will get consumed whenever a matching occurs.
        @return: Match|list[Match]|boolean
            If a match has occurred than a match or a list with match objects will be returned or True if there
            is no match to provide by this node, if not than None or False is returned.
        '''

    @abc.abstractmethod
    def newMatch(self):
        '''
        Override to provide functionality.
        Constructs a blank match object represented by this node, this is used in creating path for nodes.
        So basically this used when we need a path for a node.
        
        @return: Match|list|None
            A match object or a list with match objects, None if there is no match needed by this node.
        '''

    @abc.abstractmethod
    def __eq__(self, other):
        '''
        Needs to have the equal implemented in order to determine if there isn't already a child node with the same
        specification in the parent.
        '''

# --------------------------------------------------------------------

class IResourcesRegister(metaclass=abc.ABCMeta):
    '''
    Provides the specifications for the resources register. This will contain the resources tree and provide abilities
    to update the tree.
    '''

    @abc.abstractmethod
    def getRoot(self):
        '''
        Provides the root node of this resource repository.
        
        @return: Node
            The root Node.
        '''

    @abc.abstractmethod
    def register(self, implementation):
        '''
        Register the provided API service implementation into the resource node tree.
    
        @param implementation: object
            The implementation for and API service.
        '''

class IResourcesLocator(metaclass=abc.ABCMeta):
    '''
    Provides the specifications for the resources locator. This the abilities to find resources.
    '''

    @abc.abstractmethod
    def findPath(self, converterPath, paths):
        '''
        Finds the resource node for the provided request path.
        
        @param converterPath: ConverterPath
            The converter path used in handling the path elements.
        @param paths: list[string]
            A list of string path elements identifying a resource to be searched for, this list will be consumed 
            of every path element that was successfully identified.
        @return: Path
            The path leading to the node that provides the resource if the Path has no node it means that the paths
            have been recognized only to certain point.
        '''

    @abc.abstractmethod
    def findGetModel(self, fromPath, typeModel):
        '''
        Finds the path for the first Node that provides a get for the name. The search is made based
        on the from path. First the from path Node and is children's are searched for the get method if 
        not found it will go to the Nodes parent and make the search there, so forth and so on.
        
        @param fromPath: Path
            The path to make the search based on.
        @param typeModel: TypeModel
            The type model to search the get for.
        @return: PathExtended|None
            The extended path pointing to the desired get method, attention some updates might be necessary on 
            the path to be available. None if the path could not be found.
        '''

    @abc.abstractmethod
    def findGetAllAccessible(self, fromPath):
        '''
        Finds all GET paths that can be directly accessed without the need of any path update based on the
        provided from path, basically all paths that can be directly related to the provided path without any
        additional information.
        
        @param fromPath: Path
            The path to make the search based on.
        @return: list[PathExtended]
            A list of PathExtended from the provided from path that are accessible, empty list if none found.
        '''