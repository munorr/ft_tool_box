try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore

class CustomGridLayout(QtWidgets.QGridLayout):
    """
    A custom grid layout that automatically arranges widgets in a grid pattern.
    
    Usage:
        # Create a vertical layout (one column, multiple rows)
        layout = CustomGridLayout(rows=3, cols=0)  # 3 rows, auto columns
        
        # Create a horizontal layout (one row, multiple columns)
        layout = CustomGridLayout(rows=0, cols=4)  # auto rows, 4 columns
        
        # Add widgets without specifying position
        layout.addWidget(widget1)
        layout.addWidget(widget2)
        layout.addWidget(widget3)
    """
    
    def __init__(self, rows=0, cols=0, parent=None):
        """
        Initialize the CustomGridLayout.
        
        Args:
            rows (int): Number of rows in the grid. If 0, rows will be determined automatically.
            cols (int): Number of columns in the grid. If 0, columns will be determined automatically.
            parent (QWidget, optional): Parent widget.
        """
        super(CustomGridLayout, self).__init__(parent)
        self.rows = rows
        self.cols = cols
        self.widget_count = 0
        
        # Validate input
        if rows == 0 and cols == 0:
            # Default to horizontal layout if both are 0
            self.rows = 1
            self.cols = 0
        
        # Set spacing and margins
        self.setSpacing(4)
        self.setContentsMargins(0, 0, 0, 0)
    
    def addWidget(self, widget, row=None, col=None, rowSpan=1, colSpan=1, alignment=QtCore.Qt.AlignTop):
        """
        Add a widget to the grid layout at the next available position.
        
        Args:
            widget (QWidget): Widget to add to the layout.
            row (int, optional): Row to place the widget. If None, determined automatically.
            col (int, optional): Column to place the widget. If None, determined automatically.
            rowSpan (int, optional): Number of rows the widget spans.
            colSpan (int, optional): Number of columns the widget spans.
            alignment (Qt.Alignment, optional): Alignment of the widget.
        """
        if row is not None and col is not None:
            # If position is explicitly specified, use the standard method
            super(CustomGridLayout, self).addWidget(widget, row, col, rowSpan, colSpan, alignment)
            # Update widget count if needed
            self.widget_count = max(self.widget_count, (row + rowSpan) * (col + colSpan))
            return
        
        # Auto-calculate position based on layout type
        if self.rows > 0 and self.cols == 0:
            # Vertical layout (fixed rows)
            row = self.widget_count % self.rows
            col = self.widget_count // self.rows
        elif self.rows == 0 and self.cols > 0:
            # Horizontal layout (fixed columns)
            row = self.widget_count // self.cols
            col = self.widget_count % self.cols
        else:
            # Grid layout with both dimensions specified
            row = self.widget_count // self.cols
            col = self.widget_count % self.cols
        
        # Add the widget at the calculated position
        super(CustomGridLayout, self).addWidget(widget, row, col, rowSpan, colSpan)
        self.widget_count += 1
    
    def clear(self):
        """
        Remove all widgets from the layout.
        """
        for i in reversed(range(self.count())):
            item = self.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    self.removeWidget(widget)
        self.widget_count = 0
    
    def grid(self, rows, cols):
        """
        Reconfigure the grid dimensions.
        
        Args:
            rows (int): Number of rows in the grid. If 0, rows will be determined automatically.
            cols (int): Number of columns in the grid. If 0, columns will be determined automatically.
        """
        self.rows = rows
        self.cols = cols
        
        # Validate input
        if rows == 0 and cols == 0:
            # Default to horizontal layout if both are 0
            self.rows = 1
            self.cols = 0
        
        # Rearrange existing widgets
        widgets = []
        for i in range(self.count()):
            item = self.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())
        
        self.clear()
        
        # Re-add widgets with new arrangement
        for widget in widgets:
            self.addWidget(widget)
