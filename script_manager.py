from functools import partial
import maya.cmds as cmds
import maya.mel as mel
import os
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtGui import QColor
    from PySide6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, Signal
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtGui import QColor
    from PySide2.QtCore import QTimer, QPropertyAnimation, QEasingCurve, Signal
    from shiboken2 import wrapInstance

import re

from . import utils as UT
from . import custom_button as CB

class ScriptSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(ScriptSyntaxHighlighter, self).__init__(parent)
        
        # Create format for special tokens
        self.special_format = QtGui.QTextCharFormat()
        self.special_format.setForeground(QtGui.QColor("#91CB08"))  # Bright green color
        self.special_format.setFontWeight(QtGui.QFont.Bold)

        # Create format for @TF. function call (darker green)
        self.tf_function_format = QtGui.QTextCharFormat()
        self.tf_function_format.setForeground(QtGui.QColor("#399dcd"))  # sky blue
        self.tf_function_format.setFontWeight(QtGui.QFont.Bold)

        # Create format for special tokens 2
        self.special_format_02 = QtGui.QTextCharFormat()
        self.special_format_02.setForeground(QtGui.QColor("#10b1cc"))  
        self.special_format_02.setFontWeight(QtGui.QFont.Bold)

        # Create format for brackets/parens/braces (yellow)
        self.bracket_format = QtGui.QTextCharFormat()
        self.bracket_format.setForeground(QtGui.QColor("#FFD700"))  # Yellow (Gold)
        self.bracket_format.setFontWeight(QtGui.QFont.Bold)
   
        # Create format for comments
        self.comment_format = QtGui.QTextCharFormat()
        self.comment_format.setForeground(QtGui.QColor("#555555"))  # Gray color for comments

        # Create format for quoted text in comments
        self.quoted_text_format = QtGui.QTextCharFormat()
        self.quoted_text_format.setForeground(QtGui.QColor("#ce9178"))

        # Create format for Python keywords
        self.keyword_format = QtGui.QTextCharFormat()
        self.keyword_format.setForeground(QtGui.QColor("#2666cb"))  # Slate blue
        self.keyword_format.setFontWeight(QtGui.QFont.Bold)

        # List of Python keywords
        self.python_keywords = [
            'def', 'class', 'if', 'else', 'elif', 'for', 'while', 'return', 'import', 'from', 'as', 'pass', 'break',
            'continue', 'try', 'except', 'finally', 'with', 'lambda', 'yield', 'global', 'nonlocal', 'assert', 'del',
            'raise', 'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None'
        ]
        self.keyword_pattern = r'\\b(' + '|'.join(self.python_keywords) + r')\\b'

        
    def highlightBlock(self, text):
        # Define all special tokens to highlight
        special_patterns = [
            r'@match_ik_to_fk\s*\([^)]*\)',  # Match @match_ik_to_fk() with any parameters
            r'@match_fk_to_ik\s*\([^)]*\)',   # Match @match_fk_to_ik() with any parameters
            r'@TF\.\w+\s*\([^)]*\)',    # Match @TF.function_name() with any parameters
        ]
        special_patterns_02 = [r'@ns\.'] # Original @ns pattern
        
        # Apply highlighting for @TF.functionName() pattern with split colors
        tf_pattern = r'(@TF\.)(\w+\s*\([^)]*\))'
        for match in re.finditer(tf_pattern, text):
            # Apply bright green to @TF.
            self.setFormat(match.start(1), len(match.group(1)), self.special_format)
            # Apply darker green to the function part
            self.setFormat(match.start(2), len(match.group(2)), self.tf_function_format)

        # Apply highlighting for other special patterns
        for pattern in special_patterns:
            if pattern == r'@TF\.\w+\s*\([^)]*\)':
                continue  # Already handled above
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), len(match.group()), self.special_format)
        
        for pattern in special_patterns_02:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), len(match.group()), self.special_format_02)
        
        # Highlight Python keywords
        for match in re.finditer(r'\b(' + '|'.join(self.python_keywords) + r')\b', text):
            self.setFormat(match.start(), len(match.group()), self.keyword_format)

        # Highlight (), {}, [] in yellow
        for match in re.finditer(r'[\(\)\{\}\[\]]', text):
            self.setFormat(match.start(), 1, self.bracket_format)
        
        # Highlight comments (lines starting with #)
        comment_pattern = r'#.*$'
        for match in re.finditer(comment_pattern, text):
            self.setFormat(match.start(), len(match.group()), self.comment_format)
        
        # Highlight quoted text (both single and double quotes)
        # Handle double quotes
        double_quote_pattern = r'"[^"\\]*(?:\\.[^"\\]*)*"'
        for match in re.finditer(double_quote_pattern, text):
            # Don't highlight quotes in comments
            start_pos = match.start()
            if not self.format(start_pos) == self.comment_format:
                self.setFormat(start_pos, len(match.group()), self.quoted_text_format)

        # Handle single quotes
        single_quote_pattern = r'\'[^\'\\]*(?:\\.[^\'\\]*)*\''
        for match in re.finditer(single_quote_pattern, text):
            # Don't highlight quotes in comments
            start_pos = match.start()
            if not self.format(start_pos) == self.comment_format:
                self.setFormat(start_pos, len(match.group()), self.quoted_text_format)

