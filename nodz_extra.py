from __future__ import print_function

from Qt import QtGui, QtCore, QtWidgets


class QtPopupLineEditWidget(QtWidgets.QLineEdit):
    
    @staticmethod
    def defaultNodeCreator(nodzInst, nodeName, pos):
        nodzInst.createNode(name=nodeName, position=pos)
    
    
    def __init__(self, nodzInst, nodeList=[], nodeCreator=None):
        """
        Initialize the graphics view.

        """
        super(QtPopupLineEditWidget, self).__init__(nodzInst)
        self.nodzInst = nodzInst
        self.nodeList = nodeList
        if nodeCreator is None:
            self.nodeCreator = self.defaultNodeCreator
        else:
            self.nodeCreator = nodeCreator
        self.returnPressed.connect(self.onReturnPressedSlot)
        # hide by default
        self.hide()
        self.clear()
        self.parentWidget().setFocus()
    
    
    def popup(self):
        position = self.parentWidget().mapFromGlobal(QtGui.QCursor.pos())
        self.move(position)
        self.clear()
        self.show()
        self.setFocus()
        self.setNodesList(self.nodeList)
        self.completer.complete()
    
    
    def popdown(self):
        self.hide()
        self.clear()
        self.parentWidget().setFocus()
    
    
    def setNodesList(self, nodeList):
        self.nodeList = nodeList
        self.completer = QtWidgets.QCompleter(self.nodeList, self)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setCompleter(self.completer)
        self.completer.activated.connect(self.onCompleterActivatedSlot)
        
        fontMetrics = QtGui.QFontMetrics(self.font())
        maxSize = self.size()
        for nodeName in self.nodeList:
            boundingSize = fontMetrics.boundingRect(nodeName).size()
            maxSize.setWidth(max(maxSize.width(), boundingSize.width() + 30))  # 30 is for margin
        self.resize(maxSize.width(), self.size().height())
    
    
    def focusOutEvent(self, QFocusEvent):
        self.popdown()
    
    
    def onCompleterActivatedSlot(self, text):
        pos = QtCore.QPointF(self.nodzInst.mapToScene(self.pos()))
        self.popdown()
        newNode = self.nodeCreator(self.nodzInst, text, pos)
        if newNode is not None:
            self.nodzInst.signal_UndoRedoAddNode.emit(self.nodzInst, newNode.userData)
    
    
    def onReturnPressedSlot(self):
        name = self.text()
        pos = QtCore.QPointF(self.nodzInst.mapToScene(self.pos()))
        self.completer.activated.disconnect(self.onCompleterActivatedSlot)
        self.popdown()
        newNode = self.nodeCreator(self.nodzInst, name, pos)
        if newNode is not None:
            self.nodzInst.signal_UndoRedoAddNode.emit(self.nodzInst, newNode.userData)


class Arranger(object):
    def __init__(self, start_node, hspace=400, vspace=100, padding=200):
        self.voffset = 0
        self.hspace = hspace
        self.vspace = vspace
        self.padding = padding
        
        self.start_node = start_node
        self.scene = self.start_node.scene()
        
        self.cx = 0
        self.cy = 0
        
        self.bbmin = [999999999, 999999999]
        self.bbmax = [-999999999, -999999999]
        
        self.visited_nodes = []
        self.arranged_nodes = []
        self.node_depths = {}
        self.fuck = [0]
    
    
    def get_node_depths(self, node, depth=0):
        """
        Get the maximum possible depth of all the nodes
        """
        
        if node.name not in self.node_depths:
            self.node_depths[node.name] = depth
        else:
            self.node_depths[node.name] = max(depth, self.node_depths[node.name])
        
        socket_names = node.sockets.keys()
        for socket in socket_names:
            for i, conn in enumerate(node.sockets[socket].connections):
                conn_node = self.scene.nodes[conn.plugNode]
                self.get_node_depths(conn_node, depth=depth + 1)
    
    
    def arrange(self):
        if not self.start_node:
            return
        
        self.get_node_depths(self.start_node)
        
        self.visited_nodes = []
        
        self.adjuster(self.start_node)
        
        # gotta adjust the scene bounding box to fit all the nodes in
        for node in self.visited_nodes:
            node.checkIsWithinSceneRect()
        
        # updateScene() forces the graph edges to redraw after the nodes have been moved
        self.scene.updateScene()
    
    
    def adjust_bbox(self, pos):
        if pos.x() < self.bbmin[0]:
            self.bbmin[0] = pos.x()
        if pos.x() > self.bbmax[0]:
            self.bbmax[0] = pos.x()
        
        if pos.y() < self.bbmin[1]:
            self.bbmin[1] = pos.y()
        if pos.y() > self.bbmax[1]:
            self.bbmax[1] = pos.y()
    
    
    def adjuster(self, start_node, depth=0, index=0):
        node_depth = self.node_depths[start_node.name]
        if start_node not in self.visited_nodes:
            if index > 0:
                # we don't increment the v pos if we're hanging off the first port
                # in that case, we want to line up with the parent node
                self.voffset += 1
        start_y = self.voffset
        
        connected_nodes = []
        # loop over the attrs list rather than the sockets directly
        # because py 2.7 dicts don't maintain order
        for attr in start_node.attrs:
            attrdata = start_node.attrsData[attr]
            if attrdata['socket']:
                for i, conn in enumerate(start_node.sockets[attr].connections):
                    node_coll = [x for x in self.scene.nodes.values() if x.name == conn.plugNode]
                    connected_nodes.append(node_coll[0])
        
        if connected_nodes:
            for i, node in enumerate(connected_nodes):
                self.adjuster(node, depth=depth + 1, index=i)
        
        if start_node not in self.visited_nodes:
            pos = QtCore.QPointF(self.cx - node_depth * self.hspace, start_y * self.vspace)
            start_node.setPos(pos)
            self.adjust_bbox(pos)
            self.visited_nodes.append(start_node)
        
        return start_y
