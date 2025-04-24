import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om
from maya import OpenMayaUI as omui
from functools import wraps
import re
import json

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
    
from . utils import undoable

@undoable
def reset_move():
    # Get the list of selected objects
    sel_objs = cmds.ls(sl=True)

    # Loop through each selected object
    for obj in sel_objs:
        attrs = ['tx', 'ty', 'tz']
        
        for attr in attrs:
            attr_path = f"{obj}.{attr}"
            
            # Check if attribute is locked
            is_locked = cmds.getAttr(attr_path, lock=True)
            
            # Check if attribute has non-keyed connections
            has_non_keyed_connection = False
            if cmds.connectionInfo(attr_path, isDestination=True):
                # Get the source of the connection
                source = cmds.connectionInfo(attr_path, sourceFromDestination=True)
                
                # Check if the connection is from an animation curve (keyed)
                is_keyed = source and "animCurve" in cmds.nodeType(source.split('.')[0])
                
                # If there's a connection and it's not from an animation curve
                has_non_keyed_connection = not is_keyed
            
            # Reset the attribute if it's not locked and has no non-keyed connections
            if not is_locked and not has_non_keyed_connection:
                cmds.setAttr(attr_path, 0)

@undoable
def reset_rotate():
    # Get the list of selected objects
    sel_objs = cmds.ls(sl=True)

    # Loop through each selected object
    for obj in sel_objs:
        attrs = ['rx', 'ry', 'rz']
        
        for attr in attrs:
            attr_path = f"{obj}.{attr}"
            
            # Check if attribute is locked
            is_locked = cmds.getAttr(attr_path, lock=True)
            
            # Check if attribute has non-keyed connections
            has_non_keyed_connection = False
            if cmds.connectionInfo(attr_path, isDestination=True):
                # Get the source of the connection
                source = cmds.connectionInfo(attr_path, sourceFromDestination=True)
                
                # Check if the connection is from an animation curve (keyed)
                is_keyed = source and "animCurve" in cmds.nodeType(source.split('.')[0])
                
                # If there's a connection and it's not from an animation curve
                has_non_keyed_connection = not is_keyed
            
            # Reset the attribute if it's not locked and has no non-keyed connections
            if not is_locked and not has_non_keyed_connection:
                cmds.setAttr(attr_path, 0)

@undoable
def reset_scale():
    # Get the list of selected objects
    sel_objs = cmds.ls(sl=True)

    # Loop through each selected object
    for obj in sel_objs:
        attrs = ['sx', 'sy', 'sz']
        
        for attr in attrs:
            attr_path = f"{obj}.{attr}"
            
            # Check if attribute is locked
            is_locked = cmds.getAttr(attr_path, lock=True)
            
            # Check if attribute has non-keyed connections
            has_non_keyed_connection = False
            if cmds.connectionInfo(attr_path, isDestination=True):
                # Get the source of the connection
                source = cmds.connectionInfo(attr_path, sourceFromDestination=True)
                
                # Check if the connection is from an animation curve (keyed)
                is_keyed = source and "animCurve" in cmds.nodeType(source.split('.')[0])
                
                # If there's a connection and it's not from an animation curve
                has_non_keyed_connection = not is_keyed
            
            # Reset the attribute if it's not locked and has no non-keyed connections
            if not is_locked and not has_non_keyed_connection:
                # Scale attributes need to be set to 1 instead of 0
                cmds.setAttr(attr_path, 1)

