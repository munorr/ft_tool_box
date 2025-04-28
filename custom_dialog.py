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

class CustomDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, title="", size=(250, 150), info_box=False):
        super(CustomDialog, self).__init__(parent)
        self.info_box = info_box
        self.setWindowTitle(title)
        self.setFixedSize(*size)
        self.setStyleSheet('''
            QDialog {
                background-color: rgba(40, 40, 40, 0.9);
                border-radius: 5px;
            }
            QLabel, QRadioButton {
                color: white;
                background-color: transparent;
            }
            QLineEdit {
                background-color: #4d4d4d;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                color: white;
                border: none;
                background-color: #5285A6;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #6297B8;
            }
            QPushButton:pressed {
                background-color: #3F6F8F;
            }
            QPushButton#acceptButton {
                background-color: #00749a;
            }
            QPushButton#acceptButton:hover {
                background-color: #00ade6;
            }
            QPushButton#closeButton {
                background-color: #a30000;
            }
            QPushButton#closeButton:hover {
                background-color: #ff0000;
            }
            QPushButton#okayButton {
                background-color: #00749a;
            }
            QPushButton#okayButton:hover {
                background-color: #00ade6;
            }
            QComboBox {
                background-color: #444444;
                color: white;
                padding: 5px;
            }
            QPlainTextEdit {
                background-color: #2d2d2d;
                color: #f8f8f2;
                border: none;
                font-family: Consolas, Monaco, 'Courier New', monospace;
                font-size: 11pt;
                padding: 5px;
            }
        ''')
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # Add Enter key shortcut
        try:
            self.enter_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Return), self)
        except:
            self.enter_shortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Return), self)
        self.enter_shortcut.activated.connect(self.accept)

    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def add_layout(self, layout):
        self.layout.addLayout(layout)
        
    def add_line_edit(self, placeholder="", default_text=""):
        line_edit = QtWidgets.QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setText(default_text)
        self.add_widget(line_edit)
        return line_edit
        
    def add_label(self, text, align=QtCore.Qt.AlignLeft):
        label = QtWidgets.QLabel(text)
        label.setAlignment(align)
        self.add_widget(label)
        return label
        
    def add_color_picker(self, default_color="#5285A6"):
        color_layout = QtWidgets.QHBoxLayout()
        color_label = QtWidgets.QLabel("Color:")
        color_button = QtWidgets.QPushButton()
        color_button.setFixedSize(24, 24)
        color_button.setStyleSheet(f"background-color: {default_color}; border-radius: 3px;")
        
        color_layout.addWidget(color_label)
        color_layout.addWidget(color_button)
        color_layout.addStretch()
        
        self.add_layout(color_layout)
        
        # Store the current color
        color_button.color = default_color
        
        # Connect color picker
        def show_color_dialog():
            color = QtWidgets.QColorDialog.getColor(QColor(color_button.color), self)
            if color.isValid():
                color_hex = color.name()
                color_button.setStyleSheet(f"background-color: {color_hex}; border-radius: 3px;")
                color_button.color = color_hex
                
        color_button.clicked.connect(show_color_dialog)
        return color_button

    def add_button_box(self):
        if self.info_box:
            button_layout = QtWidgets.QHBoxLayout()
            okay_button = QtWidgets.QPushButton("Okay")
            okay_button.setObjectName("okayButton")
            button_layout.addWidget(okay_button)
            self.layout.addStretch()
            self.layout.addLayout(button_layout)
            okay_button.clicked.connect(self.accept)
            return okay_button
        else:
            button_layout = QtWidgets.QHBoxLayout()
            accept_button = QtWidgets.QPushButton("Accept")
            close_button = QtWidgets.QPushButton("Close")
            accept_button.setObjectName("acceptButton")
            close_button.setObjectName("closeButton")
            button_layout.addWidget(accept_button)
            button_layout.addWidget(close_button)
            self.layout.addStretch()
            self.layout.addLayout(button_layout)
            accept_button.clicked.connect(self.accept)
            close_button.clicked.connect(self.reject)
            return accept_button, close_button
            
class InputDialog(CustomDialog):
    def __init__(self, parent=None, title="", prompt="", default_text="", size=(300, 120)):
        super(InputDialog, self).__init__(parent, title, size)
        
        # Add prompt label
        self.add_label(prompt)
        
        # Add text input
        self.text_input = self.add_line_edit(default_text=default_text)
        
        # Add button box
        self.add_button_box()
        
        # Set focus to the text input
        self.text_input.setFocus()
        
    def get_text(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            return self.text_input.text()
        return None

class ScriptDialog(CustomDialog):
    def __init__(self, parent=None, title="Script Editor", script_text="", size=(500, 300)):
        super(ScriptDialog, self).__init__(parent, title, size)
        
        # Add script editor
        self.script_editor = QtWidgets.QPlainTextEdit()
        self.script_editor.setPlainText(script_text)
        self.add_widget(self.script_editor)
        
        # Add button box
        self.add_button_box()
        
        # Set focus to the script editor
        self.script_editor.setFocus()
        
    def get_script(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            return self.script_editor.toPlainText()
        return None

class ColorPickerDialog(CustomDialog):
    def __init__(self, parent=None, title="Choose Color", default_color="#5285A6", size=(300, 120)):
        super(ColorPickerDialog, self).__init__(parent, title, size)
        
        # Add color picker
        self.color_button = self.add_color_picker(default_color)
        
        # Add button box
        self.add_button_box()
        
    def get_color(self):
        if self.exec_() == QtWidgets.QDialog.Accepted:
            return self.color_button.color
        return None
    