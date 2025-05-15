import sys
from PySide2 import QtWidgets, QtCore, QtGui

# Import your custom_button module
from . import custom_button as CB

class SubMenuExample(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SubMenuExample, self).__init__(parent)
        self.setWindowTitle("Sub-Menu Example")
        self.resize(400, 200)
        
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # Create a button with context menu
        self.button = CB.CustomButton(
            text="Right-click for menu",
            color="#5285A6",
            tooltip="Right-click to show the context menu with sub-menu",
            ContextMenu=True
        )
        
        # Add the button to the layout
        layout.addWidget(self.button)
        
        # Add items to the context menu
        self.button.addToMenu("Option 1", lambda: print("Option 1 clicked"))
        self.button.addToMenu("Option 2", lambda: print("Option 2 clicked"))
        
        # Create a sub-menu
        sub_menu = self.button.subMenu("Sub-Menu")
        
        # Add items to the sub-menu
        sub_menu.addToMenu("Sub Option 1", lambda: print("Sub Option 1 clicked"))
        sub_menu.addToMenu("Sub Option 2", lambda: print("Sub Option 2 clicked"))
        
        # Create a nested sub-menu
        nested_sub_menu = sub_menu.subMenu("Nested Sub-Menu")
        nested_sub_menu.addToMenu("Nested Option", lambda: print("Nested Option clicked"))
        
        # Add the sub-menu to the main menu
        self.button.addToMenu(sub_menu)

# For testing outside of Maya
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SubMenuExample()
    window.show()
    sys.exit(app.exec_())
