try:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore
    from shiboken2 import wrapInstance

from . import ui as UI
from . import utils as UT
# Global variable to store the window instance
tool_box_window = None

def show_tool_box():
    """Show the Tool Box window"""
    global tool_box_window
    
    # Close existing window if it exists
    if tool_box_window is not None:
        try:
            tool_box_window.close()
            tool_box_window.deleteLater()
        except:
            pass
    
    # Create a new window
    tool_box_window = UI.ToolBoxWindow(parent=UT.maya_main_window())
    
    # Position the window in the center of the Maya window
    maya_window_center = UT.maya_main_window().geometry().center()
    window_width = 300  # Default width
    window_height = 70  # Default height
    tool_box_window.setGeometry(
        maya_window_center.x() - window_width // 2,
        maya_window_center.y() - window_height // 2,
        window_width,
        window_height
    )
    
    # Show the window
    tool_box_window.show()
    
    return tool_box_window

# Function to be called from Maya's script editor or shelf button
def run():
    """Run the Tool Box"""
    return show_tool_box()
run()
# For testing in Maya
#if __name__ == "__main__":
#    run()
