# FT Tool Box

A versatile animation tool box for Maya, part of the Floating Tools (FT) collection.

## Features

- Customizable toggle button database system
- Center-aligned UI elements that expand to fill allocated space
- Custom grid layout for easier widget management
- Color picker functionality for Maya objects
- Dynamically add and remove custom tabs with their own widgets
- Data persistence between Maya sessions

## Installation

### Automatic Installation

1. Download or clone this repository to your local machine
2. Open Maya
3. Drag and drop the `drag_and_drop_installer.py` file onto the Maya viewport
4. The installation script will automatically:
   - Set up the module file in your Maya modules directory
   - Create or update your userSetup.py to load the FT menu
   - Add the FT menu to your current Maya session
5. Restart Maya to complete the installation

### Manual Installation

1. Copy the entire `ft_tool_box` directory to a location of your choice
2. Copy the `ft_tools.mod` file to your Maya modules directory:
   - Windows: `C:\Users\[username]\Documents\maya\[version]\modules`
   - macOS: `~/Library/Preferences/Autodesk/maya/[version]/modules`
   - Linux: `~/maya/[version]/modules`
3. Edit the module file to point to the location where you copied the `ft_tool_box` directory
4. Add the following code to your Maya userSetup.py:
   ```python
   import sys
   sys.path.append(r'path/to/ft_tool_box')
   import ft_tool_box.ft_menu_setup as menu_setup
   menu_setup.setup_ft_tools()
   ```
5. Restart Maya

## Usage

After installation, you can access the FT Tool Box from the Maya menu bar:

1. Click on the "FT" menu in the Maya menu bar
2. Select "FT Tool Box" to open the tool

## Uninstallation

1. Remove the `ft_tools.mod` file from your Maya modules directory
2. Remove the FT Tools setup code from your userSetup.py
3. Restart Maya

## Adding More Tools to the FT Menu

To add more tools to the FT menu, modify the `ft_menu_setup.py` file and add additional menu items in the `setup_ft_tools()` function.
