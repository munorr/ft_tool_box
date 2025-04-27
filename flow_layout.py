try:
    from PySide6 import QtWidgets, QtCore, QtGui
    import shiboken6 as shiboken
    import sip
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    import shiboken2 as shiboken
    try:
        import sip
    except ImportError:
        # If sip is not available, create a simple isdeleted function
        sip = type('sip', (), {'isdeleted': lambda obj: False})

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
        # Clear all items
        while self.itemList:
            self.takeAt(0)
    
    def is_valid_item(self, item):
        """Helper method to consistently check if an item is valid and usable"""
        try:
            # First check if item exists and isn't deleted
            if item is None or sip.isdeleted(item):
                return False
                
            # Then check if widget exists and isn't deleted
            widget = item.widget()
            if widget is None or sip.isdeleted(widget):
                return False
                
            # Additional check: verify the widget is still valid
            # This catches more obscure cases of invalid widgets
            widget.size()  # This will raise an exception if widget is invalid
            return True
        except (RuntimeError, ReferenceError, AttributeError, TypeError):
            return False
    
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
        
        # Get only valid items
        valid_items = [item for item in self.itemList if self.is_valid_item(item)]
        
        # If horizontal_only or horizontal_priority is True, calculate total width
        if self.horizontal_only or self.horizontal_priority:
            width = 0
            height = 0
            
            for item in valid_items:
                item_size = item.sizeHint()
                width += item_size.width() + self.spacing()
                height = max(height, item_size.height())
            
            if valid_items:
                width -= self.spacing()  # Remove extra spacing after last item
            
            size = QtCore.QSize(width, height)
        else:
            # Default behavior for regular flow layout
            for item in valid_items:
                size = size.expandedTo(item.minimumSize())
        
        # Add margins to the size
        margins = self.contentsMargins()
        size += QtCore.QSize(margins.left() + margins.right(), 
                             margins.top() + margins.bottom())
        return size
    
    def doLayout(self, rect, testOnly):
        """Arrange items according to layout rules"""
        # Initialize position with margins
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        lineHeight = 0
        
        # Filter out invalid items first
        valid_items = [item for item in self.itemList if self.is_valid_item(item)]
        
        # For horizontal_only layout - just arrange items in a single row
        if self.horizontal_only:
            for item in valid_items:
                spaceX = self.spacing()
                
                # Position the item
                if not testOnly:
                    item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
                
                # Move to the next position
                x += item.sizeHint().width() + spaceX
                lineHeight = max(lineHeight, item.sizeHint().height())
            
            return y + lineHeight - rect.y() + margins.bottom()
        
        # Regular flow layout with optional horizontal priority
        available_width = rect.width() - margins.left() - margins.right()
        
        for item in valid_items:
            item_width = item.sizeHint().width()
            item_height = item.sizeHint().height()
            spaceX = self.spacing()
            spaceY = self.spacing()
            
            nextX = x + item_width + spaceX
            
            # Check if we need to wrap to the next line
            if (nextX - spaceX > rect.right() - margins.right() and 
                lineHeight > 0 and 
                not self.horizontal_priority):
                # Standard wrapping behavior
                x = rect.x() + margins.left()
                y = y + lineHeight + spaceY
                nextX = x + item_width + spaceX
                lineHeight = 0
            
            # Position the item
            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
            
            # Move to the next position
            x = nextX
            lineHeight = max(lineHeight, item_height)
        
        return y + lineHeight - rect.y() + margins.bottom()
    
    def invalidate(self):
        """Force the layout to be recalculated"""
        self.update()
        
    def reset(self):
        """Reset the layout state completely
        
        This method should be called when the layout is being reused after a window close/reopen
        to ensure all cached state is cleared and the layout is properly reinitialized.
        """
        # Create a clean copy of valid items - prevents modification issues during iteration
        valid_items = [item for item in self.itemList if self.is_valid_item(item)]
        
        # Clear the item list completely first
        self.itemList = []
        
        # Add back only the valid items
        for item in valid_items:
            self.addItem(item)
            
        # Force a complete layout recalculation
        self.invalidate()
        
        # Request an immediate geometry update
        parent = self.parent()
        if parent:
            parent.updateGeometry()