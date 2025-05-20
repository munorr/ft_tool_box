try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtGui import QColor, QPainter, QPainterPath
    from PySide6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, Qt, QRect
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtGui import QColor, QPainter, QPainterPath
    from PySide2.QtCore import QTimer, QPropertyAnimation, QEasingCurve, Qt, QRect
    from shiboken2 import wrapInstance

import maya.cmds as cmds
import maya.mel as mel


from . import utils as UT
from . import custom_line_edit as CLE

class TwoColumnMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_widget = QtWidgets.QWidget(self)
        self.grid_layout = QtWidgets.QGridLayout(self.grid_widget)
        gls = 6 # grid layout spacing
        self.grid_layout.setSpacing(gls)
        self.grid_layout.setContentsMargins(gls, gls, gls, gls)

        # Background color for the menu
        self.bg_color = "rgba(35, 35, 35, 1)"
        
        # Add the grid widget to the menu using a QWidgetAction
        widget_action = QtWidgets.QWidgetAction(self)
        widget_action.setDefaultWidget(self.grid_widget)
        self.addAction(widget_action)
        
        # Apply styling
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet('QMenu { background-color: transparent; border: none; }')
        self.grid_widget.setStyleSheet(f'''
                QWidget {{
                    background-color: {self.bg_color};
                    border: 1px solid #444444;
                    border-radius: 3px;
                    padding:  4px 5px;
                }}''')

    def _create_menu_button(self, action):
        # Extract text, function and color from the action
        text = ''
        func = None
        button_color = None
        
        # Handle QAction
        if isinstance(action, QtWidgets.QAction):
            text = action.text()
            icon = action.icon() if action.icon() else None
            
            def trigger_action():
                self.close()
                action.triggered.emit()
                
            func = trigger_action
            
        # Handle tuple with properties dictionary
        elif isinstance(action, tuple) and len(action) >= 2 and isinstance(action[1], dict):
            properties = action[1]
            button_action = action[0]
            
            # Get color from properties if available
            if 'color' in properties and properties['color']:
                button_color = properties['color']
            
            # Handle different action types
            if isinstance(button_action, QtWidgets.QAction):
                text = button_action.text()
                icon = button_action.icon() if button_action.icon() else None
                
                def trigger_action():
                    self.close()
                    button_action.triggered.emit()
                    
                func = trigger_action
            
            elif isinstance(button_action, tuple) and len(button_action) >= 2:
                text = str(button_action[0])
                if callable(button_action[1]):
                    action_func = button_action[1]
                    
                    def call_func():
                        self.close()
                        action_func()
                        
                    func = call_func
            
            else:
                text = str(button_action)
        
        # Handle simple tuple (text, function)
        elif isinstance(action, tuple) and len(action) >= 2:
            text = str(action[0])
            if callable(action[1]):
                action_func = action[1]
                
                def call_func():
                    self.close()
                    action_func()
                    
                func = call_func
        
        # Handle any other case
        else:
            text = str(action)
        
        # Create the button
        button = QtWidgets.QPushButton(text)
        if func:
            button.clicked.connect(func)
        
        # Use custom color if provided, otherwise use parent's color
        bg_color = button_color if button_color else self.parent().cmColor
        
        # Make sure we're using the actual color value, not None
        if bg_color is not None:
            button.setStyleSheet(f'''
                QPushButton {{
                    background-color: {UT.rgba_value(bg_color, 1)};
                    color: white;
                    border: none;
                    padding: 3px 10px;
                    border-radius: 3px;
                    text-align: center;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {UT.rgba_value(bg_color, 1.2)};
                }}
            ''')
        button.setFixedHeight(self.parent().cmHeight)
        return button

    def _create_separator(self):
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFixedHeight(2)
        separator.setStyleSheet("""
            QFrame {
                background-color: #444444;
                margin: 4px 5px;
                border-radius: 1px;
            }
        """)
        return separator
    
    def _create_menu_label(self, text):
        label = QtWidgets.QLabel(text)
        label.setStyleSheet(f'''
            QLabel {{
                color: #999999;
                background-color: transparent;
                border: none;
                padding: 0px 10px;
                font-size: 11px;
            }}
        ''')
        label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label.setFixedHeight(self.parent().cmHeight)
        return label

    def rebuild_grid(self, actions):
        # Clear existing items
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # Separate positioned and unpositioned items
        positioned = []
        unpositioned = []
        max_row = max_col = -1
        
        for item in actions:
            # Check for special types (separator, label)
            if isinstance(item, tuple):
                # Check for new label format: ('label', text, properties)
                if len(item) == 3 and item[0] == 'label':
                    label_text = item[1]
                    properties = item[2]
                    
                    # Extract position and span information
                    if isinstance(properties, dict):
                        # New format with properties dictionary
                        position = properties.get('position')
                        rowSpan = properties.get('rowSpan', 1)
                        colSpan = properties.get('colSpan', 1)
                    else:
                        # Legacy format with just position
                        position = properties
                        rowSpan = 1
                        colSpan = 1
                    
                    positioned.append(('label', label_text, position, rowSpan, colSpan))
                    if position:
                        max_row = max(max_row, position[0] + rowSpan - 1)
                        max_col = max(max_col, position[1] + colSpan - 1)
                    else:
                        unpositioned.append(('label', label_text, rowSpan, colSpan))
                    continue
                    
                # Check for separator with new format: ('separator', properties)
                if len(item) == 2 and item[0] == 'separator':
                    properties = item[1]
                    
                    # Extract position and span information
                    if isinstance(properties, dict):
                        # New format with properties dictionary
                        position = properties.get('position')
                        rowSpan = properties.get('rowSpan', 1)
                        colSpan = properties.get('colSpan', 1)
                    else:
                        # Legacy format with just position
                        position = properties
                        rowSpan = 1
                        colSpan = 2  # Default separator spans 2 columns
                    
                    positioned.append(('separator', None, position, rowSpan, colSpan))
                    if position:
                        max_row = max(max_row, position[0] + rowSpan - 1)
                        max_col = max(max_col, position[1] + colSpan - 1)
                    continue
                
                # Handle regular action items
                if len(item) >= 2:
                    # Extract action and properties
                    action = None
                    position = None
                    rowSpan = 1
                    colSpan = 1
                    
                    if isinstance(item[1], dict):
                        # New format with properties dictionary
                        action = item[0]
                        properties = item[1]
                        
                        # Extract position and span information
                        position = properties.get('position')
                        rowSpan = properties.get('rowSpan', 1)
                        colSpan = properties.get('colSpan', 1)
                    elif isinstance(item[1], tuple):
                        # Legacy format with position tuple
                        action = item[0]
                        position = item[1]
                        rowSpan = item[2] if len(item) > 2 else 1
                        colSpan = item[3] if len(item) > 3 else 1
                    else:
                        # Other tuple format
                        action = item[0]
                        position = item[1] if len(item) > 1 else None
                        
                    # Add to appropriate list based on position
                    if position is not None:
                        positioned.append(('action', action, position, rowSpan, colSpan))
                        max_row = max(max_row, position[0] + rowSpan - 1)
                        max_col = max(max_col, position[1] + colSpan - 1)
                    else:
                        unpositioned.append(('action', action, rowSpan, colSpan))
                else:
                    # Simple tuple item
                    unpositioned.append(('action', item, 1, 1))
            else:
                # Simple item (not a tuple)
                unpositioned.append(('action', item, 1, 1))
        
        # Place positioned items first
        for item_type, item, pos, rowSpan, colSpan in positioned:
            if item_type == 'separator':
                widget = self._create_separator()
            elif item_type == 'label':
                widget = self._create_menu_label(item)
            else:  # 'action'
                if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], dict):
                    # New format - pass the whole item to create_menu_button
                    widget = self._create_menu_button(item)
                else:
                    # Legacy format
                    widget = self._create_menu_button(item)
                    
            self.grid_layout.addWidget(widget, pos[0], pos[1], rowSpan, colSpan)
        
        # Find available positions for unpositioned items
        if unpositioned:
            next_row = 0 if max_row == -1 else max_row + 1
            next_col = 0
            
            for item_type, item, rowSpan, colSpan in unpositioned:
                if item_type == 'label':
                    widget = self._create_menu_label(item)
                else:  # 'action'
                    if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], dict):
                        # New format - pass the whole item to create_menu_button
                        widget = self._create_menu_button(item)
                    else:
                        # Legacy format
                        widget = self._create_menu_button(item)
                    
                # If this item would overflow the columns, move to next row
                if next_col + colSpan > 2:
                    next_col = 0
                    next_row += 1
                self.grid_layout.addWidget(widget, next_row, next_col, rowSpan, colSpan)
                next_col += colSpan
                if next_col >= 2:
                    next_col = 0
                    next_row += rowSpan
        
        self.grid_widget.adjustSize()
        self.adjustSize()
        
