import os
from functools import partial
import maya.cmds as cmds
from pathlib import Path

try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
    from PySide6.QtGui import QColor
    from shiboken6 import wrapInstance
    from PySide6.QtGui import QColor, QShortcut
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtCore import QTimer, QPropertyAnimation, QEasingCurve
    from PySide2.QtGui import QColor
    from PySide2.QtWidgets import QShortcut
    from shiboken2 import wrapInstance

from . import custom_button as CB
from . import utils as UT
from . import tool_functions as TF
from . import flow_layout as FL
from . import custom_scroll as CS
from . import fade_away_logic as FAL

class ToolBoxWindow(QtWidgets.QWidget):
    def __init__(self, parent=None, title="Tool Box"):
        super(ToolBoxWindow, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Setup dragging parameters
        self.dragging = False
        self.offset = None
        
        # Setup resizing parameters
        self.resizing = False
        self.resize_edge = None
        self.resize_range = 8  # Pixels from edge where resizing is active
        self.cursor_override_active = False
        
        # Set minimum size to 70x30 as requested
        self.setMinimumSize(100, 70)
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        #-----------------------------------------------------------------------------------------------------------------------------
        # Setup main layout
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)

        self.body_layout = QtWidgets.QVBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        self.main_layout.addLayout(self.body_layout)

        self.body_header_layout = QtWidgets.QHBoxLayout()
        self.body_header_layout.setContentsMargins(2, 2, 2, 2)
        self.body_header_layout.setSpacing(2)
        self.body_layout.addLayout(self.body_header_layout)

        self.body_content_layout = QtWidgets.QVBoxLayout()
        self.body_content_layout.setContentsMargins(2, 2, 2, 2)
        self.body_content_layout.setSpacing(2)
        self.body_layout.addLayout(self.body_content_layout)
        
        self.utility_layout = QtWidgets.QVBoxLayout()
        #self.utility_layout.setAlignment(QtCore.Qt.AlignTop)
        self.utility_layout.setContentsMargins(2, 2, 2, 2)
        self.utility_layout.setSpacing(2)
        self.main_layout.addLayout(self.utility_layout)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Create main frame
        self.frame = QtWidgets.QFrame()
        # Define default frame style
        self.default_frame_style = """
            QFrame {background-color: rgba(36, 36, 36, .7);border: 1px solid #444444;border-radius: 4px;}
        """
        
        # Define resize frame style 
        self.resize_frame_style = """
            QFrame {background-color: rgba(36, 36, 36, .7);border: 1px solid #2f8cad;border-radius: 4px;}
        """
        
        # Apply default style initially
        self.frame.setStyleSheet(self.default_frame_style)
        self.frame_layout = QtWidgets.QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(6, 6, 6, 6)
        self.frame_layout.setSpacing(2)
        #-----------------------------------------------------------------------------------------------------------------------------
        #self.util_button = CB.CustomButton(icon=":moreOverlay.png", width=20, height=20, radius=10,color="#262626", ContextMenu=True, onlyContext=True, tooltip="Open Util Menu")
        self.util_button = CB.CustomButton(text="☰",width=20, height=20, radius=3,color="#555555", textColor="#888888",text_size=8, ContextMenu=True, onlyContext=True, tooltip="Open Util Menu")
        self.util_button.addToMenu('Close', self.close, icon="closeTabButton.png", position=(0,0))
        self.utility_layout.addSpacing(10)
        self.utility_layout.addWidget(self.util_button)
        
        # Connect to the button's mouse events for dragging
        self.util_button.installEventFilter(self)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Header Layout
        #-----------------------------------------------------------------------------------------------------------------------------
        tbw = 12
        tbh = 12
        tbr = 6
        
        self.model_toggle_button = CB.CustomToggleButton(text='1', button_id=0, group_id="widget_stack", bg_color='#5285A6', tooltip="Toggle between modeling and animation tools", border_radius=tbr, width=tbw, height=tbh)
        self.animation_toggle_button = CB.CustomToggleButton(text='2', button_id=1, group_id="widget_stack", bg_color='#5285A6', tooltip="Toggle between modeling and animation tools", border_radius=tbr, width=tbw, height=tbh)
        self.graph_toggle_button = CB.CustomToggleButton(text='3', button_id=2, group_id="widget_stack", bg_color='#5285A6', tooltip="Toggle between modeling and animation tools", border_radius=tbr, width=tbw, height=tbh)
        
        self.close_button = CB.CustomButton(text="✕", width=tbw, height=tbh, color="#ff0000", textColor="rgba(255, 255, 255, 0.9)",text_size=6, tooltip="Close Tool Box", radius=tbr)
        self.close_button.singleClicked.connect(self.close)

        self.body_header_layout.addStretch()
        self.body_header_layout.addWidget(self.model_toggle_button)
        self.body_header_layout.addWidget(self.animation_toggle_button)
        self.body_header_layout.addWidget(self.graph_toggle_button)
        self.body_header_layout.addSpacing(10)
        self.body_header_layout.addWidget(self.close_button)

        # Initially check the first button to show the first widget
        self.model_toggle_button.setChecked(True)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Modeling Widget
        #-----------------------------------------------------------------------------------------------------------------------------
        self.modeling_widget = QtWidgets.QWidget()
        self.modeling_widget.setStyleSheet("background-color: rgba(36, 36, 36, 0);border:none;border-radius: 4px;")
        self.modeling_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        # Initialize with dynamic horizontal priority based on height
        initial_horizontal_priority = self.height() <= 75
        self.modeling_layout = FL.FlowLayout(self.modeling_widget, margin=2, spacing=8, horizontal_priority=initial_horizontal_priority)
        # Create a custom scroll area for the modeling buttons with inverted wheel scrolling (vertical wheel = horizontal scroll)
        self.modeling_scroll_area = CS.CustomScrollArea(invert_primary=True)
        self.modeling_scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # Scrollbars are hidden but scrolling still works through wheel events
        self.modeling_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.modeling_scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)


        self.modeling_scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(100, 100, 100, 0.5);
                min-width: 20px;
                border-radius: 0px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(100, 100, 100, 0.5);
                min-height: 20px;
                border-radius: 0px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                width: 0px;
            }
        """)
        self.modeling_scroll_area.setWidget(self.modeling_widget)
        #-----------------------------------------------------------------------------------------------------------------------------
        reset_transform_button = CB.CustomButton(text='Reset', icon=':delete.png', color='#222222', size=14, tooltip="Resets the object transform to Origin.",
                                                ContextMenu=True, onlyContext=False)
        reset_transform_button.addToMenu("Move", TF.reset_move, icon='delete.png', position=(0,0))
        reset_transform_button.addToMenu("Rotate", TF.reset_rotate, icon='delete.png', position=(1,0))
        reset_transform_button.addToMenu("Scale", TF.reset_scale, icon='delete.png', position=(2,0))
        reset_transform_button.singleClicked.connect(TF.reset_all)
        self.modeling_layout.addWidget(reset_transform_button)
        #-----------------------------------------------------------------------------------------------------------------------------
        store_pos_button = CB.CustomButton(text='Store Pos', color='#16AAA6', tooltip="Store Position: Stores the position of selected Vertices, Edges or Faces. Double Click to make locator visible")
        move_to_pos_button = CB.CustomButton(text='Move to Pos', color='#D58C09', tooltip="Move to Position: Move selected object(s) to the stored position.")

        parent_constraint_button = CB.CustomButton(icon=':parentConstraint.png', flat=True,color='#444444', tooltip="Constraint active object to selected object."
                                                ,ContextMenu=True, onlyContext=True,cmColor='#5285a6', cmHeight=22)
        parent_constraint_button.addToMenu("Parent", TF.parent_constraint , position=(0, 0), icon='parentConstraint.png')
        parent_constraint_button.addToMenu("Offset", TF.parent_constraint_offset, position=(0, 1))

        parent_constraint_button.addToMenu("Point ", TF.point_constraint, position=(1, 0), icon='pointConstraint.svg')
        parent_constraint_button.addToMenu("Offset ", TF.point_constraint_offset, position=(1, 1))

        parent_constraint_button.addToMenu("Orient", TF.orient_constraint, position=(2, 0), icon='orientConstraint.png')
        parent_constraint_button.addToMenu("Offset", TF.orient_constraint_offset, position=(2, 1))

        parent_constraint_button.addToMenu("Scale", TF.scale_constraint, position=(3, 0), icon='scaleConstraint.png')
        parent_constraint_button.addToMenu("Offset", TF.scale_constraint_offset, position=(3, 1))

        parent_constraint_button.addToMenu("Aim", TF.aim_constraint, position=(4, 0), icon='aimConstraint.png')
        parent_constraint_button.addToMenu("Offset", TF.aim_constraint_offset, position=(4, 1))

        parent_constraint_button.addToMenu("Pole Vector", TF.pole_vector_constraint, position=(5, 0),colSpan=2, icon='poleVectorConstraint.png')
        
        adj_grp_tt = '<b>Create Adjustment Group:</b> <br> Single Click: Create offset group for selected objects. <br> Double Click: Select the control object and the joint object to create the adjustment group.'
        self.adjustment_grp_button = CB.CustomButton(text='GRP', color='#112f61', tooltip=adj_grp_tt, ContextMenu=True, cmColor='#226dc0',width=35)
        self.adjustment_grp_button.addToMenu("1 Group", TF.create_single_adjustment_group, position=(0, 0))
        self.adjustment_grp_button.addToMenu("Snap", TF.create_single_adjustment_group_move, position=(0, 1))
        self.adjustment_grp_button.addToMenu("Multi", TF.create_single_adjustment_group_move_multi, position=(0, 2))
        self.adjustment_grp_button.addToMenu("2 Groups", TF.create_double_adjustment_group, position=(1, 0))
        self.adjustment_grp_button.addToMenu("Snap", TF.create_double_adjustment_group_move, position=(1, 1))

        anim_extra = CB.CustomButton(icon=':moreOverlay.png', flat =False, color='#262626', tooltip="More Options.",ContextMenu=True, onlyContext=True,cmColor='#5285a6', cmHeight=22)
        anim_extra.addToMenu("Mute All", TF.mute_all)
        anim_extra.addToMenu("Unmute All", TF.unMute_all)
        anim_extra.addToMenu("Mute Selected", TF.mute_selected)
        anim_extra.addToMenu("Unmute Selected", TF.unMute_selected)
        anim_extra.addToMenu("Break Connections", TF.break_connections,colSpan=2)

        store_pos_button.singleClicked.connect(TF.store_component_position)
        move_to_pos_button.singleClicked.connect(TF.move_objects_to_stored_position)
        parent_constraint_button.singleClicked.connect(TF.parent_constraint)
        parent_constraint_button.doubleClicked.connect(TF.parent_constraint_options)
        self.adjustment_grp_button.singleClicked.connect(TF.create_single_adjustment_group)
        self.adjustment_grp_button.doubleClicked.connect(TF.create_single_adjustment_group_move)

        self.modeling_layout.addWidget(store_pos_button)
        self.modeling_layout.addWidget(move_to_pos_button)
        self.modeling_layout.addWidget(parent_constraint_button)
        self.modeling_layout.addWidget(self.adjustment_grp_button)
        self.modeling_layout.addWidget(anim_extra)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Animation Widget
        #-----------------------------------------------------------------------------------------------------------------------------
        self.animation_widget = QtWidgets.QWidget()
        self.animation_layout = QtWidgets.QVBoxLayout(self.animation_widget)
        self.animation_layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins
        self.animation_layout.setSpacing(2)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Graph Widget
        #-----------------------------------------------------------------------------------------------------------------------------
        self.graph_widget = QtWidgets.QWidget()
        self.graph_layout = QtWidgets.QVBoxLayout(self.graph_widget)
        self.graph_layout.setContentsMargins(2, 2, 2, 2)  # Minimal margins
        self.graph_layout.setSpacing(2)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Stacked Widget
        self.content_widget = QtWidgets.QStackedWidget()
        self.content_widget.setStyleSheet("background-color: rgba(36, 36, 36, 0);border:none;border-radius: 0px;")
        self.content_widget.addWidget(self.modeling_scroll_area)
        self.content_widget.addWidget(self.animation_widget)
        # Add the content widget to the frame layout
        self.frame_layout.addWidget(self.content_widget)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Add the frame to the main layout
        self.body_content_layout.addWidget(self.frame)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Enable mouse tracking for cursor changes during resize
        self.setMouseTracking(True)
        self.frame.setMouseTracking(True)
        self.frame.installEventFilter(self)
        
        # Store the last height to detect changes that cross the threshold
        self.last_height = self.height()
    
    def setup_connections(self):
        self.model_toggle_button.toggled_with_id.connect(self.switch_widget)
        self.animation_toggle_button.toggled_with_id.connect(self.switch_widget)
        self.graph_toggle_button.toggled_with_id.connect(self.switch_widget)
        self.content_widget.setCurrentIndex(self.model_toggle_button.button_id)
        
    def switch_widget(self, checked, button_id):
        if checked:
            self.content_widget.setCurrentIndex(button_id)
    #----------------------------------------------------------------------------------
    # Window event handlers
    #----------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        # Only handle events that occur outside the frame
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
        UT.maya_main_window().activateWindow()
    
    def mouseMoveEvent(self, event):
        # Only handle events that occur outside the frame
        if event.buttons() == QtCore.Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.offset)
    
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
        UT.maya_main_window().activateWindow()
    
    def resizeEvent(self, event):
        """Handle window resize events
        
        This method detects when the window crosses the height threshold of 65 pixels
        and adjusts the modeling layout's horizontal priority accordingly.
        """
        super(ToolBoxWindow, self).resizeEvent(event)
        
        current_height = self.height()
        height_threshold = 75
        
        # Check if we've crossed the threshold in either direction
        was_below_threshold = self.last_height <= height_threshold
        is_below_threshold = current_height <= height_threshold
        
        if was_below_threshold != is_below_threshold:
            # We've crossed the threshold, update the layout
            self.modeling_layout.horizontal_priority = is_below_threshold
            # Force layout update
            self.modeling_widget.updateGeometry()
            self.modeling_scroll_area.updateGeometry()
        
        # Store the current height for next comparison
        self.last_height = current_height
       
    #----------------------------------------------------------------------------------
    # Resize handling methods
    #----------------------------------------------------------------------------------
    def _get_resize_edge_from_frame_pos(self, frame_pos, frame_rect):
        """Determine which resize edge the position is on within the frame
        
        Args:
            frame_pos (QPoint): Position in frame coordinates
            frame_rect (QRect): Rectangle representing the frame boundaries
            
        Returns:
            str or None: The resize edge identifier or None if not on an edge
        """
        # Use a smaller edge size to make resize detection closer to the actual border
        edge_size = 4  # Reduced from self.resize_range to be closer to the border
        
        # Check if we're on the edge of the frame
        is_left = frame_pos.x() <= edge_size
        is_right = frame_pos.x() >= frame_rect.width() - edge_size
        is_top = frame_pos.y() <= edge_size
        is_bottom = frame_pos.y() >= frame_rect.height() - edge_size
        
        if is_top and is_left: return 'top_left'
        if is_top and is_right: return 'top_right'
        if is_bottom and is_left: return 'bottom_left'
        if is_bottom and is_right: return 'bottom_right'
        if is_top: return 'top'
        if is_bottom: return 'bottom'
        if is_left: return 'left'
        if is_right: return 'right'
        return None
    
    def _update_cursor_for_edge(self, edge):
        """Update the cursor based on the resize edge
        
        Args:
            edge (str): The resize edge identifier
        """
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
        self.frame.setCursor(cursor)
        
        # Clear any existing override cursor before setting a new one
        while QtWidgets.QApplication.overrideCursor() is not None:
            QtWidgets.QApplication.restoreOverrideCursor()
            
        # Use application-wide cursor override to ensure it takes effect
        QtWidgets.QApplication.setOverrideCursor(cursor)
    
    def _handle_resize(self, global_pos):
        """Handle window resizing
        
        Args:
            global_pos (QPoint): Current global mouse position
        """
        delta = global_pos - self.resize_start_pos
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
        
    #----------------------------------------------------------------------------------
    # Event filter and handlers
    #----------------------------------------------------------------------------------
    def eventFilter(self, obj, event):
        """Main event filter that dispatches events to specialized handlers
        
        Args:
            obj (QObject): The object that triggered the event
            event (QEvent): The event to process
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        # Handle events for both the frame and the util_button
        if obj != self.frame and obj != self.util_button:
            return super(ToolBoxWindow, self).eventFilter(obj, event)
            
        # Special handling for util_button
        if obj == self.util_button:
            return self._handle_util_button_events(event)
        
        # Frame event handling
        event_type = event.type()
        
        if event_type == QtCore.QEvent.MouseMove:
            if not event.buttons():
                return self._handle_frame_hover(event)
            elif event.buttons() == QtCore.Qt.LeftButton:
                return self._handle_frame_drag_or_resize(event)
        elif event_type == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            return self._handle_frame_mouse_press(event)
        elif event_type == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
            return self._handle_frame_mouse_release(event)
        elif event_type == QtCore.QEvent.Leave:
            return self._handle_frame_mouse_leave(event)
        
        # Let the parent class handle other events
        UT.maya_main_window().activateWindow()
        return super(ToolBoxWindow, self).eventFilter(obj, event)
    
    def _handle_util_button_events(self, event):
        """Handle events specific to the utility button
        
        Args:
            event (QEvent): The event to process
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        event_type = event.type()
        
        if event_type == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            # Start dragging the window when left-click and drag on util_button
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
            return True  
            
        elif event_type == QtCore.QEvent.MouseMove and event.buttons() == QtCore.Qt.LeftButton and self.dragging:
            # Handle dragging
            self.move(event.globalPos() - self.offset)
            return True  # Consume the event
            
        elif event_type == QtCore.QEvent.MouseButtonRelease and event.button() == QtCore.Qt.LeftButton:
            # End dragging
            self.dragging = False
            return False  # Don't consume the event so the button still gets it
            
        return False
    
    def _handle_frame_hover(self, event):
        """Handle mouse hover events over the frame
        
        Args:
            event (QEvent): The event to process
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        if not self.resizing:
            frame_pos = event.pos()
            frame_rect = self.frame.rect()
            
            # Determine which edge (if any) the mouse is over
            old_resize_edge = self.resize_edge  # Store previous edge state
            self.resize_edge = self._get_resize_edge_from_frame_pos(frame_pos, frame_rect)
            
            # Update cursor based on edge, or reset it if we're not on an edge
            if self.resize_edge:
                # Apply resize frame style
                self.frame.setStyleSheet(self.resize_frame_style)
                
                # Set cursor based on the edge
                self._update_cursor_for_edge(self.resize_edge)
            else:
                # Reset to default frame style
                self.frame.setStyleSheet(self.default_frame_style)
                
                # Set default cursor for draggable area
                self.setCursor(QtCore.Qt.ArrowCursor)
                self.frame.setCursor(QtCore.Qt.ArrowCursor)
                
                # Clear all override cursors
                while QtWidgets.QApplication.overrideCursor() is not None:
                    QtWidgets.QApplication.restoreOverrideCursor()
        
        return True
    
    def _handle_frame_drag_or_resize(self, event):
        """Handle mouse drag events for dragging or resizing
        
        Args:
            event (QEvent): The event to process
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        if self.resizing and self.resize_edge:
            # Handle resizing
            self._handle_resize(event.globalPos())
            return True  # Event handled
        elif self.dragging:
            # Handle dragging
            self.move(event.globalPos() - self.offset)
            return True  # Event handled
            
        return False
    
    def _handle_frame_mouse_press(self, event):
        """Handle mouse press events on the frame
        
        Args:
            event (QEvent): The event to process
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        frame_pos = event.pos()
        frame_rect = self.frame.rect()
        
        # Check if we're on a resize edge
        self.resize_edge = self._get_resize_edge_from_frame_pos(frame_pos, frame_rect)
        
        if self.resize_edge:
            # Start resizing
            self.resizing = True
            self.resize_start_pos = event.globalPos()
            self.initial_size = self.size()
            self.initial_pos = self.pos()
        else:
            # Start dragging
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
            
            # Set grab cursor when starting to drag
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self.frame.setCursor(QtCore.Qt.ClosedHandCursor)
            
            # Clear any existing override cursor before setting a new one
            while QtWidgets.QApplication.overrideCursor() is not None:
                QtWidgets.QApplication.restoreOverrideCursor()
                
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.ClosedHandCursor)
            
        return True  # Event handled
    
    def _handle_frame_mouse_release(self, event):
        """Handle mouse release events on the frame
        
        Args:
            event (QEvent): The event to process
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        # Reset states
        was_resizing = self.resizing
        was_dragging = self.dragging
        
        self.resizing = False
        self.dragging = False
        
        # Restore cursor after operation
        if was_resizing:
            # Reset to default frame style
            self.frame.setStyleSheet(self.default_frame_style)
            
            # Reset cursor
            self._reset_cursor()
        elif was_dragging:
            # Reset to default frame style
            self.frame.setStyleSheet(self.default_frame_style)
            
            # Set back to default cursor after dragging
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.frame.setCursor(QtCore.Qt.ArrowCursor)
            
            # Clear all override cursors
            while QtWidgets.QApplication.overrideCursor() is not None:
                QtWidgets.QApplication.restoreOverrideCursor()
        
        if was_resizing or was_dragging:
            return True  # Event handled
            
        return False
    
    def _handle_frame_mouse_leave(self, event):
        """Handle mouse leave events on the frame
        
        Args:
            event (QEvent): The event to process
            
        Returns:
            bool: True if the event was handled, False otherwise
        """
        if not self.resizing:
            # Reset to default frame style
            self.frame.setStyleSheet(self.default_frame_style)
            
            # Reset cursor
            self._reset_cursor()
            
            self.resize_edge = None
        return True  # Event handled
    
    def _reset_cursor(self):
        """Reset cursor to default arrow cursor"""
        # Always reset cursor when not on an edge
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.frame.setCursor(QtCore.Qt.ArrowCursor)
        
        # Clear all override cursors
        while QtWidgets.QApplication.overrideCursor() is not None:
            QtWidgets.QApplication.restoreOverrideCursor()
        
        UT.maya_main_window().activateWindow()
