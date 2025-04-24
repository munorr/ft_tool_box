try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui

class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=0, spacing=2, horizontal_priority=True, horizontal_only=False):
        super(FlowLayout, self).__init__(parent)
        
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        
        self.setSpacing(spacing)
        self.horizontal_priority = horizontal_priority  # Prioritize horizontal stacking
        self.horizontal_only = horizontal_only  # Force horizontal-only layout
        
        self.itemList = []
    
    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    
    def addItem(self, item):
        self.itemList.append(item)
    
    def count(self):
        return len(self.itemList)
    
    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None
    
    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None
    
    def expandingDirections(self):
        return QtCore.Qt.Orientations(QtCore.Qt.Orientation(0))
    
    def hasHeightForWidth(self):
        return True
    
    def heightForWidth(self, width):
        height = self.doLayout(QtCore.QRect(0, 0, width, 0), True)
        return height
    
    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        size = QtCore.QSize()
        
        # If horizontal_only or horizontal_priority is True, calculate total width
        if self.horizontal_only or self.horizontal_priority:
            width = 0
            height = 0
            
            for item in self.itemList:
                item_size = item.sizeHint()
                width += item_size.width() + self.spacing()
                height = max(height, item_size.height())
            
            if len(self.itemList) > 0:
                width -= self.spacing()  # Remove extra spacing after last item
            
            size = QtCore.QSize(width, height)
        else:
            # Default behavior for regular flow layout
            for item in self.itemList:
                size = size.expandedTo(item.minimumSize())
        
        margin = self.contentsMargins().left() + self.contentsMargins().right() + self.contentsMargins().top() + self.contentsMargins().bottom()
        size += QtCore.QSize(margin, margin)
        return size
    
    def doLayout(self, rect, testOnly):
        x = rect.x() + self.contentsMargins().left()
        y = rect.y() + self.contentsMargins().top()
        lineHeight = 0
        
        # If horizontal_only is True, just arrange items in a single row
        if self.horizontal_only:
            for item in self.itemList:
                wid = item.widget()
                spaceX = self.spacing() + wid.style().layoutSpacing(
                    QtWidgets.QSizePolicy.PushButton,
                    QtWidgets.QSizePolicy.PushButton,
                    QtCore.Qt.Horizontal)
                
                if not testOnly:
                    item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
                
                x += item.sizeHint().width() + spaceX
                lineHeight = max(lineHeight, item.sizeHint().height())
            
            return y + lineHeight - rect.y() + self.contentsMargins().bottom()
        
        # Regular flow layout with optional horizontal priority
        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing()
            spaceY = self.spacing()
            
            nextX = x + item.sizeHint().width() + spaceX
            
            # Check if we need to wrap to the next line
            if nextX - spaceX > rect.right() and lineHeight > 0:
                if not self.horizontal_priority:
                    # Standard wrapping behavior
                    x = rect.x() + self.contentsMargins().left()
                    y = y + lineHeight + spaceY
                    nextX = x + item.sizeHint().width() + spaceX
                    lineHeight = 0
                # If horizontal_priority is True, we don't wrap and just continue horizontally
            
            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
            
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        
        return y + lineHeight - rect.y() + self.contentsMargins().bottom()
