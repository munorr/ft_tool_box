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

class CustomScrollArea(QtWidgets.QScrollArea):
    def __init__(self, parent=None, invert_primary=False, horizontal_mode=False):
        """
        A custom scroll area that handles both vertical and horizontal scrolling with configurable inputs.
        
        Args:
            parent: Parent widget
            invert_primary: If True, primary scroll (mouse wheel) controls horizontal scrolling
                          If False, primary scroll controls vertical scrolling (default behavior)
            horizontal_mode: If True, optimizes for horizontal scrolling (hides vertical scrollbar)
                           If False, shows both scrollbars as needed
        """
        super(CustomScrollArea, self).__init__(parent)
        self.invert_primary = invert_primary
            
        self.setWidgetResizable(True)
        
        # Set focus policy to enable wheel events
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
    
    def wheelEvent(self, event):
        # Get both scrollbars
        hbar = self.horizontalScrollBar()
        vbar = self.verticalScrollBar()
        
        # Check if Alt key is pressed (secondary input)
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        alt_pressed = bool(modifiers & QtCore.Qt.AltModifier)
        
        # Get deltas
        delta_y = event.angleDelta().y()
        delta_x = event.angleDelta().x()
        
        # Make scrolling more responsive but not too fast
        sensitivity_factor = 10  # Higher value = less sensitive scrolling
        scroll_y = delta_y // sensitivity_factor  # Reduced sensitivity for vertical scrolling
        scroll_x = delta_x // sensitivity_factor  # Same reduced sensitivity for horizontal scrolling
        
        # Handle scrolling based on inversion setting and alt key
        if self.invert_primary:
            # Inverted: Primary (normal wheel) -> horizontal, Secondary (alt+wheel) -> vertical
            if alt_pressed:
                # Secondary input (Alt+Wheel) controls vertical
                # Check if scrolling is possible, even if scrollbar is hidden
                if vbar.maximum() > 0:
                    vbar.setValue(vbar.value() - scroll_y)
                    event.accept()
                    return
            else:
                # Primary input (Wheel) controls horizontal
                # Check if scrolling is possible, even if scrollbar is hidden
                if hbar.maximum() > 0:
                    # Use vertical delta for horizontal scrolling (more common in mice)
                    # Using the same reduced sensitivity as vertical scrolling
                    hbar.setValue(hbar.value() - scroll_y)
                    event.accept()
                    return
        else:
            # Normal: Primary (normal wheel) -> vertical, Secondary (alt+wheel) -> horizontal
            if alt_pressed:
                # Secondary input (Alt+Wheel) controls horizontal
                # Check if scrolling is possible, even if scrollbar is hidden
                if hbar.maximum() > 0:
                    hbar.setValue(hbar.value() - scroll_y)
                    event.accept()
                    return
            else:
                # Primary input (Wheel) controls vertical
                # Check if scrolling is possible, even if scrollbar is hidden
                if vbar.maximum() > 0:
                    vbar.setValue(vbar.value() - scroll_y)
                    event.accept()
                    return
                # If no vertical scrolling possible, try horizontal
                elif hbar.maximum() > 0:
                    hbar.setValue(hbar.value() - scroll_y)
                    event.accept()
                    return
            
        # If we get here, use default behavior
        super(CustomScrollArea, self).wheelEvent(event)
    
    def set_invert_primary(self, enabled):
        """Set whether to invert primary wheel behavior
        
        Args:
            enabled: If True, primary scroll (mouse wheel) controls horizontal scrolling
                    If False, primary scroll controls vertical scrolling (default behavior)
        """
        self.invert_primary = enabled

# For backward compatibility
class HorizontalScrollArea(CustomScrollArea):
    def __init__(self, parent=None, invert=False):
        super(HorizontalScrollArea, self).__init__(parent, invert_primary=invert, horizontal_mode=True)
        self.invert = invert
    
    def set_invert(self, enabled):
        self.invert = enabled
        self.set_invert_primary(enabled)
