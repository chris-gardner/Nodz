from Qt import QtGui, QtCore, QtWidgets
import nodz_main

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
        #hide by default
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
            maxSize.setWidth(max(maxSize.width(), boundingSize.width()+30))  #30 is for margin
        self.resize(maxSize.width(), self.size().height())

    def focusOutEvent(self, QFocusEvent):
        self.popdown()

    def onCompleterActivatedSlot(self, text):
        pos=QtCore.QPointF(self.nodzInst.mapToScene(self.pos()))
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
    def __init__(self, start_node, hspace=400, vspace=100, padding=300):
        self.voffset = 0
        self.hspace = hspace
        self.vspace = vspace
        self.padding = padding
        
        self.start_node = start_node
        
        rect = start_node.scene().sceneRect()
        self.cx = rect.right()
        self.cy = rect.bottom()
        
        self.bbmin = [999999999, 999999999]
        self.bbmax = [-999999999, -999999999]
        
        self.visited_nodes = []
    
    
    def arrange(self):
        self.visited_nodes = []
        
        pos = self.adjuster(self.start_node)
        
        scene = self.start_node.scene()
        
        # gotta adjust the scene bounding box to fit all the nodes in
        for node in self.visited_nodes:
            node.checkIsWithinSceneRect()
        
        # updateScene() forces the graph edges to redraw after the nodes have been moved
        scene.updateScene()
        
        return pos
    
    
    def get_max_child_count(self, node):
        """
        Maximum
        :param node:
        :return:
        """
        ret = 0
        for conn in node.sockets['layers'].connections:
            ret += 1
            node_coll = [x for x in node.scene().nodes.values() if x.name == conn.plugNode]
            connected_node = node_coll[0]
            
            ret += self.get_max_child_count(connected_node)
        
        return ret
    
    
    def adjust_bbox(self, pos):
        if pos.x() < self.bbmin[0]:
            self.bbmin[0] = pos.x()
        if pos.x() > self.bbmax[0]:
            self.bbmax[0] = pos.x()
        
        if pos.y() < self.bbmin[1]:
            self.bbmin[1] = pos.y()
        if pos.y() > self.bbmax[1]:
            self.bbmax[1] = pos.y()
    
    
    def adjuster(self, start_node, depth=0):
        
        start_voffset = self.voffset
        connected_nodes = []
        for i, conn in enumerate(start_node.sockets['layers'].connections):
            node_coll = [x for x in start_node.scene().nodes.values() if x.name == conn.plugNode]
            connected_nodes.append(node_coll[0])
        for i, conn in enumerate(start_node.sockets['clips'].connections):
            node_coll = [x for x in start_node.scene().nodes.values() if x.name == conn.plugNode]
            connected_nodes.append(node_coll[0])
        
        if connected_nodes:
            # it has children. average it's position vertically
            avg = 0
            for node in connected_nodes:
                if node not in self.visited_nodes:
                    avg += self.adjuster(node, depth=depth + 1)
                    self.visited_nodes.append(node)
            avg /= len(connected_nodes)
            
            if len(connected_nodes) == 1:
                # if just one child node, copy the vertical position
                pos = QtCore.QPointF(self.cx - depth * self.hspace, connected_nodes[0].pos().y())
            else:
                # more than one child - use the average
                pos = QtCore.QPointF(self.cx - depth * self.hspace, self.cy - avg * self.vspace)
            
            start_node.setPos(pos)
            self.adjust_bbox(pos)
        
        else:
            if start_node not in self.visited_nodes:
                # nothing connected. stack it's position vertically
                pos = QtCore.QPointF(self.cx - depth * self.hspace, self.cy - (self.voffset) * self.vspace)
                start_node.setPos(pos)
                self.voffset += 1
                self.adjust_bbox(pos)
                self.visited_nodes.append(start_node)
        
        if depth == 0:
            # redraw all the connections and stuff
            start_node.scene().updateScene()
        
        return start_voffset + (self.voffset - start_voffset) * 0.5

