"""
Drag and drop this file into Maya to install the FT Tool Box.

This will:
- Create a button in the active shelf with the FT Tool Box logo
- The button will load/reload the FT Tool Box tool
"""

import maya.cmds as cmds
import maya.mel as mel
import os
import sys

def create_ft_tool_box_button():
    # Get the directory where this script is located
    script_dir = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))
    # Get the parent directory (where ft_tool_box is located)
    parent_dir = os.path.normpath(os.path.dirname(script_dir))
    
    # Define the icon path
    icon_path = os.path.join(script_dir, 'ft_tool_box_icons', 'fttb_logo_1080.png')
    
    # Create the command string - use raw string and normalize path
    parent_dir_normalized = parent_dir.replace("\\", "/")
    command_str = r'''
import sys
import os
sys.path.append("{0}")

import ft_tool_box.__unload_pkg as unld

try:
    unld.unload(ft_tool_box)
    import ft_tool_box.main
except:
    import ft_tool_box.main
    unld.unload(ft_tool_box)
'''.format(parent_dir_normalized)
    
    # Get the active shelf
    gShelfTopLevel = mel.eval('$tmpVar=$gShelfTopLevel')
    active_shelf = cmds.tabLayout(gShelfTopLevel, query=True, selectTab=True)
    
    # Create the button
    button = cmds.shelfButton(
        label="FT Tool Box",
        image=icon_path,
        command=command_str,
        parent=active_shelf,
        imageOverlayLabel="",
        overlayLabelColor=[1, 1, 1],
        overlayLabelBackColor=[0, 0, 0, 0],
    )
    
    print("FT Tool Box button added to the '{0}' shelf.".format(active_shelf))
    return "FT Tool Box button added to the '{0}' shelf.".format(active_shelf)

def onMayaDroppedPythonFile(*args, **kwargs):
    create_ft_tool_box_button()

# This will be executed when the file is dropped into Maya
if __name__ == '__main__':
    onMayaDroppedPythonFile()