class ScriptManagerWidget(QtWidgets.QWidget):
    # Signal to notify when script is updated
    script_updated = QtCore.Signal(dict)
    
    def __init__(self, parent=None):
        if parent is None:
            # Lazy import MAIN to avoid circular dependency
            from . import main as MAIN
            manager = MAIN.PickerWindowManager.get_instance()
            parent = manager._picker_widgets[0] if manager._picker_widgets else None
        super(ScriptManagerWidget, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Setup resizing parameters
        self.resizing = False
        self.resize_edge = None
        self.resize_range = 8  # Pixels from edge where resizing is active
          # Set minimum size
        self.setGeometry(0,0,400,300)
        self.setMinimumSize(305, 300)
        # Setup main layout
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)
        
        # Create main frame
        self.frame = QtWidgets.QFrame()
        self.frame.setMinimumWidth(300)
        self.frame.setStyleSheet("""
            QFrame {
                background-color: rgba(36, 36, 36, .9);
                border: 1px solid #444444;
                border-radius: 4px;
            }
        """)
        self.frame_layout = QtWidgets.QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(6, 6, 6, 6)
        self.frame_layout.setSpacing(6)
        
        # Title bar with draggable area and close button
        self.title_bar = QtWidgets.QWidget()
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet("background: rgba(30, 30, 30, .9); border: none; border-radius: 3px;")
        title_layout = QtWidgets.QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(6, 6, 6, 6)
        title_layout.setSpacing(6)
        
        self.title_label = QtWidgets.QLabel("Script Manager (Python)")
        self.title_label.setStyleSheet("color: #dddddd; background: transparent;")
        title_layout.addSpacing(4)
        title_layout.addWidget(self.title_label)
        
        self.close_button = QtWidgets.QPushButton("✕")
        self.close_button.setFixedSize(16, 16)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 0, 0, 0.6);
                color: #ff9393;
                border: none;
                border-radius: 2px;
                padding: 0px 0px 2px 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.6);
            }
        """)
        title_layout.addWidget(self.close_button)
        
        # Language selection
        self.language_layout = QtWidgets.QHBoxLayout()
        self.language_layout.setAlignment(QtCore.Qt.AlignLeft)

        self.python_button = CB.CustomRadioButton("Python", fill=False, width=60, height=16, group=True)
        self.mel_button = CB.CustomRadioButton("MEL", fill=False, width=40, height=16, group=True)
        self.python_button.group('script_language')
        self.mel_button.group('script_language')

        self.function_preset_stack = QtWidgets.QStackedWidget()
        self.function_preset_stack.setFixedSize(20, 20)
        self.function_preset_stack.setStyleSheet("background: rgba(30, 30, 30, .9); border: none; border-radius: 3px;")
        self.python_function_preset_button = CB.CustomButton(text='', icon=':addClip.png', size=14, height=20, width=20, radius=3,color='#385c73',alpha=0,textColor='#aaaaaa', 
                                                             ContextMenu=True, onlyContext= True, cmColor='#333333',tooltip='Python function presets', flat=True)
        
        self.python_function_preset_button.addMenuLabel('Presets Commands',position=(0,0))
        self.python_function_preset_button.addToMenu('Set Attribute', self.ppf_set_attribute, position=(1,0))
        self.python_function_preset_button.addToMenu('Match IK to FK', self.ppf_match_ik_to_fk, position=(2,0))
        self.python_function_preset_button.addToMenu('Match FK to IK', self.ppf_match_fk_to_ik, position=(3,0))
        self.python_function_preset_button.addToMenu('Button Appearance', self.ppf_button_appearance, position=(4,0))
        self.python_function_preset_button.addToMenu('Get Selected Button IDs', self.ppf_get_selected_button_ids, position=(5,0))

        self.mel_function_preset_button = CB.CustomButton(text='', icon=':addClip.png', size=14, height=20, width=20, radius=3,color='#385c73',alpha=0,textColor='#aaaaaa', 
                                                          ContextMenu=True, onlyContext= True, cmColor='#333333',tooltip='Python function presets', flat=True)
        
        self.mel_function_preset_button.addMenuLabel('Presets Commands',position=(0,0))
        self.mel_function_preset_button.addToMenu('Set Attribute', self.mpf_set_attribute, position=(1,0))

        self.function_preset_stack.addWidget(self.python_function_preset_button)
        self.function_preset_stack.addWidget(self.mel_function_preset_button)

        self.language_layout.addWidget(self.python_button)
        self.language_layout.addWidget(self.mel_button)
        self.language_layout.addStretch()
        self.language_layout.addWidget(self.function_preset_stack)

        # Create custom QPlainTextEdit subclass with line numbers and tab handling
        class LineNumberArea(QtWidgets.QWidget):
            def __init__(self, editor):
                super(LineNumberArea, self).__init__(editor)
                self.editor = editor
                self.setFixedWidth(15)  # Initial width for line numbers - reduced to save space
            
            def sizeHint(self):
                return QtCore.QSize(self.editor.line_number_area_width(), 0)
            
            def paintEvent(self, event):
                self.editor.line_number_area_paint_event(event)
        
        class CodeEditor(QtWidgets.QPlainTextEdit):
            def __init__(self, parent=None):
                super(CodeEditor, self).__init__(parent)
                self.line_number_area = LineNumberArea(self)
                
                # Connect signals for updating line number area
                self.blockCountChanged.connect(self.update_line_number_area_width)
                self.updateRequest.connect(self.update_line_number_area)
                self.cursorPositionChanged.connect(self.highlight_current_line)
                
                # Initialize the line number area width
                self.update_line_number_area_width(0)
                
                # Highlight the current line
                self.highlight_current_line()
            
            def line_number_area_width(self):
                digits = 1
                max_num = max(1, self.blockCount())
                while max_num >= 10:
                    max_num //= 10
                    digits += 1
                
                space = 8 + self.fontMetrics().horizontalAdvance('9') * digits  # Reduced padding
                return space
            
            def update_line_number_area_width(self, _):
                # Set viewport margins to make room for line numbers
                width = self.line_number_area_width()
                # Add 15 pixels of extra margin to prevent text from touching the gutter
                self.setViewportMargins(width + 0, 0, 0, 0)
            
            def update_line_number_area(self, rect, dy):
                if dy:
                    self.line_number_area.scroll(0, dy)
                else:
                    self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
                
                if rect.contains(self.viewport().rect()):
                    self.update_line_number_area_width(0)
            
            def resizeEvent(self, event):
                super(CodeEditor, self).resizeEvent(event)
                
                cr = self.contentsRect()
                self.line_number_area.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
            
            def line_number_area_paint_event(self, event):
                painter = QtGui.QPainter(self.line_number_area)
                # Use a color that matches the editor background but is slightly different
                painter.fillRect(event.rect(), QtGui.QColor('#1e1e1e'))  # Match editor background
                
                # Draw a subtle separator line
                painter.setPen(QtGui.QColor('#2d2d2d'))
                painter.drawLine(event.rect().topRight(), event.rect().bottomRight())
                
                block = self.firstVisibleBlock()
                block_number = block.blockNumber()
                top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
                bottom = top + self.blockBoundingRect(block).height()
                
                while block.isValid() and top <= event.rect().bottom():
                    if block.isVisible() and bottom >= event.rect().top():
                        number = str(block_number + 1)
                        # Use a more subtle color for line numbers
                        painter.setPen(QtGui.QColor('#6d6d6d'))  # Line number color
                        painter.drawText(0, top, self.line_number_area.width() - 3, self.fontMetrics().height(),
                                        QtCore.Qt.AlignRight, number)
                    
                    block = block.next()
                    top = bottom
                    bottom = top + self.blockBoundingRect(block).height()
                    block_number += 1
            
            def highlight_current_line(self):
                extra_selections = []
                
                if not self.isReadOnly():
                    selection = QtWidgets.QTextEdit.ExtraSelection()
                    line_color = QtGui.QColor('#222222')  # Current line highlight color
                    
                    selection.format.setBackground(line_color)
                    selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
                    selection.cursor = self.textCursor()
                    selection.cursor.clearSelection()
                    extra_selections.append(selection)
                
                self.setExtraSelections(extra_selections)
            
            def keyPressEvent(self, event):
                # Explicitly check for Shift+Tab and handle it first
                if event.key() == QtCore.Qt.Key_Backtab:
                    # Qt sends Key_Backtab for Shift+Tab
                    event.accept()  # Prevent event propagation
                    self._handle_shift_tab()
                    return
                elif event.key() == QtCore.Qt.Key_Tab:
                    if event.modifiers() & QtCore.Qt.ShiftModifier:
                        event.accept()  # Prevent event propagation
                        self._handle_shift_tab()
                        return
                    else:
                        handled = self._handle_tab()
                        if handled:
                            event.accept()  # Prevent event propagation
                            return
                elif event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                    if self._handle_enter():
                        event.accept()  # Prevent event propagation
                        return
                # Pass unhandled events to parent
                super().keyPressEvent(event)

            def _handle_tab(self):
                cursor = self.textCursor()
                if cursor.hasSelection():
                    start = cursor.selectionStart()
                    end = cursor.selectionEnd()
                    cursor.setPosition(start)
                    start_block = cursor.blockNumber()
                    cursor.setPosition(end)
                    end_block = cursor.blockNumber()
                    cursor.beginEditBlock()
                    for _ in range(end_block - start_block + 1):
                        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
                        cursor.insertText("    ")
                        cursor.movePosition(QtGui.QTextCursor.NextBlock)
                    cursor.endEditBlock()
                    # Restore selection
                    cursor.setPosition(start + 4)  # +4 for the added spaces
                    cursor.setPosition(end + 4 * (end_block - start_block + 1), QtGui.QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)
                    return True
                else:
                    # Store current position
                    pos = cursor.position()
                    line_pos = cursor.positionInBlock()
                    cursor.beginEditBlock()
                    cursor.movePosition(QtGui.QTextCursor.StartOfLine)
                    cursor.insertText("    ")
                    cursor.endEditBlock()
                    # Move cursor to after the inserted spaces
                    cursor.setPosition(pos + 4)  # +4 for the added spaces
                    self.setTextCursor(cursor)
                    return True

            def _handle_shift_tab(self):
                cursor = self.textCursor()
                if cursor.hasSelection():
                    # Store selection info
                    start = cursor.selectionStart()
                    end = cursor.selectionEnd()
                    cursor.setPosition(start)
                    start_block = cursor.blockNumber()
                    start_pos_in_block = cursor.positionInBlock()
                    cursor.setPosition(end)
                    end_block = cursor.blockNumber()
                    end_pos_in_block = cursor.positionInBlock()
                    
                    # Track how many spaces were removed from each line
                    spaces_removed = []
                    
                    cursor.beginEditBlock()
                    # Process each line in the selection
                    for i in range(end_block - start_block + 1):
                        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
                        line_text = cursor.block().text()
                        
                        # Count leading spaces/tabs
                        spaces_to_remove = 0
                        if line_text.startswith("    "):  # 4 spaces
                            spaces_to_remove = 4
                        elif line_text.startswith(" "):  # 1-3 spaces
                            for j, char in enumerate(line_text):
                                if char == ' ' and j < 4:
                                    spaces_to_remove += 1
                                else:
                                    break
                        elif line_text.startswith("\t"):  # Tab
                            spaces_to_remove = 1  # Count tab as 1 character
                        
                        # Remove the spaces/tab if any
                        if spaces_to_remove > 0:
                            cursor.movePosition(QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor, spaces_to_remove)
                            cursor.removeSelectedText()
                        
                        spaces_removed.append(spaces_to_remove)
                        cursor.movePosition(QtGui.QTextCursor.NextBlock)
                    cursor.endEditBlock()
                    
                    # Adjust selection start/end based on removed spaces
                    new_start = start - (spaces_removed[0] if start_pos_in_block >= spaces_removed[0] else start_pos_in_block)
                    
                    # Calculate total spaces removed before end position
                    total_spaces_before_end = sum(spaces_removed[:end_block - start_block])
                    # Add spaces removed from the last line if cursor is past them
                    if end_pos_in_block >= spaces_removed[end_block - start_block]:
                        total_spaces_before_end += spaces_removed[end_block - start_block]
                    else:
                        total_spaces_before_end += end_pos_in_block
                    
                    new_end = end - total_spaces_before_end
                    
                    # Restore adjusted selection
                    cursor.setPosition(new_start)
                    cursor.setPosition(new_end, QtGui.QTextCursor.KeepAnchor)
                    self.setTextCursor(cursor)
                    return True
                else:
                    # Store cursor position
                    original_pos = cursor.position()
                    pos_in_block = cursor.positionInBlock()
                    
                    cursor.beginEditBlock()
                    cursor.movePosition(QtGui.QTextCursor.StartOfLine)
                    line_text = cursor.block().text()
                    
                    # Count leading spaces/tabs
                    spaces_to_remove = 0
                    if line_text.startswith("    "):  # 4 spaces
                        spaces_to_remove = 4
                    elif line_text.startswith(" "):  # 1-3 spaces
                        for i, char in enumerate(line_text):
                            if char == ' ' and i < 4:
                                spaces_to_remove += 1
                            else:
                                break
                    elif line_text.startswith("\t"):  # Tab
                        spaces_to_remove = 1  # Count tab as 1 character
                    
                    # Remove the spaces/tab if any
                    if spaces_to_remove > 0:
                        cursor.movePosition(QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor, spaces_to_remove)
                        cursor.removeSelectedText()
                    
                    # Adjust cursor position
                    new_pos = original_pos - (spaces_to_remove if pos_in_block >= spaces_to_remove else pos_in_block)
                    cursor.setPosition(new_pos)
                    cursor.endEditBlock()
                    
                    self.setTextCursor(cursor)
                    return True

            def _handle_enter(self):
                cursor = self.textCursor()
                cursor.beginEditBlock()
                
                # Get current line and position within line
                current_line = cursor.block().text()
                position_in_line = cursor.positionInBlock()
                
                # Extract text before and after cursor on current line
                text_before_cursor = current_line[:position_in_line]
                text_after_cursor = current_line[position_in_line:]
                
                # Get indentation of current line
                indent = ''
                for char in current_line:
                    if char in (' ', '\t'):
                        indent += char
                    else:
                        break
                
                # Check if current line ends with ':' (before the cursor)
                add_extra_indent = text_before_cursor.rstrip().endswith(':')
                
                # Check if cursor is at the end of the line
                at_end_of_line = position_in_line == len(current_line)
                
                # Insert newline with appropriate indentation
                if add_extra_indent:
                    # Add one level of indentation
                    cursor.insertText("\n" + indent + "    " + text_after_cursor)
                    # Only move cursor up if not at the end of the line
                    if not at_end_of_line:
                        cursor.movePosition(QtGui.QTextCursor.Up)
                        cursor.movePosition(QtGui.QTextCursor.EndOfLine)
                    else:
                        # Position cursor after the indentation on the new line
                        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
                        cursor.movePosition(QtGui.QTextCursor.Right, QtGui.QTextCursor.MoveAnchor, len(indent) + 4)
                else:
                    # Maintain same indentation level
                    cursor.insertText("\n" + indent + text_after_cursor)
                    # Only handle text removal if not at the end of the line
                    if not at_end_of_line:
                        # Remove the duplicated text after cursor
                        end_pos = cursor.position()
                        cursor.setPosition(end_pos - len(text_after_cursor))
                        cursor.setPosition(end_pos, QtGui.QTextCursor.KeepAnchor)
                        cursor.removeSelectedText()
                    else:
                        # Position cursor after the indentation on the new line
                        cursor.movePosition(QtGui.QTextCursor.StartOfLine)
                        cursor.movePosition(QtGui.QTextCursor.Right, QtGui.QTextCursor.MoveAnchor, len(indent))
                
                cursor.endEditBlock()
                self.setTextCursor(cursor)
                return True

        # Editor style
        editor_style = """
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #dddddd;
                border: 0px solid #444444;
                border-radius: 3px;
                padding: 5px 5px 5px 15px; /* Added significant left padding to prevent text from being under line numbers */
                font-family: Consolas, Monaco, monospace;
                selection-background-color: #264f78;
            }
        """
        
        # Create editors using the custom CodeEditor class
        self.python_editor = CodeEditor()
        self.python_editor.setStyleSheet(editor_style)
        self.python_highlighter = ScriptSyntaxHighlighter(self.python_editor.document())
        # Force document margin to create space for line numbers
        self.python_editor.document().setDocumentMargin(5)
        
        self.mel_editor = CodeEditor()
        self.mel_editor.setStyleSheet(editor_style)
        self.mel_highlighter = ScriptSyntaxHighlighter(self.mel_editor.document())
        # Force document margin to create space for line numbers
        self.mel_editor.document().setDocumentMargin(15)
        
        # Set tab width for both editors
        font = self.python_editor.font()
        font_metrics = QtGui.QFontMetrics(font)
        space_width = font_metrics.horizontalAdvance(' ')
        self.python_editor.setTabStopDistance(space_width * 4)
        self.mel_editor.setTabStopDistance(space_width * 4)
        
        # Create stacked widget for editors
        self.editor_stack = QtWidgets.QStackedWidget()
        self.editor_stack.setMinimumSize(100, 100)
        #self.editor_stack.setMinimumHeight(100)
        self.editor_stack.addWidget(self.python_editor)
        self.editor_stack.addWidget(self.mel_editor)

        # Apply Button
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.setFixedHeight(24)
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #5285a6;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 2px 10px;
            }
            QPushButton:hover {
                background-color: #77c2f2;
            }
        """)
        
        # Add widgets to layout
        self.frame_layout.addWidget(self.title_bar)
        self.frame_layout.addLayout(self.language_layout)
        self.frame_layout.addWidget(self.editor_stack)
        self.frame_layout.addWidget(self.apply_button)
        self.main_layout.addWidget(self.frame)
        
        # Connect signals
        self.close_button.clicked.connect(self.close)
        self.apply_button.clicked.connect(self.execute_code)
        self.python_button.toggled.connect(self.update_language_selection)
        self.mel_button.toggled.connect(self.update_language_selection)
        
        # Setup event handling for dragging and resizing
        self.dragging = False
        self.offset = None
        self.title_bar.mousePressEvent = self.title_bar_mouse_press
        self.title_bar.mouseMoveEvent = self.title_bar_mouse_move
        self.title_bar.mouseReleaseEvent = self.title_bar_mouse_release
        
        # Install event filter for the frame
        self.frame.setMouseTracking(True)
        self.frame.installEventFilter(self)
        
        self.picker_button = None
        self.current_button_data = None
        self.current_button = None
    #--------------------------------------------------------------------------------------------------------------------
    # Preset Functions
    #--------------------------------------------------------------------------------------------------------------------
    def ppf_match_ik_to_fk(self): # Match IK to FK
        preset_code = '''#Replace the ik_controls and fk_joints with your own names
ik_controls = ['@ns.ik_pole_ctrl', '@ns.ik_arm_or_leg_ctrl'] 
fk_joints = ['@ns.fk_upper_arm_or_leg_jnt', '@ns.fk_elbow_or_knee_jnt', '@ns.fk_wrist_or_ankle_jnt'] 
@match_ik_to_fk(ik_controls, fk_joints)'''
        
        # Insert code at the current cursor position
        cursor = self.python_editor.textCursor()
        cursor.insertText(preset_code)
        self.python_editor.setFocus()

    def ppf_match_fk_to_ik(self): # Match FK to IK
        preset_code = '''#Replace the fk_controls and ik_joints with your own names
fk_controls = ['@ns.fk_upper_arm_or_leg_ctrl', '@ns.fk_elbow_or_knee_ctrl', '@ns.fk_wrist_or_ankle_ctrl'] 
ik_joints = ['@ns.ik_upper_arm_or_leg_jnt', '@ns.ik_elbow_or_knee_jnt', '@ns.ik_wrist_or_ankle_jnt'] 
@match_fk_to_ik(fk_controls, ik_joints)'''
        
        # Insert code at the current cursor position
        cursor = self.python_editor.textCursor()
        cursor.insertText(preset_code)
        self.python_editor.setFocus()
    
    def ppf_set_attribute(self): # Match FK to IK
        preset_code = '''#Replace the Object, Attribute and Attribute Value with your own names
cmds.setAttr("@ns.Object.Attribute", AttributeValue)'''
        
        # Insert code at the current cursor position
        cursor = self.python_editor.textCursor()
        cursor.insertText(preset_code)
        self.python_editor.setFocus()

    def ppf_button_appearance(self): # Button Appearance
        preset_code = '''@TF.button_appearance(text=" ", opacity=1, selectable=1, target_buttons=None)'''
        
        # Insert code at the current cursor position
        cursor = self.python_editor.textCursor()
        cursor.insertText(preset_code)
        self.python_editor.setFocus()
        
    def ppf_get_selected_button_ids(self): # Get Selected Button IDs
        # Get the canvas from the picker button
        canvas = None
        if self.picker_button:
            canvas = self.picker_button.parent()
            
        if canvas:
            # Get all selected buttons
            selected_buttons = canvas.get_selected_buttons()
            
            # Extract button IDs
            button_ids = [button.unique_id for button in selected_buttons]
            
            # Create the preset code
            preset_code = f'''button_ids = {button_ids}'''
            
            # Insert code at the current cursor position
            cursor = self.python_editor.textCursor()
            cursor.insertText(preset_code)
            self.python_editor.setFocus()
    #--------------------------------------------------------------------------------------------------------------------
    def mel_preset_function_01(self):
        print('Mel Preset Function 01')

    def mpf_set_attribute(self): # Match FK to IK
        preset_code = '''#Replace the Object, Attribute and Attribute Value with your own names
setAttr "@ns.Object.Attribute" Attribute Value;'''
        
        # Insert code at the current cursor position
        cursor = self.mel_editor.textCursor()
        cursor.insertText(preset_code)
        self.mel_editor.setFocus()  
    #--------------------------------------------------------------------------------------------------------------------
    def set_picker_button(self, button):
        """Modified to ensure proper initialization of script data for individual buttons"""
        self.picker_button = button
        script_data = button.script_data if isinstance(button.script_data, dict) else {}
        
        # Create default script data if not properly formatted
        if not script_data:
            script_data = {
                'type': 'python',
                'python_code': '',
                'mel_code': '',
                'code': ''  # For backwards compatibility
            }
            
        # Set the editors' content from button-specific data
        self.python_editor.setPlainText(script_data.get('python_code', ''))
        self.mel_editor.setPlainText(script_data.get('mel_code', ''))
        
        # Set the correct language button based on stored type
        script_type = script_data.get('type', 'python')
        if script_type == 'python':
            self.python_button.setChecked(True)
        else:
            self.mel_button.setChecked(True)
        
        # Make sure to update the button's script data
        button.script_data = script_data
        
        self.position_window()

    def position_window(self):
        if self.picker_button:
            button_geometry = self.picker_button.geometry()
            scene_pos = self.picker_button.scene_position
            canvas = self.picker_button.parent()
            
            if canvas:
                canvas_pos = canvas.scene_to_canvas_coords(scene_pos)
                global_pos = canvas.mapToGlobal(canvas_pos.toPoint())
                self.move(global_pos) #+ QtCore.QPoint(button_geometry.width() + 10, 0))

    def update_language_selection(self, checked):
        if checked:  # Only respond to the button being checked
            is_python = self.python_button.isChecked()
            self.title_label.setText("Script Manager (Python)" if is_python else "Script Manager (MEL)")
            self.editor_stack.setCurrentIndex(0 if is_python else 1)
            self.function_preset_stack.setCurrentIndex(0 if is_python else 1)
            
    def execute_code(self):
        """Modified to ensure each button gets its own script data"""
        if self.picker_button:
            # Create fresh script data for this button
            script_data = {
                'type': 'python' if self.python_button.isChecked() else 'mel',
                'python_code': self.python_editor.toPlainText(),
                'mel_code': self.mel_editor.toPlainText(),
                'code': self.python_editor.toPlainText() if self.python_button.isChecked() else self.mel_editor.toPlainText()
            }
            
            # Update the button's script data
            self.picker_button.script_data = script_data
            self.picker_button.changed.emit(self.picker_button)
            self.close()
        elif self.current_button_data:
            # Update the current button data with the new script
            script_type = 'python' if self.python_button.isChecked() else 'mel'
            script_text = self.python_editor.toPlainText() if script_type == 'python' else self.mel_editor.toPlainText()
            
            # Update the button data
            self.current_button_data['script_type'] = script_type
            self.current_button_data['script'] = script_text
            
            # Emit the signal to notify that the script has been updated
            self.script_updated.emit(self.current_button_data)
            self.close()
    #---------------------------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if obj == self.frame:
            if event.type() == QtCore.QEvent.MouseMove:
                if not self.resizing:
                    pos = self.mapFromGlobal(self.frame.mapToGlobal(event.pos()))
                    if self.is_in_resize_range(pos):
                        self.update_cursor(pos)
                    else:
                        self.unsetCursor()
                return False
            elif event.type() == QtCore.QEvent.Leave:
                if not self.resizing:
                    self.unsetCursor()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.resize_edge = self.get_resize_edge(event.pos())
            if self.resize_edge:
                self.resizing = True
                self.resize_start_pos = event.globalPos()
                self.initial_size = self.size()
                self.initial_pos = self.pos()
            else:
                self.resizing = False
        UT.maya_main_window().activateWindow()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.resizing and self.resize_edge:
            delta = event.globalPos() - self.resize_start_pos
            new_geometry = self.geometry()
            
            if 'left' in self.resize_edge:
                new_width = max(self.minimumWidth(), self.initial_size.width() - delta.x())
                new_x = self.initial_pos.x() + delta.x()
                if new_width >= self.minimumWidth():
                    new_geometry.setLeft(new_x)
                
            if 'right' in self.resize_edge:
                new_width = max(self.minimumWidth(), self.initial_size.width() + delta.x())
                new_geometry.setWidth(new_width)
                
            if 'top' in self.resize_edge:
                new_height = max(self.minimumHeight(), self.initial_size.height() - delta.y())
                new_y = self.initial_pos.y() + delta.y()
                if new_height >= self.minimumHeight():
                    new_geometry.setTop(new_y)
                
            if 'bottom' in self.resize_edge:
                new_height = max(self.minimumHeight(), self.initial_size.height() + delta.y())
                new_geometry.setHeight(new_height)
            
            self.setGeometry(new_geometry)
        
        elif not self.resizing:
            if self.is_in_resize_range(event.pos()):
                self.update_cursor(event.pos())
            else:
                self.unsetCursor()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.resizing = False
            self.resize_edge = None
            self.unsetCursor()

    def closeEvent(self, event):
        super().closeEvent(event)
        UT.maya_main_window().activateWindow()

    def is_in_resize_range(self, pos):
        width = self.width()
        height = self.height()
        edge_size = self.resize_range

        return (pos.x() <= edge_size or 
                pos.x() >= width - edge_size or 
                pos.y() <= edge_size or 
                pos.y() >= height - edge_size)
    
    def get_resize_edge(self, pos):
        width = self.width()
        height = self.height()
        edge_size = self.resize_range
        
        is_top = pos.y() <= edge_size
        is_bottom = pos.y() >= height - edge_size
        is_left = pos.x() <= edge_size
        is_right = pos.x() >= width - edge_size
        
        if is_top and is_left: return 'top_left'
        if is_top and is_right: return 'top_right'
        if is_bottom and is_left: return 'bottom_left'
        if is_bottom and is_right: return 'bottom_right'
        if is_top: return 'top'
        if is_bottom: return 'bottom'
        if is_left: return 'left'
        if is_right: return 'right'
        return None

    def update_cursor(self, pos):
        edge = self.get_resize_edge(pos)
        cursor = QtCore.Qt.ArrowCursor
        
        if edge:
            cursor_map = {
                'top': QtCore.Qt.SizeVerCursor,
                'bottom': QtCore.Qt.SizeVerCursor,
                'left': QtCore.Qt.SizeHorCursor,
                'right': QtCore.Qt.SizeHorCursor,
                'top_left': QtCore.Qt.SizeFDiagCursor,
                'bottom_right': QtCore.Qt.SizeFDiagCursor,
                'top_right': QtCore.Qt.SizeBDiagCursor,
                'bottom_left': QtCore.Qt.SizeBDiagCursor
            }
            cursor = cursor_map.get(edge, QtCore.Qt.ArrowCursor)
        
        self.setCursor(cursor)
    #---------------------------------------------------------------------------------------
    # Window dragging methods
    def title_bar_mouse_press(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
        UT.maya_main_window().activateWindow()
            
    def title_bar_mouse_move(self, event):
        if self.dragging and event.buttons() == QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.offset)
            
    def title_bar_mouse_release(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
            
    def set_script(self, script_text):
        """Set the script text in the current editor"""
        self.python_editor.setPlainText(script_text)
        
    def set_current_button_data(self, button_data):
        """Set the current button data and update the UI"""
        self.current_button_data = button_data
        self.current_button = None
        
        # Set the script text
        if "script" in button_data:
            self.python_editor.setPlainText(button_data["script"])
        else:
            self.python_editor.setPlainText("")
        
        # Set the script type
        if "script_type" in button_data and button_data["script_type"] == "mel":
            self.mel_button.setChecked(True)
        else:
            self.python_button.setChecked(True)
            
        # Update the title to include the button name
        if "text" in button_data:
            self.title_label.setText(f"Script Manager - {button_data['text']}")
        else:
            self.title_label.setText("Script Manager")
