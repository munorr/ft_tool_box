import json
import maya.cmds as cmds

class ToggleButtonDatabase:
    def __init__(self):
        self.tool_box_data = {}
        self.data_attribute_name = 'ftToolBoxData'
        # For backward compatibility
        self.toggle_attribute_name = 'toolBoxToggleButtons'
        self.function_attribute_name = 'toolBoxFunctionButtons'
        # Define default tabs that will not be stored in the database
        self.default_tabs = [
            {
                "id": 0,
                "text": "1",
                "tooltip": "Modeling Tools",
                "checked_color": "#5285A6",
                "unchecked_color": "rgba(40, 40, 40, .3)",
                "hover_color": "rgba(20, 20, 20, .3)",
                "widget_name": "modeling_scroll_area",
                "border_radius": 6,
                "buttons": []
            },
            {
                "id": 1,
                "text": "2",
                "tooltip": "Animation Tools",
                "checked_color": "#5285A6",
                "unchecked_color": "rgba(40, 40, 40, .3)",
                "hover_color": "rgba(20, 20, 20, .3)",
                "widget_name": "animation_scroll_area",
                "border_radius": 6,
                "buttons": []
            },
            {
                "id": 2,
                "text": "3",
                "tooltip": "Graph Editor Tools",
                "checked_color": "#5285A6",
                "unchecked_color": "rgba(40, 40, 40, .3)",
                "hover_color": "rgba(20, 20, 20, .3)",
                "widget_name": "graph_scroll_area",
                "border_radius": 6,
                "buttons": []
            }
        ]
        
        # Initialize the tool box data structure with default tabs
        self.tool_box_data = {
            "tabs": list(self.default_tabs)  # Create a copy to avoid modifying the original
        }
        
        self.load_database()
    
    def load_database(self):
        """Load the tool box data from Maya's defaultObjectSet"""
        # First try to load the consolidated data structure
        if self._load_consolidated_data_from_maya():
            # Successfully loaded consolidated data
            return
            
        # If consolidated data doesn't exist, try to load from legacy format
        # and convert to the new format
        self._load_legacy_data_and_convert()
    

    
    def save_database(self):
        """Save the tool box data to Maya's defaultObjectSet"""
        # Save the consolidated data structure
        self._save_consolidated_data_to_maya()
    
    def _save_consolidated_data_to_maya(self):
        """Save the consolidated tool box data to Maya's defaultObjectSet"""
        try:
            # Create a copy of the data to avoid modifying the original
            data_to_save = {"tabs": []}
            
            # Only save custom tabs (IDs > 2)
            for tab in self.tool_box_data["tabs"]:
                if tab["id"] > 2:
                    data_to_save["tabs"].append(tab)
            
            # Convert to JSON string
            data_json = json.dumps(data_to_save)
            
            # Check if defaultObjectSet exists
            if not cmds.objExists('defaultObjectSet'):
                return False
                
            # Check if the attribute exists, create it if it doesn't
            if not cmds.attributeQuery(self.data_attribute_name, node='defaultObjectSet', exists=True):
                cmds.addAttr('defaultObjectSet', longName=self.data_attribute_name, dataType='string')
            
            # Set the attribute value
            cmds.setAttr(f'defaultObjectSet.{self.data_attribute_name}', data_json, type='string')
            return True
        except Exception as e:
            print(f"Error saving tool box data to Maya: {e}")
            return False
    
    def _load_consolidated_data_from_maya(self):
        """Load the consolidated tool box data from Maya's defaultObjectSet"""
        try:
            # Check if defaultObjectSet exists
            if not cmds.objExists('defaultObjectSet'):
                return False
                
            # Check if the attribute exists
            if not cmds.attributeQuery(self.data_attribute_name, node='defaultObjectSet', exists=True):
                return False
            
            # Get the attribute value
            data_json = cmds.getAttr(f'defaultObjectSet.{self.data_attribute_name}')
            
            # Check if the JSON string is empty or invalid
            if not data_json or data_json.strip() == '':
                return False
                
            # Convert the JSON string to a Python object
            loaded_data = json.loads(data_json)
            
            # Validate the loaded data
            if not isinstance(loaded_data, dict) or "tabs" not in loaded_data:
                print("Invalid tool box data format in Maya")
                return False
            
            # Start with default tabs
            self.tool_box_data = {"tabs": list(self.default_tabs)}
            
            # Add custom tabs to the data structure
            existing_ids = [tab["id"] for tab in self.tool_box_data["tabs"]]
            for tab in loaded_data["tabs"]:
                if tab["id"] not in existing_ids:
                    self.tool_box_data["tabs"].append(tab)
            
            return True
        except Exception as e:
            print(f"Error loading tool box data from Maya: {e}")
            return False
            
    def _load_legacy_data_and_convert(self):
        """Load legacy data format and convert to the new consolidated format"""
        # Start with default tabs
        self.tool_box_data = {"tabs": list(self.default_tabs)}
        
        # Try to load custom toggle buttons
        self._load_legacy_toggle_buttons()
        
        # Try to load function buttons and associate them with tabs
        self._load_legacy_function_buttons()
        
        # Save in the new format
        self._save_consolidated_data_to_maya()
        
    def _load_legacy_toggle_buttons(self):
        """Load custom toggle buttons from Maya's defaultObjectSet using legacy format"""
        try:
            # Check if defaultObjectSet exists
            if not cmds.objExists('defaultObjectSet'):
                return False
                
            # Check if the attribute exists
            if not cmds.attributeQuery(self.toggle_attribute_name, node='defaultObjectSet', exists=True):
                return False
            
            # Get the attribute value
            toggle_buttons_json = cmds.getAttr(f'defaultObjectSet.{self.toggle_attribute_name}')
            
            # Check if the JSON string is empty or invalid
            if not toggle_buttons_json or toggle_buttons_json.strip() == '':
                return False
                
            # Convert the JSON string to a Python object
            custom_buttons = json.loads(toggle_buttons_json)
            
            # Validate the loaded data
            if not isinstance(custom_buttons, list):
                print("Invalid toggle button data format in Maya")
                return False
            
            # Add custom tabs to the data structure
            existing_ids = [tab["id"] for tab in self.tool_box_data["tabs"]]
            for btn in custom_buttons:
                if btn["id"] not in existing_ids:
                    # Convert legacy button to new tab format
                    tab = dict(btn)
                    tab["buttons"] = []  # Add empty buttons array
                    self.tool_box_data["tabs"].append(tab)
            
            return True
        except Exception as e:
            print(f"Error loading legacy toggle button data from Maya: {e}")
            return False
    
    def _load_legacy_function_buttons(self):
        """Load function buttons from Maya's defaultObjectSet using legacy format and associate with tabs"""
        try:
            # Check if defaultObjectSet exists
            if not cmds.objExists('defaultObjectSet'):
                return False
                
            # Check if the attribute exists
            if not cmds.attributeQuery(self.function_attribute_name, node='defaultObjectSet', exists=True):
                return False
            
            # Get the attribute value
            function_buttons_json = cmds.getAttr(f'defaultObjectSet.{self.function_attribute_name}')
            
            # Check if the JSON string is empty or invalid
            if not function_buttons_json or function_buttons_json.strip() == '':
                return False
                
            # Convert the JSON string to a Python object
            function_buttons = json.loads(function_buttons_json)
            
            # Validate the loaded data
            if not isinstance(function_buttons, list):
                print("Invalid function button data format in Maya")
                return False
            
            # Associate function buttons with their tabs
            for btn in function_buttons:
                if "tab_id" in btn:
                    tab_id = btn["tab_id"]
                    # Find the tab with this ID
                    for tab in self.tool_box_data["tabs"]:
                        if tab["id"] == tab_id:
                            # Add the function button to the tab
                            tab["buttons"].append(btn)
                            break
            
            return True
        except Exception as e:
            print(f"Error loading legacy function button data from Maya: {e}")
            return False
    
    def get_toggle_buttons(self):
        """Get all toggle buttons (tabs)"""
        return self.tool_box_data["tabs"]
    
    def get_function_buttons(self):
        """Get all function buttons (flattened list from all tabs)"""
        all_buttons = []
        for tab in self.tool_box_data["tabs"]:
            if "buttons" in tab:
                all_buttons.extend(tab["buttons"])
        return all_buttons
    
    def get_function_buttons_for_tab(self, tab_id):
        """Get function buttons for a specific tab"""
        for tab in self.tool_box_data["tabs"]:
            if tab["id"] == tab_id and "buttons" in tab:
                return tab["buttons"]
        return []
    
    def get_next_id(self):
        """Get the next available ID for toggle buttons (tabs)"""
        if not self.tool_box_data["tabs"]:
            return 0
        
        # Find the highest ID and add 1
        max_id = max(tab["id"] for tab in self.tool_box_data["tabs"])
        return max_id + 1
    
    def get_next_function_id(self):
        """Get the next available ID for function buttons"""
        all_buttons = self.get_function_buttons()
        if not all_buttons:
            return 0
        
        # Find the highest ID and add 1
        max_id = max(btn["id"] for btn in all_buttons) if all_buttons else -1
        return max_id + 1  
    
    def add_toggle_button(self, button_data):
        """Add a toggle button (tab) to the database"""
        # Check if this is a default button (ID 0, 1, or 2)
        if button_data["id"] <= 2:
            print(f"Cannot modify default button with ID {button_data['id']}")
            return False
            
        # Make sure the button data has a 'buttons' field
        if "buttons" not in button_data:
            button_data["buttons"] = []
            
        # Check if a button with this ID already exists
        for i, tab in enumerate(self.tool_box_data["tabs"]):
            if tab["id"] == button_data["id"]:
                # Preserve existing buttons if not provided in the new data
                if "buttons" not in button_data and "buttons" in tab:
                    button_data["buttons"] = tab["buttons"]
                # Replace the existing tab
                self.tool_box_data["tabs"][i] = button_data
                self.save_database()
                return True
        
        # Add the new tab
        self.tool_box_data["tabs"].append(button_data)
        self.save_database()
        return True
        
    def add_function_button(self, button_data):
        """Add a function button to the database"""
        # Make sure the button has a tab_id
        if "tab_id" not in button_data:
            print("Function button must have a tab_id")
            return False
            
        tab_id = button_data["tab_id"]
        
        # Find the tab for this button
        tab_found = False
        for tab in self.tool_box_data["tabs"]:
            if tab["id"] == tab_id:
                # Check if a button with this ID already exists in this tab
                if "buttons" not in tab:
                    tab["buttons"] = []
                    
                for i, btn in enumerate(tab["buttons"]):
                    if btn["id"] == button_data["id"]:
                        # Replace the existing button
                        tab["buttons"][i] = button_data
                        self.save_database()
                        return True
                
                # Add the new button to this tab
                tab["buttons"].append(button_data)
                tab_found = True
                break
        
        if not tab_found:
            print(f"Could not find tab with ID {tab_id}")
            return False
            
        self.save_database()
        return True
    
    def update_function_button(self, button_data):
        """Update a function button in the database"""
        button_id = button_data["id"]
        tab_id = button_data["tab_id"]
        
        # Find the tab for this button
        for tab in self.tool_box_data["tabs"]:
            if tab["id"] == tab_id:
                if "buttons" not in tab:
                    tab["buttons"] = []
                    
                # Find the button with this ID
                for i, btn in enumerate(tab["buttons"]):
                    if btn["id"] == button_id:
                        # Update the button data
                        tab["buttons"][i] = button_data
                        self.save_database()
                        return True
                
                # Button not found in this tab, add it
                tab["buttons"].append(button_data)
                self.save_database()
                return True
                
        # Tab not found
        print(f"Could not find tab with ID {tab_id}")
        return False
    
    def remove_toggle_button(self, button_id):
        """Remove a toggle button (tab) from the database"""
        # Prevent removal of default buttons (IDs 0, 1, 2)
        if button_id <= 2:
            print(f"Cannot remove default button with ID {button_id}")
            return False
            
        for i, tab in enumerate(self.tool_box_data["tabs"]):
            if tab["id"] == button_id:
                del self.tool_box_data["tabs"][i]
                self.save_database()
                return True
        return False

    def remove_function_button(self, button_id):
        """Remove a function button from the database"""
        # Find the button in all tabs
        for tab in self.tool_box_data["tabs"]:
            if "buttons" in tab:
                for i, button in enumerate(tab["buttons"]):
                    if button["id"] == button_id:
                        del tab["buttons"][i]
                        self.save_database()
                        return True
        return False