@undoable
def reset_all():
    # Get the list of selected objects
    sel_objs = cmds.ls(sl=True)

    # Loop through each selected object
    for obj in sel_objs:
        # Define the attributes to check
        attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']
        default_values = {'tx': 0, 'ty': 0, 'tz': 0, 'rx': 0, 'ry': 0, 'rz': 0, 'sx': 1, 'sy': 1, 'sz': 1}
        
        for attr in attrs:
            attr_path = f"{obj}.{attr}"
            
            # Check if attribute is locked
            is_locked = cmds.getAttr(attr_path, lock=True)
            
            # Check if attribute has non-keyed connections
            has_non_keyed_connection = False
            if cmds.connectionInfo(attr_path, isDestination=True):
                # Get the source of the connection
                source = cmds.connectionInfo(attr_path, sourceFromDestination=True)
                
                # Check if the connection is from an animation curve (keyed)
                is_keyed = source and "animCurve" in cmds.nodeType(source.split('.')[0])
                
                # If there's a connection and it's not from an animation curve
                has_non_keyed_connection = not is_keyed
            
            # Reset the attribute if it's not locked and has no non-keyed connections
            if not is_locked and not has_non_keyed_connection:
                cmds.setAttr(attr_path, default_values[attr])
#---------------------------------------------------------------------------------------------------------------------------
@undoable
def store_component_position():
    # Get the active selection
    selection = cmds.ls(sl=True)
    
    # Get the defaultObjectSet
    default_set = 'defaultObjectSet'
    
    # Initialize the stored position
    stored_position = [0, 0, 0]  # Default to world origin
    
    # Check if there's an active selection
    if selection:
        # Get the manipulator position
        manipulator_pos = None
        current_ctx = cmds.currentCtx()
        if current_ctx == 'moveSuperContext':
            manipulator_pos = cmds.manipMoveContext('Move', q=True, position=True)
        elif current_ctx == 'RotateSuperContext':
            manipulator_pos = cmds.manipRotateContext('Rotate', q=True, position=True)
        elif current_ctx == 'scaleSuperContext':
            manipulator_pos = cmds.manipScaleContext('Scale', q=True, position=True)

        if manipulator_pos:
            stored_position = manipulator_pos
        else:
            cmds.warning("Unable to get manipulator position. Using world origin.")
    else:
        cmds.warning("Nothing selected. Using world origin.")

    # Check if the 'Stored Location' attribute exists, if not, create it
    if not cmds.attributeQuery('Stored_Location', node=default_set, exists=True):
        cmds.addAttr(default_set, longName='Stored_Location', attributeType='double3')
        cmds.addAttr(default_set, longName='Stored_Location_X', attributeType='double', parent='Stored_Location')
        cmds.addAttr(default_set, longName='Stored_Location_Y', attributeType='double', parent='Stored_Location')
        cmds.addAttr(default_set, longName='Stored_Location_Z', attributeType='double', parent='Stored_Location')

    # Store the position in the custom attribute
    cmds.setAttr(f'{default_set}.Stored_Location', *stored_position)

    print(f"Position stored in {default_set}.Stored_Location:", stored_position)

@undoable
def move_objects_to_stored_position():
    selected_objects = cmds.ls(selection=True, long=True)
    default_set = 'defaultObjectSet'
    
    # Check if the stored position attribute exists
    if not cmds.attributeQuery('Stored_Location', node=default_set, exists=True):
        cmds.warning("No stored position found. Please store a position first.")
        return

    # Get the stored position
    stored_position = cmds.getAttr(f'{default_set}.Stored_Location')[0]

    # Check if there are any objects selected
    if not selected_objects:
        cmds.warning("Please select at least one object to move.")
        return

    # Loop through the selected objects and move them to the stored position
    for obj in selected_objects:
        # Get the current world space rotate pivot of the object
        current_position = cmds.xform(obj, query=True, worldSpace=True, rotatePivot=True)
        
        # Calculate the difference between the stored position and current position
        offset = [stored_position[i] - current_position[i] for i in range(3)]
        
        # Move the object by the calculated offset
        cmds.move(offset[0], offset[1], offset[2], obj, relative=True, worldSpace=True)
    
    cmds.select(selected_objects)
    print(f"Moved {len(selected_objects)} object(s) to stored position: {stored_position}")
