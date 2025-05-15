# ===== Add this class before the ColorPickerMenu class =====

class SubMenu(TwoColumnMenu):
    def __init__(self, parent=None, title="Sub Menu", color="#444444", height=20):
        super(SubMenu, self).__init__(parent)
        self._title = title
        self.cmColor = color
        self.cmHeight = height
        self.menu_actions = []  # Store menu actions
        
    def title(self):
        return self._title
    
    def addToMenu(self, name, function, icon=None, position=None, rowSpan=1, colSpan=1, color=None):
        """
        Add an item to the sub-menu.
        Args:
            name (str): Text to display in the menu
            function: Callback function when item is clicked
            icon (str, optional): Icon path/resource
            position (tuple, optional): (row, column) position in the grid
            rowSpan (int, optional): Number of rows the item spans
            colSpan (int, optional): Number of columns the item spans
            color (str, optional): Custom color for the menu button (hex format, e.g. '#ff0000')
        """
        action = QtWidgets.QAction(name, self)
        if icon:
            action.setIcon(QtGui.QIcon(f":/{icon}"))
        action.triggered.connect(function)
        
        # Store position, span, and color with the action
        properties = {
            'position': position,
            'rowSpan': rowSpan,
            'colSpan': colSpan,
            'color': color
        }
        
        self.menu_actions.append((action, properties))
        self.rebuild_grid(self.menu_actions)
        
    def addMenuSeparator(self, position=None, rowSpan=1, colSpan=1):
        """
        Add a separator line to the sub-menu.
        Args:
            position (tuple, optional): (row) position in the grid
            rowSpan (int, optional): Number of rows the separator spans
            colSpan (int, optional): Number of columns the separator spans
        """
        properties = {
            'position': position,
            'rowSpan': rowSpan,
            'colSpan': colSpan
        }
        
        self.menu_actions.append(("separator", properties))
        self.rebuild_grid(self.menu_actions)
        
    def addMenuLabel(self, text, position=None, rowSpan=1, colSpan=1):
        """
        Add a label to the sub-menu.
        Args:
            text (str): Text to display in the menu
            position (tuple, optional): (row, column) position in the grid
            rowSpan (int, optional): Number of rows the label spans
            colSpan (int, optional): Number of columns the label spans
        """
        properties = {
            'position': position,
            'rowSpan': rowSpan,
            'colSpan': colSpan
        }
        
        self.menu_actions.append(("label", text, properties))
        self.rebuild_grid(self.menu_actions)
        
    def subMenu(self, text, position=None, rowSpan=1, colSpan=1, color=None):
        """
        Create a nested sub-menu that can be added to this sub-menu.
        
        Args:
            text (str): Text to display for the sub-menu
            position (tuple, optional): (row, column) position in the grid
            rowSpan (int, optional): Number of rows the sub-menu spans
            colSpan (int, optional): Number of columns the sub-menu spans
            color (str, optional): Custom color for the sub-menu button
            
        Returns:
            SubMenu: A sub-menu object that can have items added to it
        """
        # Create a sub-menu with the same styling as this menu
        nested_sub_menu = SubMenu(self, text, color or self.cmColor, self.cmHeight)
        
        return nested_sub_menu


# ===== Add this method to the CustomButton class after addMenuLabel method =====

def subMenu(self, text, position=None, rowSpan=1, colSpan=1, color=None):
    """
    Create a sub-menu that can be added to the context menu.
    
    Args:
        text (str): Text to display for the sub-menu
        position (tuple, optional): (row, column) position in the grid
        rowSpan (int, optional): Number of rows the sub-menu spans
        colSpan (int, optional): Number of columns the sub-menu spans
        color (str, optional): Custom color for the sub-menu button
        
    Returns:
        SubMenu: A sub-menu object that can have items added to it
    """
    if self.context_menu:
        # Create a sub-menu with the same styling as the parent menu
        sub_menu = SubMenu(self, text, color or self.cmColor, self.cmHeight)
        
        return sub_menu
    
    return None


# ===== Update the addToMenu method in the CustomButton class =====

def addToMenu(self, name, function=None, icon=None, position=None, rowSpan=1, colSpan=1, color=None):
    """
    Add an item to the context menu.
    Args:
        name (str or SubMenu): Text to display in the menu or a SubMenu object
        function: Callback function when item is clicked (not used for SubMenu)
        icon (str, optional): Icon path/resource
        position (tuple, optional): (row, column) position in the grid
        rowSpan (int, optional): Number of rows the item spans
        colSpan (int, optional): Number of columns the item spans
        color (str, optional): Custom color for the menu button (hex format, e.g. '#ff0000')
    """
    if self.context_menu:
        # Handle SubMenu objects
        if isinstance(name, SubMenu):
            sub_menu = name
            
            # Store position, span, and color with the sub-menu
            properties = {
                'position': position,
                'rowSpan': rowSpan,
                'colSpan': colSpan,
                'color': color or self.cmColor,
                'sub_menu': sub_menu  # Store reference to the sub-menu
            }
            
            self.menu_actions.append((sub_menu, properties))
        else:
            # Regular menu item
            action = QtWidgets.QAction(name, self)
            if icon:
                action.setIcon(QtGui.QIcon(f":/{icon}"))
            if function:
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


# ===== Update the _create_menu_button method in the TwoColumnMenu class =====

def _create_menu_button(self, action):
    # Extract text, function and color from the action
    text = ''
    func = None
    button_color = None
    is_submenu = False
    sub_menu = None
    
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
        
        # Check if this is a sub-menu
        if 'sub_menu' in properties and properties['sub_menu']:
            is_submenu = True
            sub_menu = properties['sub_menu']
            text = sub_menu.title()
            
            def show_submenu():
                # Position the sub-menu relative to the parent menu
                parent_pos = self.pos()
                sub_menu.popup(QtCore.QPoint(parent_pos.x() + self.width(), parent_pos.y()))
                
            func = show_submenu
        
        # Handle different action types
        elif isinstance(button_action, QtWidgets.QAction):
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
        # Add a right arrow indicator if this is a submenu
        arrow_style = ""
        if is_submenu:
            arrow_style = "QPushButton::menu-indicator { image: url(none); subcontrol-position: right; subcontrol-origin: padding; width: 10px; }"
            text += " ►"  # Add a small triangle to indicate submenu
            button.setText(text)
            
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
            {arrow_style}
        ''')
    button.setFixedHeight(self.parent().cmHeight)
    return button
