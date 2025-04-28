import os
from functools import partial
import maya.cmds as cmds
from pathlib import Path
import uuid

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
from . import custom_layout as CL
from . import create_shape as CSP
from . import fade_away_logic as FA
from . import toggle_db

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
        
        # Initialize toggle button database
        self.toggle_db = toggle_db.ToggleButtonDatabase()
        self.toggle_buttons = {}
        self.custom_widgets = {}
        
        self.setup_ui()
        self.setup_connections()

        self.fade_manager = FA.FadeAway(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.fade_manager.show_frame_context_menu)

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
        self.util_button = CB.CustomButton(text="☰",width=20, height=20, radius=3,color="#555555", textColor="#888888", cmHeight=22 ,ContextMenu=True, onlyContext=True, tooltip="Open Util Menu")
        #self.util_button.addToMenu('Close', self.close, icon="closeTabButton.png", position=(0,0))
        self.util_button.addToMenu('Horizontal', self.horizontal_window, icon="loadToolBox.png", position=(0,0))
        self.util_button.addToMenu('Vertical', self.vertical_window, icon="loadToolBox.png", position=(1,0))
        self.util_button.addToMenu('Add Tab', self.add_toggle_button, icon="loadToolBox.png", position=(2,0))
        self.util_button.addToMenu('Remove Tab', self.remove_toggle_button, icon="loadToolBox.png", position=(3,0))
        
        # Track current layout orientation
        self.is_horizontal_layout = True
        self.utility_layout.addSpacing(10)
        self.utility_layout.addWidget(self.util_button)
        
        # Connect to the button's mouse events for dragging
        self.util_button.installEventFilter(self)
        initial_horizontal_priority = self.height() <= 75
        #-----------------------------------------------------------------------------------------------------------------------------
        # Header Layout
        #-----------------------------------------------------------------------------------------------------------------------------
        tbw = 12
        tbh = 12
        tbr = 6
        
        # Create toggle buttons from database
        self.create_toggle_buttons(tbw, tbh, tbr)
        
        self.close_button = CB.CustomButton(text="✕", width=tbw, height=tbh, color="#ff0000", textColor="rgba(255, 255, 255, 0.9)",text_size=6, tooltip="Close Tool Box", radius=tbr)
        self.close_button.singleClicked.connect(self.close)

        self.body_header_layout.addStretch()
        
        # Add toggle buttons to layout
        for button_id in sorted(self.toggle_buttons.keys()):
            self.body_header_layout.addWidget(self.toggle_buttons[button_id])
            
        self.body_header_layout.addSpacing(10)
        self.body_header_layout.addWidget(self.close_button)

        # Initially check the first button to show the first widget
        if 0 in self.toggle_buttons:
            self.toggle_buttons[0].setChecked(True)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Scrollbar style
        def apply_transparent_scroll_style(widget):
            widget.setStyleSheet("""
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
        
        def mrs(col):
            self.reset_transform_button = CB.CustomButton(text='Reset', icon=':delete.png', color='#222222', size=14, tooltip="Resets the object transform to Origin.",
                                                ContextMenu=True, onlyContext=True,cmColor='#444444',cmHeight=22)
            self.reset_transform_button.addToMenu("All", TF.reset_all, icon='delete.png', position=(0,0))
            self.reset_transform_button.addToMenu("Move", TF.reset_move, icon='delete.png', position=(1,0))
            self.reset_transform_button.addToMenu("Rotate", TF.reset_rotate, icon='delete.png', position=(2,0))
            self.reset_transform_button.addToMenu("Scale", TF.reset_scale, icon='delete.png', position=(3,0))
            
            self.reset_transform_button.doubleClicked.connect(TF.reset_all)
            col.addWidget(self.reset_transform_button)
            return col
        #-----------------------------------------------------------------------------------------------------------------------------
        # Modeling Widget
        #-----------------------------------------------------------------------------------------------------------------------------
        self.modeling_widget = QtWidgets.QWidget()
        self.modeling_widget.setStyleSheet("background-color: rgba(36, 36, 36, 0);border:none;border-radius: 4px;")
        self.modeling_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        # Initialize with dynamic horizontal priority based on height
        
        self.modeling_layout = QtWidgets.QHBoxLayout(self.modeling_widget)
        self.modeling_layout.setSpacing(4)
        self.modeling_layout.setContentsMargins(0, 0, 0, 0)
        self.modeling_layout.setAlignment(QtCore.Qt.AlignCenter)

        self.modeling_layout_01 = QtWidgets.QHBoxLayout(self.modeling_widget)
        self.modeling_layout_01.setSpacing(4)
        self.modeling_layout_01.setContentsMargins(0, 0, 0, 0)
        self.modeling_layout.addLayout(self.modeling_layout_01)
        self.modeling_layout_01.setAlignment(QtCore.Qt.AlignCenter)

        self.modeling_layout_02 = CL.CustomGridLayout(rows=1, cols=0)  
        self.modeling_layout.addLayout(self.modeling_layout_02)
        #self.modeling_layout_02.setAlignment(QtCore.Qt.AlignCenter)

        # Use a custom grid layout for the third row of buttons to support both horizontal and grid patterns
        self.modeling_layout_03 = CL.CustomGridLayout(rows=1, cols=0)  
        self.modeling_layout.addLayout(self.modeling_layout_03)
        #self.modeling_layout_03.setAlignment(QtCore.Qt.AlignCenter)

        self.modeling_layout_04 = CL.CustomGridLayout(rows=1, cols=0)  
        self.modeling_layout.addLayout(self.modeling_layout_04)
        
        # Create a custom scroll area for the modeling buttons with inverted wheel scrolling (vertical wheel = horizontal scroll)
        self.modeling_scroll_area = CS.CustomScrollArea(invert_primary=True)
        self.modeling_scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # Scrollbars are hidden but scrolling still works through wheel events
        self.modeling_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.modeling_scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        apply_transparent_scroll_style(self.modeling_scroll_area)
        self.modeling_scroll_area.setWidget(self.modeling_widget)
        #-----------------------------------------------------------------------------------------------------------------------------
        mrs(self.modeling_layout_01)
        self.store_pos_button = CB.CustomButton(text='Store Pos', color='#16AAA6', tooltip="Store Position: Stores the position of selected Vertices, Edges or Faces. Double Click to make locator visible")
        self.move_to_pos_button = CB.CustomButton(text='Move to Pos', color='#D58C09', tooltip="Move to Position: Move selected object(s) to the stored position.")

        self.parent_constraint_button = CB.CustomButton(icon=':parentConstraint.png', text='Constraints', size=16, color='#262626', tooltip="Constraint active object to selected object."
                                                ,ContextMenu=True, onlyContext=True,cmColor='#444444', cmHeight=22)
        self.parent_constraint_button.addToMenu("Parent", TF.parent_constraint , position=(0, 0), icon='parentConstraint.png')
        self.parent_constraint_button.addToMenu("Offset", TF.parent_constraint_offset, position=(0, 1))

        self.parent_constraint_button.addToMenu("Point ", TF.point_constraint, position=(1, 0), icon='pointConstraint.svg')
        self.parent_constraint_button.addToMenu("Offset ", TF.point_constraint_offset, position=(1, 1))

        self.parent_constraint_button.addToMenu("Orient", TF.orient_constraint, position=(2, 0), icon='orientConstraint.png')
        self.parent_constraint_button.addToMenu("Offset", TF.orient_constraint_offset, position=(2, 1))

        self.parent_constraint_button.addToMenu("Scale", TF.scale_constraint, position=(3, 0), icon='scaleConstraint.png')
        self.parent_constraint_button.addToMenu("Offset", TF.scale_constraint_offset, position=(3, 1))

        self.parent_constraint_button.addToMenu("Aim", TF.aim_constraint, position=(4, 0), icon='aimConstraint.png')
        self.parent_constraint_button.addToMenu("Offset", TF.aim_constraint_offset, position=(4, 1))

        self.parent_constraint_button.addToMenu("Pole Vector", TF.pole_vector_constraint, position=(5, 0),colSpan=2, icon='poleVectorConstraint.png')
        
        adj_grp_tt = '<b>Create Adjustment Group:</b> <br> Single Click: Create offset group for selected objects. <br> Double Click: Select the control object and the joint object to create the adjustment group.'
        self.adjustment_grp_button = CB.CustomButton(text='Groups', color='#1a5697', tooltip=adj_grp_tt, ContextMenu=True, cmColor='#226dc0')
        self.adjustment_grp_button.addToMenu("1 Group", TF.create_single_adjustment_group, position=(0, 0))
        self.adjustment_grp_button.addToMenu("Snap", TF.create_single_adjustment_group_move, position=(0, 1))
        self.adjustment_grp_button.addToMenu("Multi", TF.create_single_adjustment_group_move_multi, position=(0, 2))
        self.adjustment_grp_button.addToMenu("2 Groups", TF.create_double_adjustment_group, position=(1, 0))
        self.adjustment_grp_button.addToMenu("Snap", TF.create_double_adjustment_group_move, position=(1, 1))

        self.anim_extra = CB.CustomButton(icon=':moreOverlay.png', flat =False, color='#262626', tooltip="More Options.",ContextMenu=True, onlyContext=True,cmColor='#5285a6', cmHeight=22)
        self.anim_extra.addToMenu("Mute All", TF.mute_all)
        self.anim_extra.addToMenu("Unmute All", TF.unMute_all)
        self.anim_extra.addToMenu("Mute Selected", TF.mute_selected)
        self.anim_extra.addToMenu("Unmute Selected", TF.unMute_selected)
        self.anim_extra.addToMenu("Break Connections", TF.break_connections,colSpan=2)

        self.centerPivot_button = CB.CustomButton(icon=':CenterPivot.png',color='#333333', tooltip="Resets the selected object(s) pivot to the center.")
        self.deleteHistory_button = CB.CustomButton(icon=':DeleteHistory.png',color='#333333', tooltip="Delete construction history on selected object(s).")
        self.freezeTransform_button = CB.CustomButton(icon=':FreezeTransform.png', color='#333333', tooltip="Changes curent transform values to base transform values.",ContextMenu=True)
        self.freezeTransform_button.addToMenu("Freeze Translate", TF.freeze_translate, position=(0, 0))
        self.freezeTransform_button.addToMenu("Freeze Rotate", TF.freeze_rotate, position=(1, 0))
        self.freezeTransform_button.addToMenu("Freeze Scale", TF.freeze_scale, position=(2, 0))
        self.object_to_world_button = CB.CustomButton(icon=':absolute.png', color='#9c6bce', size=22, tooltip="Object to world Origin: Moves object to world origin.")

        self.active_to_selected_button = CB.CustomButton(icon=':absolute.png', color='#C41B16', size=22, tooltip="Snap to Active Object: Moves selected object(s) to Active Objects Position.",ContextMenu=True)
        self.active_to_selected_button.addToMenu("Move", TF.match_move, position=(0, 0))
        self.active_to_selected_button.addToMenu("Rotate", TF.match_rotate, position=(1, 0))
        self.active_to_selected_button.addToMenu("Scale", TF.match_scale, position=(2, 0))
        self.active_to_selected_button.addToMenu("All", TF.match_all, position=(3, 0))
        
        self.pivot_to_world_button = CB.CustomButton(icon=':absolute.png', color='#049E9F', size=22, tooltip="Pivot to Stored Position: Moves the object(s) Stored Position.")

        pivot_to_selected_button_tt = "Selected Pivot to Active Pivot: Moves the pivot of selected object(s) to the pivot of active objects(s)."
        self.pivot_to_selected_button = CB.CustomButton(icon=':absolute.png', color='#6C9809', size=22, tooltip=pivot_to_selected_button_tt,ContextMenu=True)
        self.pivot_to_selected_button.addToMenu("Position", TF.selected_pivot_to_active_pivot_pos, position=(0, 0))
        self.pivot_to_selected_button.addToMenu("Orientation", TF.selected_pivot_to_active_pivot_ori, position=(0, 1))
        self.pivot_to_selected_button.addToMenu("All", TF.selected_pivot_to_active_pivot_all, position=(0, 2))
        self.pivot_to_selected_button.addToMenu("Copy Joint Pivot", TF.copy_joint_pivot,colSpan=3)

        self.create_shape_button = CB.CustomButton(text='Create Shape', color='#262626', tooltip="Create Shape: Creates a shape based on the selected object(s).",ContextMenu=True, onlyContext=True)
        self.create_shape_button.addToMenu("Circle", CSP.circle_sc, position=(0, 0))
        self.create_shape_button.addToMenu("Square", CSP.square_sc, position=(1, 0))
        self.create_shape_button.addToMenu("Cube", CSP.cube_sc, position=(2, 0))
        self.create_shape_button.addToMenu("Triangle", CSP.triangle_sc, position=(3, 0))
        self.create_shape_button.addToMenu("Pyramid", CSP.pyramid_sc, position=(4, 0))
        self.create_shape_button.addToMenu("Arrow", CSP.arrow_sc, position=(5, 0))
        self.create_shape_button.addToMenu("Cycle", CSP.cycle_sc, position=(6, 0))
        #self.color_override_button = CB.CustomButton(text='Color', color='#262626', tooltip="Override Color: Overrides the color of the selected object(s).")
        self.color_override_button = CB.ColorPickerButton()
        
        #-----------------------------------------------------------------------------------------------------------------------------
        self.store_pos_button.singleClicked.connect(TF.store_component_position)
        self.move_to_pos_button.singleClicked.connect(TF.move_objects_to_stored_position)
        self.parent_constraint_button.singleClicked.connect(TF.parent_constraint)
        self.parent_constraint_button.doubleClicked.connect(TF.parent_constraint_options)
        self.adjustment_grp_button.singleClicked.connect(TF.create_single_adjustment_group)
        self.adjustment_grp_button.doubleClicked.connect(TF.create_single_adjustment_group_move)

        self.centerPivot_button.singleClicked.connect(TF.center_pivot)
        self.deleteHistory_button.singleClicked.connect(TF.delete_history)
        self.freezeTransform_button.singleClicked.connect(TF.freeze_transformation)
        self.object_to_world_button.singleClicked.connect(TF.object_to_world_origin)
        self.active_to_selected_button.singleClicked.connect(TF.object_to_active_position)
        self.pivot_to_world_button.singleClicked.connect(TF.pivot_to_world_origin)
        self.pivot_to_selected_button.singleClicked.connect(TF.selected_pivot_to_active_pivot_pos)
        self.pivot_to_selected_button.doubleClicked.connect(TF.selected_pivot_to_active_pivot_ori)

        #self.color_override_button.singleClicked.connect(lambda: CB.ColorPickerMenu().show_color_menu(self.color_override_button))
        
        #-----------------------------------------------------------------------------------------------------------------------------
        self.modeling_layout_02.addWidget(self.store_pos_button)
        self.modeling_layout_02.addWidget(self.move_to_pos_button)
        self.modeling_layout_02.addWidget(self.parent_constraint_button)
        self.modeling_layout_02.addWidget(self.adjustment_grp_button)
        
        #self.modeling_layout_02.addSpacing(10)

        # Add buttons to grid in horizontal pattern (all in one row)
        self.modeling_layout_03.addWidget(self.centerPivot_button)
        self.modeling_layout_03.addWidget(self.deleteHistory_button)
        self.modeling_layout_03.addWidget(self.freezeTransform_button)
        self.modeling_layout_03.addWidget(self.anim_extra)
        self.modeling_layout_03.addWidget(self.active_to_selected_button)
        self.modeling_layout_03.addWidget(self.pivot_to_world_button)
        self.modeling_layout_03.addWidget(self.pivot_to_selected_button)
        self.modeling_layout_03.addWidget(self.object_to_world_button)

        self.modeling_layout_04.addWidget(self.create_shape_button)
        self.modeling_layout_04.addWidget(self.color_override_button)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Animation Widget
        #-----------------------------------------------------------------------------------------------------------------------------
        self.animation_widget = QtWidgets.QWidget()
        self.animation_widget.setStyleSheet("background-color: rgba(36, 36, 36, 0);border:none;border-radius: 4px;")

        self.animation_layout = QtWidgets.QHBoxLayout(self.animation_widget)
        self.animation_layout.setSpacing(4)
        self.animation_layout.setContentsMargins(0, 0, 0, 0)

        self.animation_scroll_area = CS.CustomScrollArea(invert_primary=True)
        self.animation_scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # Scrollbars are hidden but scrolling still works through wheel events
        self.animation_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.animation_scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        apply_transparent_scroll_style(self.animation_scroll_area)
        self.animation_scroll_area.setWidget(self.animation_widget)
        #-----------------------------------------------------------------------------------------------------------------------------
        mrs(self.animation_layout)

        self.key_frame_button = CB.CustomButton(text='Key', color='#d62e22', tooltip="Sets key frame.")
        self.key_breakdown_button = CB.CustomButton(text='Key', color='#3fb07f', tooltip="Sets breakdown frame.")
        
        self.copy_key_button = CB.CustomButton(text='Copy', color='#293F64', tooltip="Copy selected key(s).")
        self.paste_key_button = CB.CustomButton(text='Paste', color='#1699CA', tooltip="Paste copied key(s).")
        self.paste_inverse_key_button = CB.CustomButton(text='Paste Inverse', color='#9416CA', tooltip="Paste Inverted copied keys(s).")
        self.remove_inbetween_button = CB.CustomButton(text='<', color='#496d88', width=24, tooltip="Remove Inbetween at current time.")
        self.add_inbetween_button = CB.CustomButton(text='>', color='#496d88', width=24, tooltip="Add Inbetween at current time.")
        self.delete_key_button = CB.CustomButton(text='Delete Key', color='#A00000', size=16, tooltip="Deletes keys from the given start frame to the current frame.")
        
        self.animation_layout.addWidget(self.key_frame_button)
        self.animation_layout.addWidget(self.key_breakdown_button)
        self.animation_layout.addWidget(self.copy_key_button)
        self.animation_layout.addWidget(self.paste_key_button)
        self.animation_layout.addWidget(self.paste_inverse_key_button)
        self.animation_layout.addWidget(self.remove_inbetween_button)
        self.animation_layout.addWidget(self.add_inbetween_button)
        self.animation_layout.addWidget(self.delete_key_button)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Graph Widget
        #-----------------------------------------------------------------------------------------------------------------------------
        self.graph_widget = QtWidgets.QWidget()
        self.graph_widget.setStyleSheet("background-color: rgba(36, 36, 36, 0);border:none;border-radius: 4px;")
        self.graph_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.graph_layout = QtWidgets.QHBoxLayout(self.graph_widget)
        self.graph_layout.setSpacing(4)
        self.graph_layout.setContentsMargins(0, 0, 0, 0)

        self.graph_scroll_area = CS.CustomScrollArea(invert_primary=True)
        self.graph_scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        apply_transparent_scroll_style(self.graph_scroll_area)
        self.graph_scroll_area.setWidget(self.graph_widget)
        #-----------------------------------------------------------------------------------------------------------------------------
        mrs(self.graph_layout)
        #-----------------------------------------------------------------------------------------------------------------------------
        # Stacked Widget
        self.content_widget = QtWidgets.QStackedWidget()
        self.content_widget.setStyleSheet("background-color: rgba(36, 36, 36, 0);border:none;border-radius: 0px;")
        
        # Store references to default widgets
        self.custom_widgets["modeling_scroll_area"] = self.modeling_scroll_area
        self.custom_widgets["animation_scroll_area"] = self.animation_scroll_area
        self.custom_widgets["graph_scroll_area"] = self.graph_scroll_area
        
        # Add widgets to stacked widget based on database order
        self.update_content_widget()
        
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
        # Connect all toggle buttons to switch_widget
        for button_id, button in self.toggle_buttons.items():
            button.toggled_with_id.connect(self.switch_widget)
        
        # Set initial content widget
        if self.toggle_buttons and 0 in self.toggle_buttons:
            self.content_widget.setCurrentIndex(0)
        
    def switch_widget(self, checked, button_id):
        """Switch the current widget based on the toggle button ID"""
        if checked:
            self.content_widget.setCurrentIndex(button_id)
    
    def clear_layout(self, layout):
        """Remove all widgets from the given layout."""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                layout.removeWidget(item.widget())
        return layout
    
    def horizontal_window(self):
        cursor_position = QtGui.QCursor.pos()
        window_width = 300
        window_height = 70
        x = cursor_position.x() - (window_width +50)
        y = cursor_position.y() - (window_height // 2)
        self.setGeometry(x, y, window_width, window_height)
        self.last_height = window_height
        UT.maya_main_window().activateWindow()

        # Set all layouts to horizontal direction
        self.modeling_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
        self.modeling_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.modeling_layout_01.setDirection(QtWidgets.QBoxLayout.LeftToRight)
        self.animation_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
        self.graph_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
        
        # Rearrange grid to horizontal pattern (all in one row)
        
        # Configure grid layouts for horizontal arrangement
        self.modeling_layout_02.grid(1, 0)  
        self.modeling_layout_03.grid(1, 0)  
        self.modeling_layout_04.grid(1, 0)  
        
        # Clear existing layouts
        self.modeling_layout_02.clear()
        self.modeling_layout_03.clear()
        self.modeling_layout_04.clear()
                
        # Add widgets to the layouts - positions are automatically calculated
        self.modeling_layout_02.addWidget(self.store_pos_button)
        self.modeling_layout_02.addWidget(self.move_to_pos_button)
        self.modeling_layout_02.addWidget(self.parent_constraint_button)
        self.modeling_layout_02.addWidget(self.adjustment_grp_button)
        

        self.modeling_layout_03.addWidget(self.centerPivot_button)
        self.modeling_layout_03.addWidget(self.deleteHistory_button)
        self.modeling_layout_03.addWidget(self.freezeTransform_button)
        self.modeling_layout_03.addWidget(self.anim_extra)
        self.modeling_layout_03.addWidget(self.active_to_selected_button)
        self.modeling_layout_03.addWidget(self.pivot_to_world_button)
        self.modeling_layout_03.addWidget(self.pivot_to_selected_button)
        self.modeling_layout_03.addWidget(self.object_to_world_button)
        
        self.modeling_layout_04.addWidget(self.create_shape_button)
        self.modeling_layout_04.addWidget(self.color_override_button)
        # Force layout update
        self.modeling_widget.updateGeometry()
        self.modeling_scroll_area.updateGeometry()
        self.animation_widget.updateGeometry()
        self.animation_scroll_area.updateGeometry()
        self.graph_widget.updateGeometry()
        self.graph_scroll_area.updateGeometry()
        
    def vertical_window(self):
        cursor_position = QtGui.QCursor.pos()
        window_width = 165
        window_height = 300
        x = cursor_position.x() - (window_width +50)
        y = cursor_position.y() - (window_height // 2)
        self.setGeometry(x, y, window_width, window_height)
        self.last_height = window_height
        UT.maya_main_window().activateWindow()

        # Set layouts to vertical direction
        self.modeling_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        self.modeling_layout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        self.modeling_layout_01.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        self.animation_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        self.graph_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
        
        # Rearrange grid to vertical pattern
        
        # Configure grid layouts for vertical arrangement
        self.modeling_layout_02.grid(0, 1)  # 5 rows, 1 column
        self.modeling_layout_03.grid(0, 4)  # 2 rows, 4 columns
        self.modeling_layout_04.grid(0, 1)  # 2 rows, 4 columns
        
        # Clear existing layouts
        self.modeling_layout_02.clear()
        self.modeling_layout_03.clear()
        self.modeling_layout_04.clear()
        
        # Add widgets to the layouts - positions are automatically calculated
        self.modeling_layout_02.addWidget(self.store_pos_button)
        self.modeling_layout_02.addWidget(self.move_to_pos_button)
        self.modeling_layout_02.addWidget(self.parent_constraint_button)
        self.modeling_layout_02.addWidget(self.adjustment_grp_button)
        
        self.modeling_layout_03.addWidget(self.centerPivot_button)
        self.modeling_layout_03.addWidget(self.deleteHistory_button)
        self.modeling_layout_03.addWidget(self.freezeTransform_button)
        self.modeling_layout_03.addWidget(self.anim_extra)
        self.modeling_layout_03.addWidget(self.active_to_selected_button)
        self.modeling_layout_03.addWidget(self.pivot_to_world_button)
        self.modeling_layout_03.addWidget(self.pivot_to_selected_button)
        self.modeling_layout_03.addWidget(self.object_to_world_button)
        
        self.modeling_layout_04.addWidget(self.create_shape_button)
        self.modeling_layout_04.addWidget(self.color_override_button)

        # Force layout update
        self.modeling_widget.updateGeometry()
        self.modeling_scroll_area.updateGeometry()
        self.animation_widget.updateGeometry()
        self.animation_scroll_area.updateGeometry()
        self.graph_widget.updateGeometry()
        self.graph_scroll_area.updateGeometry()
    
    #----------------------------------------------------------------------------------
    # Window event handlers
    #----------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        # Only handle events that occur outside the frame
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
            event.accept()

        UT.maya_main_window().activateWindow()
    
    def mouseMoveEvent(self, event):
        # Only handle events that occur outside the frame
        if event.buttons() == QtCore.Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.offset)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
            event.accept()
        UT.maya_main_window().activateWindow()
    
    def resizeEvent(self, event):
        """Handle window resize events
        
        This method detects when the window crosses the height threshold of 65 pixels
        and adjusts the modeling layout's horizontal priority accordingly.
        It also updates function button layouts based on window orientation.
        """
        current_height = self.height()
        current_width = self.width()
        is_horizontal = current_width > current_height
        
        # Check if we've crossed the threshold (65 pixels)
        if hasattr(self, 'last_height'):
            was_below_threshold = self.last_height < 65
            is_below_threshold = current_height < 65
            
            if was_below_threshold != is_below_threshold:
                # We've crossed the threshold, update the layout
                self.modeling_layout.horizontal_priority = is_below_threshold
                self.animation_layout.horizontal_priority = is_below_threshold
                self.graph_layout.horizontal_priority = is_below_threshold
                # Force layout update
                self.modeling_widget.updateGeometry()
                self.modeling_scroll_area.updateGeometry()
                self.animation_widget.updateGeometry()
                self.animation_scroll_area.updateGeometry()
                self.graph_widget.updateGeometry()
                self.graph_scroll_area.updateGeometry()
        
        # Check if orientation has changed and update function button layouts
        if hasattr(self, 'last_orientation') and self.last_orientation != is_horizontal:
            self.update_function_button_layouts(is_horizontal)
        
        # Store current values for next comparison
        self.last_height = current_height
        self.last_orientation = is_horizontal 
    
    def closeEvent(self, event):
        """Override closeEvent to properly clean up Maya window reference"""
        # Save the database before closing to ensure all changes are saved
        self.toggle_db.save_database()
        
        # Delete the window from Maya's window list if it exists
        window_name = self.objectName()
        if window_name and cmds.window(window_name, exists=True):
            cmds.deleteUI(window_name, window=True)
    
    #----------------------------------------------------------------------------------
    # Function Button System
    #----------------------------------------------------------------------------------
    def add_function_button(self, tab_id, text="Function", script="", color="#5285A6"):
        """Add a function button to a custom tab"""
        # Get the content widget for this tab
        widget_name = None
        for tab in self.toggle_db.get_toggle_buttons():
            if tab["id"] == tab_id:
                widget_name = tab["widget_name"]
                break
        
        if not widget_name or widget_name not in self.custom_widgets:
            print(f"Error: Could not find widget for tab ID {tab_id}")
            return
        
        # Get the content widget from the scroll area
        scroll_area = self.custom_widgets[widget_name]
        content_widget = scroll_area.widget()
        
        if not hasattr(content_widget, "button_layout"):
            print(f"Error: Content widget does not have a button layout")
            return
        
        # Get the next available function button ID
        button_id = self.toggle_db.get_next_function_id()
        
        # Create button data
        button_data = {
            "id": button_id,
            "tab_id": tab_id,
            "text": text,
            "script": script,
            "script_type": "python",
            "color": color
        }
        
        # Add to database
        self.toggle_db.add_function_button(button_data)
        
        # Create the button
        self._create_function_button(content_widget, button_data)
        
        # Open the script manager to edit the script
        '''from . import script_manager
        script_widget = script_manager.ScriptManagerWidget(self)
        script_widget.set_current_button_data(button_data)
        script_widget.script_updated.connect(self.update_button_script)
        script_widget.show()
        
        # Position the script manager near the button
        pos = QtGui.QCursor.pos()
        script_widget.move(pos.x() + 20, pos.y())'''
    
    def _create_function_button(self, content_widget, button_data):
        """Create a function button and add it to the content widget"""
        # Create the button
        button = CB.CustomFunctionButton(
            text=button_data["text"],
            button_id=button_data["id"],
            script=button_data["script"],
            color=button_data["color"],
            parent=content_widget
        )
        
        if "script_type" in button_data:
            button.script_type = button_data["script_type"]
            
        # Connect signals
        button.script_manager_requested.connect(self.open_script_manager_for_button_id)
        button.delete_requested.connect(self.remove_function_button)
        button.renamed.connect(self.update_function_button_name)
        button.color_changed.connect(self.update_function_button_color)
        
        # Get the button layout
        button_layout = content_widget.button_layout
        
        # Simply add the button to the layout - QHBoxLayout/QVBoxLayout handle positioning automatically
        button_layout.addWidget(button)
    
    def load_function_buttons(self, tab_id, content_widget):
        """Load function buttons for a specific tab"""
        # Get function buttons for this tab
        buttons = self.toggle_db.get_function_buttons_for_tab(tab_id)
        
        # Create buttons
        for button_data in buttons:
            self._create_function_button(content_widget, button_data)
    
    def remove_function_button(self, button_id):
        """Remove a function button"""
        # Remove from database
        self.toggle_db.remove_function_button(button_id)
        # Save the database to ensure changes are persisted
        self.toggle_db.save_database()
        
        # Find and remove the button from UI
        # (The button will remove itself from the layout when deleted)
        
    def open_script_manager_for_button_id(self, button_id):
        """Open script manager for an existing function button"""
        # Get the button data from the database
        button_data = None
        for btn in self.toggle_db.get_function_buttons():
            if btn["id"] == button_id:
                button_data = btn
                break
        
        if button_data:
            # Open the script manager
            from . import script_manager
            script_widget = script_manager.ScriptManagerWidget(self)
            script_widget.set_current_button_data(button_data)
            script_widget.script_updated.connect(self.update_button_script)
            script_widget.show()
            
            # Position the script manager near the cursor
            pos = QtGui.QCursor.pos()
            script_widget.move(pos.x() + 20, pos.y())
    
    def update_button_script(self, button_data):
        """Update a function button's script and save to the database"""
        # Update the database
        self.toggle_db.update_function_button(button_data)
        # Save the database to ensure changes are persisted
        self.toggle_db.save_database()
        
        # Find the button in the UI and update its script
        button_id = button_data["id"]
        tab_id = button_data["tab_id"]
        
        # Find the button and update only its script
        button = self._find_function_button(button_id, tab_id)
        if button:
            button.set_script(button_data["script"], button_data.get("script_type", "python"))
            
    def _find_function_button(self, button_id, tab_id=None):
        """Helper method to find a function button by ID"""
        # If tab_id is not provided, search all tabs
        tabs_to_search = [tab for tab in self.toggle_db.get_toggle_buttons() 
                         if tab_id is None or tab["id"] == tab_id]
        
        for tab in tabs_to_search:
            widget_name = tab["widget_name"]
            if widget_name in self.custom_widgets:
                content_widget = self.custom_widgets[widget_name].widget()
                
                # Find the button in the layout
                if hasattr(content_widget, "button_layout"):
                    layout = content_widget.button_layout
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget() and isinstance(item.widget(), CB.CustomFunctionButton):
                            if item.widget().button_id == button_id:
                                return item.widget()
        return None
    
    def update_function_button_name(self, button_id, new_name):
        """Update a function button's name in the database and UI"""
        # Update database
        updated = False
        for tab in self.toggle_db.get_toggle_buttons():
            if "buttons" in tab:
                for button in tab["buttons"]:
                    if button["id"] == button_id:
                        button["text"] = new_name
                        updated = True
                        break
                if updated:
                    break
                    
        if updated:
            self.toggle_db.save_database()
            
        # No need to update UI since the signal is emitted by the button itself
        # which already updated its text
                        
    def update_function_button_color(self, button_id, new_color):
        """Update a function button's color in the database and UI"""
        # Update database
        updated = False
        for tab in self.toggle_db.get_toggle_buttons():
            if "buttons" in tab:
                for button in tab["buttons"]:
                    if button["id"] == button_id:
                        button["color"] = new_color
                        updated = True
                        break
                if updated:
                    break
                    
        if updated:
            self.toggle_db.save_database()
            
        # No need to update UI since the signal is emitted by the button itself
        # which already updated its color
    
    def update_function_button_layouts(self, is_horizontal):
        """Update function button layouts based on window orientation"""
        # Loop through all custom tabs
        for tab in self.toggle_db.get_toggle_buttons():
            # Skip default tabs
            if tab["id"] <= 2:
                continue
                
            widget_name = tab["widget_name"]
            if widget_name not in self.custom_widgets:
                continue
                
            scroll_area = self.custom_widgets[widget_name]
            content_widget = scroll_area.widget()
            
            if not hasattr(content_widget, "button_layout") or not hasattr(content_widget, "is_horizontal"):
                continue
                
            # Skip if orientation hasn't changed
            if content_widget.is_horizontal == is_horizontal:
                continue
                
            # Update orientation flag
            content_widget.is_horizontal = is_horizontal
            
            # Get all buttons from the current layout
            old_layout = content_widget.button_layout
            buttons = []
            for i in range(old_layout.count()):
                item = old_layout.itemAt(i)
                if item and item.widget():
                    buttons.append(item.widget())
            
            # Remove old layout from main layout
            main_layout = content_widget.layout()
            if main_layout and old_layout:
                main_layout.removeItem(old_layout)
                
                # Delete old layout by reparenting its widgets
                while old_layout.count():
                    item = old_layout.takeAt(0)
                    if item.widget():
                        item.widget().setParent(None)
            
            # Create new layout based on orientation
            if is_horizontal:
                new_layout = QtWidgets.QHBoxLayout()
            else:
                new_layout = QtWidgets.QVBoxLayout()
                
            new_layout.setContentsMargins(0, 0, 0, 0)
            new_layout.setSpacing(4)
            new_layout.setAlignment(QtCore.Qt.AlignCenter)
            
            # Add all buttons to the new layout
            for button in buttons:
                new_layout.addWidget(button)
            
            # Add the new layout to the main layout
            if main_layout:
                main_layout.addLayout(new_layout)
            
            # Update the reference to the button layout
            content_widget.button_layout = new_layout
    #----------------------------------------------------------------------------------
    # Tab System
    #----------------------------------------------------------------------------------  
    def create_toggle_buttons(self, width, height, border_radius):
        """Create toggle buttons from the database"""
        # Clear existing toggle buttons
        self.toggle_buttons = {}
        
        # Create toggle buttons from database
        for button_data in self.toggle_db.get_toggle_buttons():
            button_id = button_data["id"]
            
            # Use the button's stored border radius if available, otherwise use default
            button_border_radius = button_data.get("border_radius", border_radius)
            
            button = CB.CustomToggleButton(
                text=button_data["text"],
                button_id=button_id,
                group_id="widget_stack",
                checked_color=button_data["checked_color"],
                unchecked_color=button_data["unchecked_color"],
                hover_color=button_data["hover_color"],
                tooltip=button_data["tooltip"],
                border_radius=button_border_radius,
                width=width,
                height=height
            )
            self.toggle_buttons[button_id] = button
    
    def update_content_widget(self):
        """Update the content widget with widgets from the database"""
        # Clear the stacked widget
        while self.content_widget.count() > 0:
            self.content_widget.removeWidget(self.content_widget.widget(0))
        
        # Add widgets in the order defined by the database
        for tab in sorted(self.toggle_db.get_toggle_buttons(), key=lambda x: x["id"]):
            widget_name = tab["widget_name"]
            button_id = tab["id"]
            
            # Check if this is a default widget or a custom widget
            if widget_name in ["modeling_scroll_area", "animation_scroll_area", "graph_scroll_area"]:
                # Default widget - should already be in self.custom_widgets
                if widget_name in self.custom_widgets:
                    index = self.content_widget.addWidget(self.custom_widgets[widget_name])
            else:
                # Custom widget - might need to be recreated
                if widget_name not in self.custom_widgets:
                    # Create a default empty widget for custom tabs
                    self._create_empty_widget(button_id, widget_name)
                
                # Add the widget to the stacked widget
                index = self.content_widget.addWidget(self.custom_widgets[widget_name])
                
            # Verify that the index matches the button_id
            if index != button_id:
                print(f"Warning: Widget index {index} does not match button_id {button_id}")
    
    def add_toggle_button(self, text=None, tooltip= 'Custom Tab', checked_color="#84bf4d", unchecked_color="#798b61", 
                         hover_color="#84bf4d", widget=None, widget_name=None, border_radius=2):
        """Add a new toggle button to the body_header_layout"""
        # Get next available ID
        button_id = self.toggle_db.get_next_id()
        
        # Auto-generate text if not provided (use sequential numbering: 4, 5, 6, etc.)
        if text is None:
            text = str(button_id + 1)  # +1 because IDs start at 0 but we want to display starting from 1
        
        # Create button data
        button_data = {
            "id": button_id,
            "text": text,
            "tooltip": tooltip,
            "checked_color": checked_color,
            "unchecked_color": unchecked_color,
            "hover_color": hover_color,
            "widget_name": widget_name or f"custom_widget_{button_id}",
            "border_radius": border_radius,
            "buttons": []  # Initialize with empty buttons array
        }
        
        # Add to database
        self.toggle_db.add_toggle_button(button_data)
        
        # Create button
        tbw = 12
        tbh = 12
        tbr = 6
        button = CB.CustomToggleButton(
            text=text,
            button_id=button_id,
            group_id="widget_stack",
            checked_color=checked_color,
            unchecked_color=unchecked_color,
            hover_color=hover_color,
            tooltip=tooltip,
            border_radius=border_radius,
            width=tbw,
            height=tbh
        )
        
        # Store button
        self.toggle_buttons[button_id] = button
        
        def apply_transparent_scroll_style(widget):
            widget.setStyleSheet("""
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

        # Add widget to custom_widgets
        if widget:
            self.custom_widgets[button_data["widget_name"]] = widget
            apply_transparent_scroll_style(widget)
        else:
            # Create a default empty widget if none provided
            self._create_empty_widget(button_id, button_data["widget_name"])
            apply_transparent_scroll_style(self.custom_widgets[button_data["widget_name"]])
        
        # Disconnect all toggle buttons first to avoid multiple connections
        for btn in self.toggle_buttons.values():
            try:
                btn.toggled_with_id.disconnect(self.switch_widget)
            except:
                pass  # It's okay if it wasn't connected
        
        # Clear and rebuild header layout
        for i in reversed(range(self.body_header_layout.count())):
            item = self.body_header_layout.itemAt(i)
            if item.widget():
                self.body_header_layout.removeWidget(item.widget())
        
        # Add buttons back to layout
        self.body_header_layout.addStretch()
        for btn_id in sorted(self.toggle_buttons.keys()):
            self.body_header_layout.addWidget(self.toggle_buttons[btn_id])
            self.toggle_buttons[btn_id].toggled_with_id.connect(self.switch_widget)
        
        self.body_header_layout.addSpacing(10)
        self.body_header_layout.addWidget(self.close_button)
        
        # Update content widget
        self.update_content_widget()
        
        # Set the new button as checked to switch to it immediately
        self.toggle_buttons[button_id].setChecked(True)
        
        return button_id
    
    def _create_empty_widget(self, button_id, widget_name):
        """Create a default empty widget for custom tabs with horizontal layout similar to default tabs"""
        # Create a scroll area with inverted wheel scrolling (vertical wheel = horizontal scroll)
        scroll_area = CS.CustomScrollArea(invert_primary=True)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        # Hide scrollbars but keep scrolling functionality through wheel events
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        def apply_transparent_scroll_style(widget):
            widget.setStyleSheet("""
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

        # Apply transparent scroll style
        apply_transparent_scroll_style(scroll_area)
        
        # Create a widget to hold the content
        content_widget = QtWidgets.QWidget()
        content_widget.button_id = button_id  # Store button_id for reference
        content_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        content_widget.setStyleSheet("background-color: rgba(36, 36, 36, 0);border:none;border-radius: 4px;")
        
        # Create a horizontal layout similar to the default tabs
        main_layout = QtWidgets.QHBoxLayout(content_widget)
        main_layout.setSpacing(4)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(QtCore.Qt.AlignCenter)
        
        # Add a header layout for the add button (on the left side)
        header_layout = QtWidgets.QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        #header_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        
        # Add a button to add function buttons
        add_button = CB.CustomButton(text="+",tooltip="Add Function Button",size=14,width=20,height=20, radius=10, color="#84bf4d")
        add_button.clicked.connect(lambda: self.add_function_button(button_id))
        
        # Add button to header layout
        #header_layout.addWidget(add_button)
        #header_layout.addStretch(1)
        
        # Add the header layout to the main layout
        #main_layout.addLayout(header_layout)
        #main_layout.addWidget(add_button)
        
        # Create a flow layout for function buttons - default is horizontal
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(4)
        button_layout.setAlignment(QtCore.Qt.AlignCenter)
        content_widget.button_layout = button_layout  # Store reference for adding buttons later
        
        button_layout.addWidget(add_button)

        # Store current orientation
        content_widget.is_horizontal = self.width() > self.height()
        
        # Add the button layout to the main layout
        main_layout.addLayout(button_layout)
        
        # Set the content widget as the scroll area's widget
        scroll_area.setWidget(content_widget)
        
        # Store the widget
        self.custom_widgets[widget_name] = scroll_area
        
        # Load function buttons for this tab
        self.load_function_buttons(button_id, content_widget)
        
    def remove_toggle_button_by_id(self, button_id):
        """Remove a toggle button from the body_header_layout by its ID"""
        # Check if button exists
        if button_id not in self.toggle_buttons:
            return False
            
        # Check if this is a default tab (IDs 0, 1, 2 are default)
        if button_id <= 2:
            # Show a message that default tabs cannot be removed
            cmds.warning("Cannot remove default tabs. Only custom tabs can be removed.")
            return False
            
        # Remove from database
        self.toggle_db.remove_toggle_button(button_id)
    
    def remove_toggle_button(self):
        """Remove the currently active toggle button if it's a custom tab"""
        # Get the current active button ID (current index of the stacked widget)
        current_id = self.content_widget.currentIndex()
        
        # Find which button is currently checked
        checked_button_id = None
        for btn_id, btn in self.toggle_buttons.items():
            if btn.isChecked():
                checked_button_id = btn_id
                break
        
        # Use the checked button ID if found, otherwise use current index
        if checked_button_id is not None:
            current_id = checked_button_id
        
        # Check if this is a default tab (IDs 0, 1, 2 are default)
        if current_id <= 2:
            # Show a message that default tabs cannot be removed
            cmds.warning("Cannot remove default tabs. Only custom tabs can be removed.")
            return False
        
        # Check if button exists
        if current_id not in self.toggle_buttons:
            cmds.warning(f"Button with ID {current_id} not found.")
            return False
        
        # Get the widget name before removing from database
        widget_name = None
        for button_data in self.toggle_db.get_toggle_buttons():
            if button_data["id"] == current_id:
                widget_name = button_data["widget_name"]
                break
        
        # Remove from database
        self.toggle_db.remove_toggle_button(current_id)
        
        # Remove button from layout
        button = self.toggle_buttons.pop(current_id)
        self.body_header_layout.removeWidget(button)
        button.deleteLater()
        
        # Remove widget from custom_widgets if it exists
        if widget_name and widget_name in self.custom_widgets:
            widget = self.custom_widgets.pop(widget_name)
            if widget:
                widget.deleteLater()
        
        # Disconnect all toggle buttons first to avoid multiple connections
        for btn in self.toggle_buttons.values():
            try:
                btn.toggled_with_id.disconnect(self.switch_widget)
            except:
                pass  # It's okay if it wasn't connected
        
        # Clear and rebuild header layout
        for i in reversed(range(self.body_header_layout.count())):
            item = self.body_header_layout.itemAt(i)
            if item and item.widget():
                self.body_header_layout.removeWidget(item.widget())
        
        # Add buttons back to layout
        self.body_header_layout.addStretch()
        for btn_id in sorted(self.toggle_buttons.keys()):
            self.body_header_layout.addWidget(self.toggle_buttons[btn_id])
            self.toggle_buttons[btn_id].toggled_with_id.connect(self.switch_widget)
        
        self.body_header_layout.addSpacing(10)
        self.body_header_layout.addWidget(self.close_button)
        
        # Update content widget
        self.update_content_widget()
        
        # Activate the first available button
        if self.toggle_buttons:
            first_id = min(self.toggle_buttons.keys())
            self.toggle_buttons[first_id].setChecked(True)
        
        return True
        
    def remove_toggle_button_by_id(self, button_id):
        """Remove a toggle button from the body_header_layout by its ID"""
        # Check if button exists
        if button_id not in self.toggle_buttons:
            return False
        
        # Check if this is a default tab (IDs 0, 1, 2 are default)
        if button_id <= 2:
            # Show a message that default tabs cannot be removed
            cmds.warning("Cannot remove default tabs. Only custom tabs can be removed.")
            return False
        
        # Remove from database
        self.toggle_db.remove_toggle_button(button_id)
        
        # Remove button from layout
        button = self.toggle_buttons.pop(button_id)
        self.body_header_layout.removeWidget(button)
        button.deleteLater()
        
        # Clear and rebuild header layout
        for i in reversed(range(self.body_header_layout.count())):
            item = self.body_header_layout.itemAt(i)
            if item.widget():
                self.body_header_layout.removeWidget(item.widget())
        
        # Add buttons back to layout
        self.body_header_layout.addStretch()
        for btn_id in sorted(self.toggle_buttons.keys()):
            self.body_header_layout.addWidget(self.toggle_buttons[btn_id])
        
        self.body_header_layout.addSpacing(10)
        self.body_header_layout.addWidget(self.close_button)
        
        # Update content widget
        self.update_content_widget()
        
        # If we removed the active button, activate the first available button
        if self.content_widget.currentIndex() == button_id and self.toggle_buttons:
            first_id = min(self.toggle_buttons.keys())
            self.toggle_buttons[first_id].setChecked(True)
        
        return True
            
        # Call the parent class closeEvent to properly close the Qt window
        super(ToolBoxWindow, self).closeEvent(event)
       
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
        
    def mouseMoveEvent(self, event):
        # Handle dragging
        if self.dragging and self.offset:
            self.move(event.globalPos() - self.offset)
            event.accept()
            return
            
        # Handle resizing
        if self.resizing and self.resize_edge:
            global_pos = event.globalPos()
            new_geometry = self.geometry()
            
            if 'right' in self.resize_edge:
                width = global_pos.x() - new_geometry.left()
                new_geometry.setWidth(max(self.minimumWidth(), width))
            if 'bottom' in self.resize_edge:
                height = global_pos.y() - new_geometry.top()
                new_geometry.setHeight(max(self.minimumHeight(), height))
            if 'left' in self.resize_edge:
                diff = global_pos.x() - new_geometry.left()
                if new_geometry.width() - diff >= self.minimumWidth():
                    new_geometry.setLeft(global_pos.x())
            if 'top' in self.resize_edge:
                diff = global_pos.y() - new_geometry.top()
                if new_geometry.height() - diff >= self.minimumHeight():
                    new_geometry.setTop(global_pos.y())
                    
            self.setGeometry(new_geometry)
            event.accept()
            return
            
    def resizeEvent(self, event):
        """Handle window resize events and update layouts if orientation changes"""
        # Call parent class implementation
        super(ToolBoxWindow, self).resizeEvent(event)
        
        # Check if orientation has changed
        is_horizontal = self.width() > self.height()
        
        # Store current orientation to detect changes
        if not hasattr(self, '_last_orientation') or self._last_orientation != is_horizontal:
            self._last_orientation = is_horizontal
            # Update layouts based on new orientation
            self.update_function_button_layouts(is_horizontal)
            
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
        
        UT.maya_main_window().activateWindow()
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
        
        UT.maya_main_window().activateWindow()
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
            
        UT.maya_main_window().activateWindow()
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
        
        UT.maya_main_window().activateWindow()
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
        UT.maya_main_window().activateWindow()
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