#---------------------------------------------------------------------------------------------------------------
@undoable
def create_single_adjustment_group():
    # Get the selected objects
    selection = cmds.ls(selection=True, long=True)
    
    # Check if there is at least one object selected
    if not selection:
        cmds.error("No objects selected. Please select at least one object.")
        return

    for ctrl_obj in selection:
        # Get the short name of the control object for naming the group
        ctrl_short_name = ctrl_obj.split('|')[-1]
        grp1_name = f"{ctrl_short_name}_offset"
        #grp2_name = f"{ctrl_short_name}_xform"
        #grp3_name = f"{ctrl_short_name}_topGrp"
        
        # Get the current parent of the control object
        current_parent = cmds.listRelatives(ctrl_obj, parent=True, fullPath=True)
        
        # Create a group for ctrl_obj
        ctrl_grp1 = cmds.group(empty=True, name=grp1_name)
        #ctrl_grp2 = cmds.group(empty=True, name=grp2_name)
        #ctrl_grp3 = cmds.group(empty=True, name=grp3_name)
        
        # Match the transform of the new group to the control object
        cmds.matchTransform(ctrl_grp1, ctrl_obj)
        #cmds.matchTransform(ctrl_grp2, ctrl_obj)
        #cmds.matchTransform(ctrl_grp3, ctrl_obj)
        
        # If the control object had a parent, parent the new group to it
        if current_parent:
            cmds.parent(ctrl_grp1, current_parent[0])
            
        # Parent the control object to the new group
        cmds.parent(ctrl_obj, ctrl_grp1)
        cmds.select(ctrl_grp1, replace=True)
        #cmds.parent(ctrl_grp1, ctrl_grp2)
        #cmds.parent(ctrl_grp2, ctrl_grp3)

@undoable
def create_double_adjustment_group():
    # Get the selected objects
    selection = cmds.ls(selection=True, long=True)
    
    # Check if there is at least one object selected
    if not selection:
        cmds.error("No objects selected. Please select at least one object.")
        return

    for ctrl_obj in selection:
        # Get the short name of the control object for naming the group
        ctrl_short_name = ctrl_obj.split('|')[-1]
        grp1_name = f"{ctrl_short_name}_offset"
        grp2_name = f"{ctrl_short_name}_xform"
        #grp3_name = f"{ctrl_short_name}_topGrp"
        
        # Get the current parent of the control object
        current_parent = cmds.listRelatives(ctrl_obj, parent=True, fullPath=True)
        
        # Create a group for ctrl_obj
        ctrl_grp1 = cmds.group(empty=True, name=grp1_name)
        ctrl_grp2 = cmds.group(empty=True, name=grp2_name)
        #ctrl_grp3 = cmds.group(empty=True, name=grp3_name)
        
        # Match the transform of the new group to the control object
        cmds.matchTransform(ctrl_grp1, ctrl_obj)
        cmds.matchTransform(ctrl_grp2, ctrl_obj)
        #cmds.matchTransform(ctrl_grp3, ctrl_obj)
        
        # If the control object had a parent, parent the new group to it
        if current_parent:
            cmds.parent(ctrl_grp1, current_parent[0])
            
        # Parent the control object to the new group
        cmds.parent(ctrl_obj, ctrl_grp1)
        cmds.parent(ctrl_grp1, ctrl_grp2)
        cmds.select(ctrl_grp2, replace=True)
        #cmds.parent(ctrl_grp2, ctrl_grp3)