class CustomButton(QtWidgets.QPushButton):
    singleClicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()
    rightClicked = QtCore.Signal(QtCore.QPoint)

    def __init__(self, text='', icon=None, color='#4d4d4d', tooltip='', flat=False, size=None, width=None, height=None, parent=None, radius=3, ContextMenu=False, 
                 cmColor='#444444', cmHeight = 20, onlyContext=False, alpha=1, textColor='white', text_size=12):
        super().__init__(parent)
        self.setFlat(flat)
        self.base_color = color
        self.radius = radius
        self.cmColor = cmColor
        self.onlyContext = onlyContext
        self.alpha = alpha
        self.textSize = text_size
        self.textColor = textColor
        self.menu_actions = []  # Store menu actions
        self.cmHeight = cmHeight
        self.rename_line_edit = None  # Initialize rename_line_edit attribute
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setStyleSheet(self.get_style_sheet(color, flat, radius))
        
        icon_size = size if size else 24
        
        if icon:
            self.setIcon(QtGui.QIcon(icon))
            self.setIconSize(QtCore.QSize(icon_size, icon_size))
        
        if text:
            self.setText(text)
            if height is None:
                self.setFixedHeight(24)
            if width is None:
                if icon:
                    self.setMinimumWidth(self.calculate_button_width(text, padding=30))
                    self.setStyleSheet(self.styleSheet() + " QPushButton { text-align: right; padding-right: 10px; }")
                else:
                    self.setMinimumWidth(self.calculate_button_width(text))
        elif icon and (width is None or height is None):
            self.setFixedSize(icon_size, icon_size)
        
        if width is not None:
            self.setFixedWidth(width)
        if height is not None:
            self.setFixedHeight(height)
        
        if icon and text:
            self.setLayoutDirection(QtCore.Qt.LeftToRight)
        
        self.setToolTip(f"<html><body><p style='color:white; white-space:nowrap; '>{tooltip}</p></body></html>")
        
        self.context_menu = None
        self.has_context_menu = ContextMenu or onlyContext
        if self.has_context_menu:
            self.context_menu = TwoColumnMenu(self)
            #self.context_menu = QtWidgets.QMenu(self)
            self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu)

        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.performSingleClick)
        self.click_count = 0
        self.reset_button_state()
        
        # Explicitly set the cursor to ArrowCursor to prevent inheriting parent's cursor
        self.setCursor(QtCore.Qt.ArrowCursor)

        #--------------------------------------------------------------------------------------------------------
    
    def get_style_sheet(self, color, flat, radius):
        if flat:
            return f'''
                QPushButton {{
                    background-color: transparent;
                    color: {self.textColor};
                    border: none;
                    padding: 1px;
                    border-radius: {radius}px;
                    font-size: {self.textSize}px;
                }}
                QPushButton:hover {{
                    color: {UT.rgba_value(self.textColor, 1.2)};
                }}
            '''
        else:
            return f'''
                QPushButton {{
                    background-color: {UT.rgba_value(color, 1.0)}; 
                    color: {self.textColor};
                    border: none;
                    padding: 1px;
                    border-radius: {radius}px;
                    font-size: {self.textSize}px;
                }}
                QPushButton:hover {{
                    background-color: {UT.rgba_value(color, 1.2)};
                }}
                QPushButton:pressed {{
                    background-color: {UT.rgba_value(color, 0.8)};
                }}
                QToolTip {{
                    background-color: {color};
                    color: white;
                    border: 0px;
                }}
            '''
        
    def calculate_button_width(self, text, padding=20):
        font_metrics = QtGui.QFontMetrics(QtWidgets.QApplication.font())
        text_width = font_metrics.horizontalAdvance(text)
        return text_width + padding

    def addMenuSeparator(self, position=None, rowSpan=1, colSpan=1):
        """
        Add a separator line to the context menu.
        Args:
            position (tuple, optional): (row) position in the grid
            rowSpan (int, optional): Number of rows the separator spans
            colSpan (int, optional): Number of columns the separator spans
        """
        if self.context_menu:
            properties = {
                'position': position,
                'rowSpan': rowSpan,
                'colSpan': colSpan
            }
            self.menu_actions.append(('separator', properties))
            self.context_menu.rebuild_grid(self.menu_actions)

    def addMenuLabel(self, text, position=None, rowSpan=1, colSpan=1):
        """
        Add a label to the context menu.
        Args:
            text (str): Text to display in the menu
            position (tuple, optional): (row, column) position in the grid
            rowSpan (int, optional): Number of rows the label spans
            colSpan (int, optional): Number of columns the label spans
        """
        if self.context_menu:
            # Use 'label' as a special identifier for text labels
            properties = {
                'position': position,
                'rowSpan': rowSpan,
                'colSpan': colSpan
            }
            self.menu_actions.append(('label', text, properties))
            self.context_menu.rebuild_grid(self.menu_actions)

    def addToMenu(self, name, function, icon=None, position=None, rowSpan=1, colSpan=1, color=None):
        """
        Add an item to the context menu.
        Args:
            name (str): Text to display in the menu
            function: Callback function when item is clicked
            icon (str, optional): Icon path/resource
            position (tuple, optional): (row, column) position in the grid
            rowSpan (int, optional): Number of rows the item spans
            colSpan (int, optional): Number of columns the item spans
            color (str, optional): Custom color for the menu button (hex format, e.g. '#ff0000')
        """
        if self.context_menu:
            action = QtWidgets.QAction(name, self)
            if icon:
                action.setIcon(QtGui.QIcon(f":/{icon}"))
            action.triggered.connect(function)
            
            # Store position, span, and color with the action
            # Use a dictionary to store all properties for better extensibility
            properties = {
                'position': position,
                'rowSpan': rowSpan,
                'colSpan': colSpan,
                'color': color
            }
            
            self.menu_actions.append((action, properties))
            self.context_menu.rebuild_grid(self.menu_actions)

    def show_context_menu(self, pos):
        if self.context_menu:
            # Close any existing rename line edit
            if self.rename_line_edit and self.rename_line_edit.isVisible():
                self.rename_line_edit.deleteLater()
                self.rename_line_edit = None
                
            self.context_menu.rebuild_grid(self.menu_actions)
            self.context_menu.popup(self.mapToGlobal(pos))
                  
    #--------------------------------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if self.onlyContext:
            if event.button() in (QtCore.Qt.LeftButton, QtCore.Qt.RightButton):
                self.show_context_menu(event.pos())
                
        else:
            if event.button() == QtCore.Qt.LeftButton:
                self.click_count += 1
                if not self.timer.isActive():
                    self.timer.start(300)
            elif event.button() == QtCore.Qt.RightButton:
                self.rightClicked.emit(event.pos())
            super(CustomButton, self).mousePressEvent(event)
        UT.maya_main_window().activateWindow()
        
    def mouseReleaseEvent(self, event):
        if not self.onlyContext:
            if event.button() == QtCore.Qt.LeftButton:
                if self.click_count == 2:
                    self.timer.stop()
                    self.click_count = 0
                    self.doubleClicked.emit()
        super(CustomButton, self).mouseReleaseEvent(event)
        
    def performSingleClick(self):
        if not self.onlyContext:
            if self.click_count == 1:
                self.singleClicked.emit()
        self.click_count = 0

    def leaveEvent(self, event):
        self.reset_button_state()
        super(CustomButton, self).leaveEvent(event)
        
    def paintEvent(self, event):
        # First, let the QPushButton draw itself normally
        super(CustomButton, self).paintEvent(event)
        
        # If this button has a context menu, draw a small arrow indicator
        if self.has_context_menu:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set the arrow color to white with 50% opacity
            white_color = QColor('white')
            white_color.setAlphaF(0.4)  # 50% opacity
            painter.setPen(white_color)
            painter.setBrush(white_color)
            
            # Calculate the position for the arrow (bottom right corner)
            arrow_size = min(8, self.height() // 6)  # Size proportional to button height, max 8px
            margin = 2  # Margin from the edge
            
            # Create a triangle pointing down-right
            path = QPainterPath()
            x = self.width() - margin - arrow_size
            y = self.height() - margin - arrow_size
            
            # Arrow pointing to bottom right
            path.moveTo(x, y)
            path.lineTo(x + arrow_size, y)
            path.lineTo(x + arrow_size/2, y + arrow_size)
            path.lineTo(x, y)
            
            # Draw the arrow
            painter.drawPath(path)
        
    def reset_button_state(self):
        self.setStyleSheet(self.get_style_sheet(self.base_color, self.isFlat(), self.radius))
        self.update()

    def update_color(self, color):
        self.base_color = color
        self.setStyleSheet(self.get_style_sheet(color, self.isFlat(), self.radius))
        
    def update_text_color(self, color):
        """Update the text color of the button"""
        self.textColor = color
        self.setStyleSheet(self.get_style_sheet(self.base_color, self.isFlat(), self.radius))
        self.update()
        
    def update_text_size(self, size):
        """Update the font size of the button text"""
        self.textSize = size
        self.setStyleSheet(self.get_style_sheet(self.base_color, self.isFlat(), self.radius))
        self.update()

class CustomRadioButton(QtWidgets.QRadioButton):
    def __init__(self, text, color="#5285a6", fill=False, group=False, parent=None, border_radius=3, width=None, height=None):
        super(CustomRadioButton, self).__init__(text, parent)
        self.color = color
        self.fill = fill
        self.group_enabled = group
        self.group_name = None
        self.border_radius = border_radius
        self.custom_width = width
        self.custom_height = height
        
        # If not grouped, make it behave like a toggle button
        if not group:
            self.auto_exclusive = False
            self.setAutoExclusive(False)  # This is key - it prevents auto-grouping
        
        self.setStyleSheet(self._get_style())
        
        if width is not None or height is not None:
            self.setFixedSize(width or self.sizeHint().width(), height or self.sizeHint().height())

    def mousePressEvent(self, event):
        if not self.group_enabled:
            # Toggle the checked state when clicked
            self.setChecked(not self.isChecked())
        else:
            super().mousePressEvent(event)

    def _get_style(self):
        base_style = f"""
            QRadioButton {{
                background-color: {'transparent' if not self.fill else '#555555'};
                color: white;
                padding: 5px;
                border-radius: {self.border_radius}px;
            }}
        """
        
        if self.custom_width is not None:
            base_style += f"QRadioButton {{ min-width: {self.custom_width}px; max-width: {self.custom_width}px; }}"
        
        if self.custom_height is not None:
            base_style += f"QRadioButton {{ min-height: {self.custom_height}px; max-height: {self.custom_height}px; }}"

        if self.fill:
            return base_style + f"""
                QRadioButton::indicator {{
                    width: 0px;
                    height: 0px;
                }}
                QRadioButton:checked {{
                    background-color: {self.color};
                }}
                QRadioButton:hover {{
                    background-color: #6a6a6a;
                }}
                QRadioButton:checked:hover {{
                    background-color: {self._lighten_color(self.color, 1.2)};
                }}
            """
        else:
            return base_style + f"""
                QRadioButton::indicator {{
                    width: 13px;
                    height: 13px;
                }}
                QRadioButton::indicator:unchecked {{
                    background-color: #555555;
                    border: 0px solid #555555;
                    border-radius: {self.border_radius}px;
                }}
                QRadioButton::indicator:checked {{
                    background-color: {self.color};
                    border: 0px solid {self.color};
                    border-radius: 3px;
                }}
                QRadioButton::indicator:hover {{
                    background-color: #6a6a6a;
                }}
                QRadioButton::indicator:checked:hover {{
                    background-color: {self._lighten_color(self.color, 1.2)};
                }}
            """

    def _lighten_color(self, color, factor):
        c = QtGui.QColor(color)
        h, s, l, _ = c.getHslF()
        return QtGui.QColor.fromHslF(h, s, min(1.0, l * factor), 1.0).name()

    def group(self, group_name):
        if self.group_enabled:
            self.group_name = group_name
            if not hasattr(CustomRadioButton, 'groups'):
                CustomRadioButton.groups = {}
            if group_name not in CustomRadioButton.groups:
                CustomRadioButton.groups[group_name] = QtWidgets.QButtonGroup()
            CustomRadioButton.groups[group_name].addButton(self)
            self.setAutoExclusive(True)  # Enable auto-exclusive for grouped buttons

class CustomToolTip(QtWidgets.QWidget):
    def __init__(self, parent=None, color='#444444'):
        super().__init__(parent, QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.color = color
        self.text = ""
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        path = QtGui.QPainterPath()
        rect = QtCore.QRect(0, 0, self.width(), self.height())
        path.addRoundedRect(rect, 4, 4)
        
        painter.fillPath(path, QtGui.QColor(self.color))
        painter.setPen(QtGui.QColor(255, 255, 255))  # White border
        painter.drawPath(path)

        # Draw text
        painter.setPen(QtGui.QColor(255, 255, 255))  # White text
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.text)

    def show_tooltip(self, parent, text, pos):
        self.text = text
        self.adjustSize()
        global_pos = parent.mapToGlobal(pos)
        self.move(global_pos + QtCore.QPoint(10, 10))
        self.show()

    def hideEvent(self, event):
        self.text = ""
        super().hideEvent(event)

    def sizeHint(self):
        fm = self.fontMetrics()
        width = fm.horizontalAdvance(self.text) + 20
        height = fm.height() + 10
        return QtCore.QSize(width, height)

class CustomToggleButton(QtWidgets.QPushButton):
    """
    A custom toggle button that can be grouped with other toggle buttons.
    Buttons in the same group will behave like radio buttons (only one active at a time).
    Different groups operate independently.
    Colors can be customized for each button individually.
    """
    toggled_with_id = QtCore.Signal(bool, int)  # Custom signal
    
    # Class variable to keep track of different button groups
    button_groups = {}
    
    def __init__(self, text, button_id, group_id=None, checked_color='#5285A6', hover_color='rgba(20, 20, 20, .3)', 
                 unchecked_color='rgba(40, 40, 40, .3)', tooltip='', border_radius=10, width=20, height=20, parent=None):
        """
        Initialize a toggle button.
        
        Args:
            text: Button text
            button_id: Unique identifier for the button
            group_id: Group identifier (buttons with the same group_id behave like radio buttons)
            checked_color: Background color when button is checked
            hover_color: Background color when button is hovered
            unchecked_color: Background color when button is unchecked
            tooltip: Tooltip text
            border_radius: Border radius for styling
            width: Width of the button (default: 20)
            height: Height of the button (default: 20)
            parent: Parent widget
        """
        super(CustomToggleButton, self).__init__(text, parent)
        self.button_id = button_id
        self.group_id = group_id
        self.button_width = width
        self.button_height = height
        self.checked_color = checked_color
        self.hover_color = hover_color
        self.unchecked_color = unchecked_color
        self.border_radius = border_radius
        self.cmHeight = 22  # Default menu height for context menu items
        self.cmColor = '#444444'  # Default menu color
        
        # Store button in group if specified
        if group_id is not None:
            if group_id not in CustomToggleButton.button_groups:
                CustomToggleButton.button_groups[group_id] = []
            CustomToggleButton.button_groups[group_id].append(self)
            
        # Connect to destroyed signal to clean up references when button is deleted
        self.destroyed.connect(self._on_destroyed)
        
        self.setCheckable(True)
        self.setFixedSize(width, height)
        self.toggled.connect(self.on_toggle)
        self.setText(text)
        
        # Calculate font size based on button height (approximately 60% of height)
        font_size = int(self.button_height * 0.6)  # Round down to ensure integer font size
        
        self.setStyleSheet(f'''
            QPushButton {{
                background-color: {self.unchecked_color};
                border: none;
                color: rgba(250, 250, 250, .6);
                padding: 0px;
                text-align: center;
                border-radius: {border_radius};
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                background-color: {self.hover_color};
            }}
            QPushButton:checked {{
                background-color: {self.checked_color};
                color: white;
            }}
            QToolTip {{
                background-color: {self.checked_color};
                color: white;
                border: 0px;
            }}
        ''')
        self.setToolTip(f"<html><body><p>{tooltip}</p></body></html>")
        
        # Add context menu for tab operations
        self.context_menu = None
        self.setup_context_menu()
        
    def on_toggle(self, checked):
        """
        Handle toggle event. If button is part of a group and is being checked,
        uncheck all other buttons in the group.
        """
        if checked and self.group_id is not None and self.group_id in CustomToggleButton.button_groups:
            # Create a copy of the button group to avoid modification during iteration
            button_group = list(CustomToggleButton.button_groups[self.group_id])
            
            # Uncheck all other buttons in the group
            for button in button_group:
                try:
                    # Check if button still exists and is not self
                    if button is not self and button.isChecked():
                        button.blockSignals(True)
                        button.setChecked(False)
                        button.blockSignals(False)
                except RuntimeError:
                    # Button has been deleted, remove it from the group
                    if self.group_id in CustomToggleButton.button_groups and button in CustomToggleButton.button_groups[self.group_id]:
                        CustomToggleButton.button_groups[self.group_id].remove(button)
        
        # Emit the toggled signal with the button ID
        self.toggled_with_id.emit(checked, self.button_id)
                    
    def update_colors(self, checked_color=None, hover_color=None, unchecked_color=None):
        """
        Update the button colors without recreating the button.
        
        Args:
            checked_color: New background color when button is checked
            hover_color: New background color when button is hovered
            unchecked_color: New background color when button is unchecked
        """
        if checked_color is not None:
            self.checked_color = checked_color
        if hover_color is not None:
            self.hover_color = hover_color
        if unchecked_color is not None:
            self.unchecked_color = unchecked_color
            
        # Update the stylesheet with the new colors
        font_size = int(self.button_height * 0.6)
        self.setStyleSheet(f'''
            QPushButton {{
                background-color: {self.unchecked_color};
                border: none;
                color: rgba(250, 250, 250, .6);
                padding: 0px;
                text-align: center;
                border-radius: {self.border_radius};
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                background-color: {self.hover_color};
            }}
            QPushButton:checked {{
                background-color: {self.checked_color};
                color: white;
            }}
            QToolTip {{
                background-color: {self.checked_color};
                color: white;
                border: 0px;
            }}
        ''')

    def _on_destroyed(self):
        """Clean up references when button is destroyed"""
        # Remove self from button group
        if self.group_id is not None and self.group_id in CustomToggleButton.button_groups:
            if self in CustomToggleButton.button_groups[self.group_id]:
                CustomToggleButton.button_groups[self.group_id].remove(self)
                
            # If group is empty, remove it
            if not CustomToggleButton.button_groups[self.group_id]:
                del CustomToggleButton.button_groups[self.group_id]

    def setup_context_menu(self):
        """Setup the context menu for the toggle button"""
        self.context_menu = TwoColumnMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.menu_actions = []  # Store menu actions like CustomButton does
        
        # Only add delete option for custom tabs (IDs > 2)
        if self.button_id > 2:
            # Add label
            self.addMenuLabel('Tab Options', position=(0, 0), colSpan=2)
            
            # Add delete action
            self.addToMenu('Delete Tab', self.delete_tab, position=(1, 0), colSpan=2, color='#ff5555')
    
    def addMenuLabel(self, text, position=None, rowSpan=1, colSpan=1):
        """
        Add a label to the context menu.
        Args:
            text (str): Text to display in the menu
            position (tuple, optional): (row, column) position in the grid
            rowSpan (int, optional): Number of rows the label spans
            colSpan (int, optional): Number of columns the label spans
        """
        if self.context_menu:
            # Use 'label' as a special identifier for text labels
            properties = {
                'position': position,
                'rowSpan': rowSpan,
                'colSpan': colSpan
            }
            self.menu_actions.append(('label', text, properties))
            self.context_menu.rebuild_grid(self.menu_actions)

    def addToMenu(self, name, function, icon=None, position=None, rowSpan=1, colSpan=1, color=None):
        """
        Add an item to the context menu.
        Args:
            name (str): Text to display in the menu
            function: Callback function when item is clicked
            icon (str, optional): Icon path/resource
            position (tuple, optional): (row, column) position in the grid
            rowSpan (int, optional): Number of rows the item spans
            colSpan (int, optional): Number of columns the item spans
            color (str, optional): Custom color for the menu button (hex format, e.g. '#ff0000')
        """
        if self.context_menu:
            action = QtWidgets.QAction(name, self)
            if icon:
                action.setIcon(QtGui.QIcon(f":/{icon}"))
            action.triggered.connect(function)
            
            # Store position, span, and color with the action
            # Use a dictionary to store all properties for better extensibility
            properties = {
                'position': position,
                'rowSpan': rowSpan,
                'colSpan': colSpan,
                'color': color
            }
            
            self.menu_actions.append((action, properties))
            self.context_menu.rebuild_grid(self.menu_actions)
            
    def show_context_menu(self, pos):
        """Show the context menu with options based on button ID"""
        if self.context_menu and self.button_id > 2:
            # Show the menu at the cursor position
            global_pos = self.mapToGlobal(pos)
            self.context_menu.popup(global_pos)
    
    def delete_tab(self):
        """Delete this tab if it's a custom tab (ID > 2)"""
        if self.button_id > 2:
            # Find the parent window to call the remove method
            parent = self.parent()
            while parent and not hasattr(parent, 'remove_toggle_button_by_id'):
                parent = parent.parent()
                
            if parent and hasattr(parent, 'remove_toggle_button_by_id'):
                parent.remove_toggle_button_by_id(self.button_id)
    
    # Event Filter: Basic mouse press event handling
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            UT.maya_main_window().activateWindow()
            super(CustomToggleButton, self).mousePressEvent(event)
        elif event.button() == QtCore.Qt.RightButton:
            # Right-click is handled by the customContextMenuRequested signal
            pass

class ColorPickerMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super(ColorPickerMenu, self).__init__(parent)
        self.use_index = True  # Track index/RGB mode
        self.use_override = True  # Track override/outline mode
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet('''
            QMenu {
                background-color: rgba(30, 30, 30, .9);
                border: 1px solid #444444;
                border-radius: 3px;
                padding: 5px 7px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 3px 15px 3px 3px; ;
                margin: 3px 0px  ;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #2c4759;
            }''')
        
        
        self.setup_ui()
        
    def setup_ui(self):
        main_widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QGridLayout(main_widget)
        cm = 2
        self.layout.setContentsMargins(cm, cm, cm, cm)
        self.layout.setSpacing(4)
        
        # Create buttons container
        buttons_widget = QtWidgets.QWidget()
        buttons_layout = QtWidgets.QGridLayout(buttons_widget)
        buttons_layout.setContentsMargins(cm, cm, cm, cm)
        buttons_layout.setSpacing(4)
        
        
        # Create color buttons
        for i in range(30):
            row = i // 10
            col = i % 10
            
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(20, 20)
            
            color = self.get_maya_color_rgb(i + 1)
            
            btn.setStyleSheet(
                f"QPushButton {{ background-color: rgb({color[0]}, {color[1]}, {color[2]}); "
                f"border: 0px solid #555555; }}"
                f"QPushButton:hover {{ border: 1px solid #444444; }}"
            )
            #print(color[0], color[1], color[2])
            btn.clicked.connect(lambda *args, index=i+1: self.apply_color(index))
            buttons_layout.addWidget(btn, row, col)
        
        # Create mode toggle and disable overrides buttons
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_widget)
        control_layout.setContentsMargins(cm, cm, cm, cm)
        control_layout.setSpacing(4)
        
        # Add color type toggle (Override/Outline)
        color_type_btn = QtWidgets.QPushButton("Override")
        color_type_btn.setFixedHeight(20)
        color_type_btn.setStyleSheet('''
                               QPushButton{background-color: #444444; color: white; border-radius: 3px;}
                               QPushButton:hover{background-color: #555555;
                               }''')
        color_type_btn.clicked.connect(self.toggle_color_type)
        control_layout.addWidget(color_type_btn)
        
        # Add color mode toggle (Index/RGB)
        mode_btn = QtWidgets.QPushButton("Index")
        mode_btn.setFixedHeight(20)
        mode_btn.setStyleSheet('''
                               QPushButton{background-color: #444444; color: white; border-radius: 3px;}
                               QPushButton:hover{background-color: #555555;
                               }''')
        mode_btn.clicked.connect(self.toggle_mode)
        control_layout.addWidget(mode_btn)
        
        disable_btn = QtWidgets.QPushButton("Disable")
        disable_btn.setFixedHeight(20)
        disable_btn.setStyleSheet('''
                               QPushButton{background-color: #444444; color: white; border-radius: 3px;}
                               QPushButton:hover{background-color: #555555;
                               }''')
        disable_btn.clicked.connect(self.disable_overrides)
        control_layout.addWidget(disable_btn)
        
        # Add widgets to main layout
        self.layout.addWidget(buttons_widget, 0, 0)
        self.layout.addWidget(control_widget, 1, 0)
        
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(main_widget)
        self.addAction(action)
        
    def get_maya_color_rgb(self, index):
        color = cmds.colorIndex(index, q=True)
        return [int(c * 255) for c in color]
    
    def apply_color(self, color_index):
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Nothing selected. Please select objects to apply color.")
            return
            
        for obj in selection:
            if self.use_override:
                # Apply override color
                cmds.setAttr(f"{obj}.overrideEnabled", 1)
                if self.use_index:
                    # Switch to index mode
                    rgb = self.get_maya_color_rgb(color_index)
                    cmds.setAttr(f"{obj}.overrideRGBColors", 0)
                    cmds.setAttr(f"{obj}.overrideColor", color_index)
                else:
                    # Switch to RGB mode
                    rgb = self.get_maya_color_rgb(color_index)
                    cmds.setAttr(f"{obj}.overrideRGBColors", 1)
                    cmds.setAttr(f"{obj}.overrideColorRGB", rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
            else:
                # Apply outline color
                if self.use_index:
                    # Switch to index mode - convert index to RGB first
                    rgb = self.get_maya_color_rgb(color_index)
                    cmds.setAttr(f"{obj}.useOutlinerColor", 1)
                    cmds.setAttr(f"{obj}.outlinerColorR", rgb[0]/255.0)
                    cmds.setAttr(f"{obj}.outlinerColorG", rgb[1]/255.0)
                    cmds.setAttr(f"{obj}.outlinerColorB", rgb[2]/255.0)
                else:
                    # Switch to RGB mode
                    rgb = self.get_maya_color_rgb(color_index)
                    cmds.setAttr(f"{obj}.useOutlinerColor", 1)
                    cmds.setAttr(f"{obj}.outlinerColorR", rgb[0]/255.0)
                    cmds.setAttr(f"{obj}.outlinerColorG", rgb[1]/255.0)
                    cmds.setAttr(f"{obj}.outlinerColorB", rgb[2]/255.0)
        
        self.close()
    
    def toggle_mode(self):
        self.use_index = not self.use_index
        sender = self.sender()
        sender.setText("Index" if self.use_index else "RGB")
    
    def toggle_color_type(self):
        self.use_override = not self.use_override
        sender = self.sender()
        sender.setText("Override" if self.use_override else "Outline")
    
    def disable_overrides(self):
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("Nothing selected. Please select objects to disable color settings.")
            return
            
        for obj in selection:
            if self.use_override:
                cmds.setAttr(f"{obj}.overrideEnabled", 0)
            else:
                cmds.setAttr(f"{obj}.useOutlinerColor", 0)
        self.close()

class ColorPickerButton(CustomButton):
    def __init__(self, parent=None):
        super(ColorPickerButton, self).__init__(
            text='Color Override',
            color='#222222',
            tooltip='Override Color: Overrides the color of the selected object(s).',
            ContextMenu=True,
        )
        self.color_menu = ColorPickerMenu(self)
        #self.singleClicked.connect(self.show_color_menu)

    def show_color_menu(self):
        pos = self.mapToGlobal(QtCore.QPoint(0, self.height()))
        self.color_menu.popup(pos)

    def show_context_menu(self, event):
        self.show_color_menu()

    def mousePressEvent(self, event):       
        self.show_color_menu()
        UT.maya_main_window().activateWindow()

class CustomFunctionButton(CustomButton):
    """A custom button that can be added to the custom toggle button widget layout.
    This button has a context menu with options for Script Manager, Rename, Color, and Delete.
    When clicked, it runs the associated script.
    """
    # Signal emitted when script manager is requested, passing the button ID
    script_manager_requested = QtCore.Signal(int)
    # Signal emitted when button is deleted, passing the button ID
    delete_requested = QtCore.Signal(int)
    # Signal emitted when button is renamed, passing the button ID and new name
    renamed = QtCore.Signal(int, str)
    # Signal emitted when button color is changed, passing the button ID and new color
    color_changed = QtCore.Signal(int, str)
    
    def __init__(self, text='Function', button_id=None, script='', color='#5285A6', parent=None, width=None, height=24, 
                 script_type='python', cmColor="#444444",cmHeight=24):
        # Ensure text is properly formatted
        display_text = text.strip() if text else 'Function'
        
        # Check if the script contains a tooltip directive
        tooltip_text = f'Function Button: {display_text}'
        if script:
            import re
            tooltip_match = re.search(r'^\s*@TF\.tool_tip\s*\(\s*[\"\'](.*?)[\"\'](\s*)?\)', script, flags=re.MULTILINE)
            if tooltip_match:
                tooltip_text = tooltip_match.group(1)
        
        super(CustomFunctionButton, self).__init__(
            text=display_text,
            color=color,
            tooltip=tooltip_text,
            ContextMenu=True,
            width=width,
            height=height,
            parent=parent,
            cmColor=cmColor,
            cmHeight=cmHeight
        )
        
        self.button_id = button_id  # Unique identifier for the button
        self.script = script  # Script to run when button is clicked
        self.rename_line_edit = None  # Will hold the QLineEdit for inline renaming
        
        # Validate script_type
        if script_type.lower() not in ['python', 'mel']:
            cmds.warning(f"Invalid script type: {script_type}. Using 'python' instead.")
            self.script_type = 'python'
        else:
            self.script_type = script_type.lower()
        
        # Connect click signal to run script
        self.clicked.connect(self.run_script)
        
        # Setup context menu
        self.setup_context_menu()
    
    def setup_context_menu(self):
        # Add items to the context menu
        self.addMenuLabel('Function Button',position=(0,0),colSpan=2) 
        self.addToMenu('Script Manager', lambda: self._execute_and_close_menu(self.open_script_manager), position=(1,0),colSpan=2)
        self.addToMenu('Rename', lambda: self._execute_and_close_menu(self.rename_button), position=(2,0))
        self.addToMenu('Color', lambda: self._execute_and_close_menu(self.change_color), position=(2,1))
        self.addToMenu('Delete', lambda: self._execute_and_close_menu(self.delete_button), position=(3,0),colSpan=2)
        
    def _execute_and_close_menu(self, func):
        """Execute a function and ensure the context menu is closed"""
        # Close the menu first
        if self.context_menu and self.context_menu.isVisible():
            self.context_menu.hide()
        # Use a short timer to allow the menu to close before executing the function
        QTimer.singleShot(10, func)
    
    def run_script(self):       
        """Run the associated script when the button is clicked"""
        import re
        if not self.script:
            return
        
        code = self.script
        if code:
            try:
                # Remove any tooltip directives from the code before execution
                code = re.sub(r'^\s*@TF\.tool_tip\s*\(\s*[\"\'](.*?)[\"\'](\s*)?\)', '', code, flags=re.MULTILINE)
                
                # Handle @TF.function_name(arguments) syntax with indentation preservation
                modified_code = re.sub(
                    r'^(\s*)@TF\.(\w+)\s*\((.*?)\)',
                    r'\1import ft_tool_box.tool_functions as TF\n\1TF.\2(\3)',
                    code,
                    flags=re.MULTILINE  # Enable multiline mode to match at the start of each line
                )
                # Execute the modified code
                if self.script_type == 'python':
                    print(modified_code)
                    exec(modified_code)
                else:
                    import maya.mel as mel
                    mel.eval(modified_code)
            except Exception as e:
                cmds.warning(f"Error executing {self.script_type} code: {str(e)}")
        
    
    def open_script_manager(self):
        """Open the script manager dialog to edit the button's script"""
        # Emit signal to request script manager with this button's ID
        if self.button_id is not None:
            self.script_manager_requested.emit(self.button_id)
        else:
            cmds.warning("Cannot open script manager: button ID is not set")
    
    def rename_button(self):
        """Show an inline QLineEdit to rename the button"""
        # First, ensure the context menu is closed
        if self.context_menu and self.context_menu.isVisible():
            self.context_menu.hide()
        
        # Set active window to ToolBox Window
        from . import utils as UT

        UT.tool_box_window().activateWindow()
        # Import the custom line edit class
        from . import custom_line_edit
        
        # Create a FocusLosingLineEdit on top of the button
        line_edit = custom_line_edit.FocusLosingLineEdit(self)
        self.rename_line_edit = line_edit  # Store reference to prevent garbage collection
        line_edit.setText(self.text())
        line_edit.setStyleSheet(f'''
            QLineEdit {{
                background-color: {UT.rgba_value(self.base_color, .8)};
                color: {self.textColor};
                border: 1px solid #5285a6;
                border-radius: {self.radius}px;
                padding: 2px 5px;
                font-size: {self.textSize}px;
            }}
        ''')
        line_edit.setGeometry(self.rect())
        line_edit.setAlignment(QtCore.Qt.AlignCenter)
        
        # Handle escape key for cancellation
        def key_press_event(event):
            if event.key() == QtCore.Qt.Key_Escape:
                self.rename_line_edit = None
                line_edit.deleteLater()
                UT.maya_main_window().activateWindow()
            else:
                # Call the original keyPressEvent
                custom_line_edit.FocusLosingLineEdit.keyPressEvent(line_edit, event)
        line_edit.keyPressEvent = key_press_event
        
        # Connect focus out event to apply the name
        def apply_name():
            new_name = line_edit.text().strip()
            if new_name:
                self.setText(new_name)
                self.setToolTip(f'<html><body><p style=\'color:white; white-space:nowrap; \'>Function Button: {new_name}</p></body></html>')
                
                # Update the button width to fit the new text
                if self.width() is not None:
                    new_width = self.calculate_button_width(new_name)
                    # Only update if the new width is different to avoid unnecessary resizing
                    if new_width != self.width():
                        self.setMinimumWidth(new_width)
                        # If parent has a layout, ask it to update
                        if self.parent() and self.parent().layout():
                            self.parent().layout().update()
                
                # Emit signal to update the database
                if self.button_id is not None:
                    self.renamed.emit(self.button_id, new_name)
            self.rename_line_edit = None
            line_edit.deleteLater()
            
            UT.maya_main_window().activateWindow()
        line_edit.editingFinished.connect(apply_name)
        
        # Set initial focus
        line_edit.show()
        line_edit.setFocus()
        line_edit.selectAll()
        
    def create_color_change_function(self, color):
        """Create a function that changes the button's color"""
        def change_to_color():
            # Set the base color property and update stylesheet
            self.base_color = color
            self.setStyleSheet(self.get_style_sheet(color, False, self.radius))
            
            # Emit signal to update the database
            if self.button_id is not None:
                self.color_changed.emit(self.button_id, color)
        return change_to_color
            
    def change_color(self):
        """Open a color palette menu to change the button's color"""
        from . import utils as UT
        
        # Create a context menu for color selection
        menu = QtWidgets.QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 5px 20px 5px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        """)
        
        # Add color selection submenu
        color_widget = QtWidgets.QWidget()
        color_layout = QtWidgets.QGridLayout(color_widget)
        color_layout.setSpacing(5)
        color_layout.setContentsMargins(3, 5, 3, 5)
        
        color_palette = [
            "#000000", "#3F3F3F", "#999999", "#9B0028", "#00045F",  
            "#0000FF", "#004618", "#250043", "#C700C7", "#894733",  
            "#3E221F", "#992500", "#FF0000", "#00FF00", "#004199",  
            "#FFFFFF", "#FFFF00", "#63DCFF", "#43FFA2", "#FFAFAF",  
            "#E3AC79", "#FFFF62", "#009953", "#D9916C", "#DFC74D",  
            "#A1CE46", "#3AC093", "#40D1B8", "#399DCD", "#9B6BCD"  
        ]

        for i, color in enumerate(color_palette):
            color_button = QtWidgets.QPushButton()
            color_button.setFixedSize(20, 20)
            color_button.setStyleSheet(f'''QPushButton {{background-color: {color}; border: none; border-radius: 3px;}} 
                                        QPushButton:hover {{background-color: {UT.rgba_value(color, 1.2)};}}''')
            color_button.clicked.connect(self.create_color_change_function(color))
            color_layout.addWidget(color_button, i // 5, i % 5)

        color_action = QtWidgets.QWidgetAction(menu)
        color_action.setDefaultWidget(color_widget)
        menu.addAction(color_action)
        
        # Show the menu at cursor position
        menu.exec_(QtGui.QCursor.pos())
    
    def delete_button(self):
        """Delete this button"""
        # Ask for confirmation
        from . import custom_dialog as CD
        '''
        dialog = CD.CustomDialog(parent=self.parent(),title='Delete Function Button',)

        delete_message = QtWidgets.QLabel(f'Are you sure you want to delete the "{self.text()}" button?')
        delete_message.setWordWrap(True)
        dialog.add_widget(delete_message)
        dialog.add_button_box()
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            '''
        # Emit signal to notify parent that this button is being deleted
        if self.button_id is not None:
            self.delete_requested.emit(self.button_id)
        else:
            cmds.warning("Button deleted without ID notification")
        
        # Remove from parent layout
        parent_widget = self.parent()
        if parent_widget and parent_widget.layout():
            parent_widget.layout().removeWidget(self)
            # Ensure the layout updates properly
            parent_widget.layout().update()
        
        # Delete the button
        self.setParent(None)  # Detach from parent before deletion
        self.deleteLater()

    def set_script(self, script, script_type='python'):
        """Set the script and script type for this button
        
        Args:
            script (str): The script code to be executed when the button is clicked
            script_type (str): The script language type ('python' or 'mel')
        """
        self.script = script
        # Validate script_type
        if script_type.lower() not in ['python', 'mel']:
            cmds.warning(f"Invalid script type: {script_type}. Using 'python' instead.")
            self.script_type = 'python'
        else:
            self.script_type = script_type.lower()
