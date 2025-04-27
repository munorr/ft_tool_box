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

class TwoColumnMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_widget = QtWidgets.QWidget(self)
        self.grid_layout = QtWidgets.QGridLayout(self.grid_widget)
        gls = 6 # grid layout spacing
        self.grid_layout.setSpacing(gls)
        self.grid_layout.setContentsMargins(gls, gls, gls, gls)

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
                    background-color: rgba(10, 10, 10, .8);
                    border: 1px solid #444444;
                    border-radius: 3px;
                    padding:  4px 5px;
                }}''')

    def rebuild_grid(self, actions):
        # Clear existing items
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # Separate positioned and unpositioned items
        positioned = []
        unpositioned = []
        max_row = max_col = -1
        
        for item in actions:
            if len(item) == 4:  # Item with position, rowSpan, and colSpan
                action, position, rowSpan, colSpan = item
            else:  # Unpositioned item
                action = item
                position = None
                rowSpan = 1
                colSpan = 1
                
            if position is not None:
                positioned.append((action, position, rowSpan, colSpan))
                max_row = max(max_row, position[0] + rowSpan - 1)
                max_col = max(max_col, position[1] + colSpan - 1)
            else:
                unpositioned.append((action, rowSpan, colSpan))
        
        # Place positioned items first
        for action, pos, rowSpan, colSpan in positioned:
            button = self._create_menu_button(action)
            self.grid_layout.addWidget(button, pos[0], pos[1], rowSpan, colSpan)
        
        # Find available positions for unpositioned items
        if unpositioned:
            next_row = 0 if max_row == -1 else max_row + 1
            next_col = 0
            
            for action, rowSpan, colSpan in unpositioned:
                button = self._create_menu_button(action)
                # If this item would overflow the columns, move to next row
                if next_col + colSpan > 2:
                    next_col = 0
                    next_row += 1
                self.grid_layout.addWidget(button, next_row, next_col, rowSpan, colSpan)
                next_col += colSpan
                if next_col >= 2:
                    next_col = 0
                    next_row += rowSpan
        
        self.grid_widget.adjustSize()
        self.adjustSize()
        
    def _create_menu_button(self, action):
        button = QtWidgets.QPushButton(action.text())
        if action.icon():
            button.setIcon(action.icon())
        button.clicked.connect(action.triggered)
        
        button.setStyleSheet(f'''
            QPushButton {{
                background-color: {UT.rgba_value(self.parent().cmColor, 1)};
                color: white;
                border: none;
                padding: 3px 10px;
                border-radius: 3px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {UT.rgba_value(self.parent().cmColor, 1.2)};
            }}
        ''')
        button.setFixedHeight(self.parent().cmHeight)
        return button

class CustomButton(QtWidgets.QPushButton):
    singleClicked = QtCore.Signal()
    doubleClicked = QtCore.Signal()
    rightClicked = QtCore.Signal(QtCore.QPoint)

    def __init__(self, text='', icon=None, color='#4d4d4d', tooltip='', flat=False, size=None, width=None, height=None, parent=None, radius=3, ContextMenu=False, 
                 cmColor='#00749a', cmHeight = 20, onlyContext=False, alpha=1, textColor='white', text_size=12):
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

    def addMenuSeparator(self, position=None):
        """
        Add a separator line to the context menu.
        Args:
            position (tuple, optional): (row) position in the grid
        """
        if self.context_menu:
            self.menu_actions.append(('separator', position))
            self.context_menu.rebuild_grid(self.menu_actions)

    def addMenuLabel(self, text, position=None):
        """
        Add a label to the context menu.
        Args:
            text (str): Text to display in the menu
            position (tuple, optional): (row, column) position in the grid
        """
        if self.context_menu:
            self.menu_actions.append((text, position))
            self.context_menu.rebuild_grid(self.menu_actions)

    def addToMenu(self, name, function, icon=None, position=None, rowSpan=1, colSpan=1):
        """
        Add an item to the context menu.
        Args:
            name (str): Text to display in the menu
            function: Callback function when item is clicked
            icon (str, optional): Icon path/resource
            position (tuple, optional): (row, column) position in the grid
        """
        if self.context_menu:
            action = QtWidgets.QAction(name, self)
            if icon:
                action.setIcon(QtGui.QIcon(f":/{icon}"))
            action.triggered.connect(function)
            # Store position along with the action
            self.menu_actions.append((action, position, rowSpan, colSpan))
            self.context_menu.rebuild_grid(self.menu_actions)

    def show_context_menu(self, pos):
        if self.context_menu:
            self.reset_button_state()
            self.context_menu.exec_(self.mapToGlobal(pos))
                  
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
        
        # Store button in group if specified
        if group_id is not None:
            if group_id not in CustomToggleButton.button_groups:
                CustomToggleButton.button_groups[group_id] = []
            CustomToggleButton.button_groups[group_id].append(self)
        
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
        
    def on_toggle(self, checked):
        """
        Handle toggle event. If button is part of a group and is being checked,
        uncheck all other buttons in the group.
        """
        # Emit the signal with button id
        self.toggled_with_id.emit(checked, self.button_id)
        
        # If this button is in a group and is being checked on
        if self.group_id is not None and checked:
            # Uncheck all other buttons in the same group
            for button in CustomToggleButton.button_groups[self.group_id]:
                if button is not self and button.isChecked():
                    # Block signals temporarily to avoid recursion
                    button.blockSignals(True)
                    button.setChecked(False)
                    button.blockSignals(False)
                    # Still emit the signal for the unchecked button
                    button.toggled_with_id.emit(False, button.button_id)
                    
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
            
        # Get the current border radius and font size from the existing style
        current_style = self.styleSheet()
        border_radius = 10  # Default value
        font_size = int(self.button_height * 0.6)  # Default calculation
        
        # Try to extract the current border-radius from the style
        import re
        border_match = re.search(r'border-radius:\s*(\d+)px', current_style)
        if border_match:
            border_radius = border_match.group(1)
            
        # Update the style sheet with the new colors
        self.setStyleSheet(f'''
            QPushButton {{
                background-color: {self.unchecked_color};
                border: none;
                color: rgba(250, 250, 250, .6);
                padding: 0px;
                text-align: center;
                border-radius: {border_radius}px;
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