@undoable
def create_single_adjustment_group_move():
    # Get the selected objects
    selection = cmds.ls(selection=True, long=True)
    
    if len(selection) < 2:
        cmds.warning("Please select at least two objects: the control object and then the joint object.")
        return
    
    ctrl_obj = selection[0]
    jnt_obj = selection[-1]
    
    if not cmds.objExists(ctrl_obj) or not cmds.objExists(jnt_obj):
        cmds.warning("One or both of the selected objects do not exist.")
        return
    #cmds.matchTransform(ctrl_obj, jnt_obj, rotation=True)
    #cmds.makeIdentity(ctrl_obj, apply=True, rotate=True)

    # Get the short name of the control object for naming the group
    ctrl_short_name = cmds.ls(ctrl_obj, shortNames=True)[0]
    grp1_name = f"{ctrl_short_name}_offset"
    #grp2_name = f"{ctrl_short_name}_xform"
    #grp3_name = f"{ctrl_short_name}_topGrp"
    
    # Get the current parent of the control object
    current_parent = cmds.listRelatives(ctrl_obj, parent=True, fullPath=True)
    
    # Create a group for ctrl_obj
    ctrl_grp1 = cmds.group(empty=True, name=grp1_name)
    #ctrl_grp2 = cmds.group(empty=True, name=grp2_name)
    #ctrl_grp3 = cmds.group(empty=True, name=grp3_name)
    
    # Match the transform of the new group to the control object
    cmds.matchTransform(ctrl_grp1, ctrl_obj)
    #cmds.matchTransform(ctrl_grp2, ctrl_obj)
    #cmds.matchTransform(ctrl_grp3, ctrl_obj)
    
    # Parent the control object to the new group
    cmds.parent(ctrl_obj, ctrl_grp1)
    #cmds.parent(ctrl_grp1, ctrl_grp2)
    #cmds.parent(ctrl_grp2, ctrl_grp3)
    
    # If the control object had a parent, parent the new group to it
    if current_parent:
        cmds.parent(ctrl_grp1, current_parent[0])

    # Match the group's transform to the control object
    cmds.matchTransform(ctrl_grp1, jnt_obj)

@undoable
def create_double_adjustment_group_move():
    # Get the selected objects
    selection = cmds.ls(selection=True, long=True)
    
    if len(selection) < 2:
        cmds.warning("Please select at least two objects: the control object and then the joint object.")
        return
    
    ctrl_obj = selection[0]
    jnt_obj = selection[-1]
    
    if not cmds.objExists(ctrl_obj) or not cmds.objExists(jnt_obj):
        cmds.warning("One or both of the selected objects do not exist.")
        return
    #cmds.matchTransform(ctrl_obj, jnt_obj, rotation=True)
    #cmds.makeIdentity(ctrl_obj, apply=True, rotate=True)

    # Get the short name of the control object for naming the group
    ctrl_short_name = cmds.ls(ctrl_obj, shortNames=True)[0]
    grp1_name = f"{ctrl_short_name}_offset"
    grp2_name = f"{ctrl_short_name}_xform"
    #grp3_name = f"{ctrl_short_name}_topGrp"
    
    # Get the current parent of the control object
    current_parent = cmds.listRelatives(ctrl_obj, parent=True, fullPath=True)
    
    # Create a group for ctrl_obj
    ctrl_grp1 = cmds.group(empty=True, name=grp1_name)
    ctrl_grp2 = cmds.group(empty=True, name=grp2_name)
    #ctrl_grp3 = cmds.group(empty=True, name=grp3_name)
    
    # Match the transform of the new group to the control object
    cmds.matchTransform(ctrl_grp1, ctrl_obj)
    cmds.matchTransform(ctrl_grp2, ctrl_obj)
    #cmds.matchTransform(ctrl_grp3, ctrl_obj)
    
    # Parent the control object to the new group
    cmds.parent(ctrl_obj, ctrl_grp1)
    cmds.parent(ctrl_grp1, ctrl_grp2)
    #cmds.parent(ctrl_grp2, ctrl_grp3)
    
    # If the control object had a parent, parent the new group to it
    if current_parent:
        cmds.parent(ctrl_grp1, current_parent[0])

    # Match the group's transform to the control object
    cmds.matchTransform(ctrl_grp2, jnt_obj)

