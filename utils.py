import maya.cmds as cmds
from maya import OpenMayaUI as omui
from functools import wraps
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtGui import QColor
    from PySide6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtGui import QColor
    from PySide2.QtCore import QTimer, QPropertyAnimation, QEasingCurve
    from shiboken2 import wrapInstance
    

def undoable(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(openChunk=True)
        try:
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrapper

def rgba_value(hex_color, factor, alpha=None):
    color = QColor(hex_color)
    r, g, b, a = color.getRgbF()
    
    # Apply factor to RGB values
    r = min(max(r * factor, 0), 1)
    g = min(max(g * factor, 0), 1)
    b = min(max(b * factor, 0), 1)
    
    # Use the provided alpha if given, otherwise keep the original
    a = alpha if alpha is not None else a
    
    color.setRgbF(r, g, b, a)
    return color.name(QColor.HexArgb)

def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

def tool_box_window():
    """Return the current instance of the Tool Box window.
    
    Returns:
        QtWidgets.QWidget: The Tool Box window instance, or None if not open.
    """
    from . import main
    return main.tool_box_window

def activate_tool_box_window():
    """Activate the Tool Box window (bring to front and give focus).
    
    Returns:
        bool: True if window was activated, False if window doesn't exist.
    """
    window = tool_box_window()
    if window is not None:
        window.activateWindow()
        window.raise_()
        return True
    return False