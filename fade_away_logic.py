try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QObject
    from PySide6.QtGui import QColor
    from shiboken6 import wrapInstance
    from PySide6.QtGui import QColor, QShortcut
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QObject
    from PySide2.QtGui import QColor
    from shiboken2 import wrapInstance

class FadeAway(QObject):
    def __init__(self, parent):
        super(FadeAway, self).__init__(parent)
        self.parent = parent
        self.fade_away_enabled = False
        self.context_menu_open = False

        self.fade_timer = QTimer(self)
        self.fade_timer.setSingleShot(True)
        self.fade_timer.timeout.connect(self.start_fade_animation)

        self.fade_animation = QPropertyAnimation(self.parent, b"windowOpacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.parent.installEventFilter(self)

    def handle_enter_event(self):
        if self.fade_away_enabled:
            self.fade_timer.stop()
            self.fade_animation.stop()
            self.fade_animation.setDuration(100)
            self.fade_animation.setStartValue(self.parent.windowOpacity())
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()

    def handle_leave_event(self):
        if self.fade_away_enabled and not self.context_menu_open:
            self.fade_timer.start(10)

    def start_fade_animation(self):
        if self.fade_away_enabled and not self.context_menu_open:
            self.fade_animation.setDuration(400)
            self.fade_animation.setStartValue(self.parent.windowOpacity())
            self.fade_animation.setEndValue(0.05)
            self.fade_animation.start()

    def toggle_fade_away(self):
        self.fade_away_enabled = not self.fade_away_enabled
        if not self.fade_away_enabled:
            self.fade_timer.stop()
            self.fade_animation.stop()
            self.parent.setWindowOpacity(1.0)
        else:
            self.fade_timer.start(10)

    def set_context_menu_open(self, is_open):
        self.context_menu_open = is_open

    def eventFilter(self, obj, event):
        if obj == self.parent:
            if event.type() == QtCore.QEvent.Enter:
                self.handle_enter_event()
            elif event.type() == QtCore.QEvent.Leave:
                self.handle_leave_event()
        return False
    
    def show_frame_context_menu(self, pos):
        self.context_menu_open = True
        menu = QtWidgets.QMenu(self.parent)
        
        # Remove background and shadow
        menu.setWindowFlags(menu.windowFlags() | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        menu.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        menu.setStyleSheet('''
        QMenu {
            background-color: rgba(30, 30, 30, .9);
            border-radius: 3px;
            padding: 5px;
        }
        QMenu::item {
            background-color: #222222;
            padding: 6px;
            border: 1px solid #00749a;
            border-radius: 3px;
            margin: 3px 0px;
        }
        QMenu::item:selected {
            background-color: #111111;
        }''')

        # Add label using QWidgetAction
        label = QtWidgets.QLabel("Tool Box Frame")
        #label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #dddddd;
                font-size: 12px;
                padding: 5px;
                background-color: transparent;
            }
        """)
        
        # Create a QWidgetAction to hold the label
        label_action = QtWidgets.QWidgetAction(menu)
        label_action.setDefaultWidget(label)
        menu.addAction(label_action)

        # Add toggle fade action
        toggle_fade_action = menu.addAction("Toggle Fade Away")
        toggle_fade_action.setCheckable(True)
        toggle_fade_action.setChecked(self.fade_away_enabled)
        
        # Use the parent's mapToGlobal method
        action = menu.exec_(self.parent.mapToGlobal(pos))
        
        self.context_menu_open = False
        if self.fade_away_enabled:
            self.fade_timer.start(10)
        if action == toggle_fade_action:
            self.toggle_fade_away()