@undoable
def create_single_adjustment_group_move_multi():
    # Get the selected objects
    selection = cmds.ls(selection=True, long=True)
    
    if len(selection) < 2:
        cmds.warning("Please select at least two objects: the control object and then the joint object.")
        return
    
    # First half of selections
    ctrl_objs = selection[:len(selection)//2]
    # Second half of selections
    jnt_objs = selection[len(selection)//2:]

    for obj in ctrl_objs:

        ctrl_obj = obj
        jnt_obj = jnt_objs[ctrl_objs.index(obj)]
        
        if not cmds.objExists(ctrl_obj) or not cmds.objExists(jnt_obj):
            cmds.warning("One or both of the selected objects do not exist.")
            return
        #cmds.matchTransform(ctrl_obj, jnt_obj, rotation=True)
        #cmds.makeIdentity(ctrl_obj, apply=True, rotate=True)

        # Get the short name of the control object for naming the group
        ctrl_short_name = cmds.ls(ctrl_obj, shortNames=True)[0]
        grp1_name = f"{ctrl_short_name}_offset"

        # Get the current parent of the control object
        current_parent = cmds.listRelatives(ctrl_obj, parent=True, fullPath=True)
        
        # Create a group for ctrl_obj
        ctrl_grp1 = cmds.group(empty=True, name=grp1_name)

        # Match the transform of the new group to the control object
        cmds.matchTransform(ctrl_grp1, ctrl_obj)

        # Parent the control object to the new group
        cmds.parent(ctrl_obj, ctrl_grp1)

        # If the control object had a parent, parent the new group to it
        if current_parent:
            cmds.parent(ctrl_grp1, current_parent[0])

        # Match the group's transform to the control object
        cmds.matchTransform(ctrl_grp1, jnt_obj)
#---------------------------------------------------------------------------------------------------------------
@undoable
def create_constraint(constraint_type="parent", maintain_offset=True):
    """
    Creates a constraint based on specified type and offset setting using Maya's selection
    Args:
        constraint_type: Type of constraint ("parent", "point", "orient", "scale", "aim", "pole")
        maintain_offset: Whether to maintain offset (True/False)
    """
    selection = cmds.ls(sl=True)
    
    # Special case for pole vector - needs IK handle
    if constraint_type == "pole":
        if len(selection) != 2:
            cmds.warning("Pole Vector needs exactly 2 selections: ctrl and IK handle")
            return
        ctrl = selection[0]
        ik_handle = selection[1]
        constraint = cmds.poleVectorConstraint(
            ctrl,
            ik_handle,
            name=f"{ctrl}_poleVectorConstraint"
        )
        return

    if len(selection) < 2:
        cmds.warning("Please select at least 2 objects. First selection(s) will be the source(s).")
        return
            
    sources = selection[:-1]  # First selected objects are sources
    target = selection[-1]   # Last selected object is target
    
    if constraint_type == "aim":
        cmds.aimConstraint(
            sources,
            target,
            maintainOffset=maintain_offset,
            weight=1.0,
            aimVector=[1, 0, 0],
            upVector=[0, 1, 0],
            worldUpType="vector",
            name=f"{sources[0]}_{constraint_type}Constraint"
        )
    else:
        constraint_cmd = getattr(cmds, f"{constraint_type}Constraint")
        constraint_cmd(
            sources,
            target,
            maintainOffset=maintain_offset,
            weight=1.0,
            name=f"{sources[0]}_{constraint_type}Constraint"
        )

def parent_constraint():
    create_constraint("parent", False)

def parent_constraint_offset():
    create_constraint("parent", True)

def point_constraint():
    create_constraint("point", False)

def point_constraint_offset():
    create_constraint("point", True)

def orient_constraint():
    create_constraint("orient", False)

def orient_constraint_offset():
    create_constraint("orient", True)

def scale_constraint():
    create_constraint("scale", False)

def scale_constraint_offset():
    create_constraint("scale", True)

def aim_constraint():
    create_constraint("aim", False)

def aim_constraint_offset():
    create_constraint("aim", True)

def pole_vector_constraint():
    create_constraint("pole", False)

def parent_constraint_options():
    mel.eval("ParentConstraintOptions ;")

#---------------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------------
def mute_all():
    mel.eval('channelBoxCommand -muteall;')

def unMute_all():
    mel.eval('channelBoxCommand -unmuteall;')

def mute_selected():
    mel.eval('channelBoxCommand -mute;')

def unMute_selected():
    mel.eval('channelBoxCommand -unmute;')

def break_connections():
    mel.eval('channelBoxCommand -break;')

#---------------------------------------------------------------------------------------------------------------
