import maya.cmds as cmds
import maya.mel as mel


def create_curve(object_name, object_data):
    created_curves = []
    shapes_data = object_data.get("shapes", [object_data])
    for i, shape_data in enumerate(shapes_data):
        required_keys = ["form", "pos_vectors", "knots", "degree"]
        for key in required_keys:
            if key not in shape_data:
                raise Exception(f"Cannot create curve with lacking curve data: missing {key}")

        points = shape_data["pos_vectors"]
        curve_name = f"{object_name}_curve_{i+1}"
        new_node = cmds.curve(p=points, k=shape_data["knots"], d=shape_data["degree"], name=curve_name)
        
        # Get the shape node and rename it
        curve_shapes = cmds.listRelatives(new_node, shapes=True, fullPath=True) or []
        if curve_shapes:
            curve_shape = curve_shapes[0]
            cmds.rename(curve_shape, f"{curve_name}Shape")

        if shape_data["form"] > 0:
            cmds.closeCurve(new_node, ch=False, rpo=True)
        if "offset" in shape_data:
            offset_matrix = shape_data["offset"]
            cmds.xform(new_node, matrix=offset_matrix, worldSpace=True)
        created_curves.append(new_node)

    for curve in created_curves:
        cmds.makeIdentity(curve, apply=True, translate=True, rotate=True, scale=True)

    curve_group = cmds.group(empty=True, name=object_name)
    cmds.select(clear=True)
    curve_shapes = []
    for curve in created_curves:
        shapes = cmds.listRelatives(curve, shapes=True, fullPath=True) or []
        curve_shapes.extend(shapes)

    if curve_shapes:
        cmds.select(curve_shapes, replace=True)
        cmds.select(curve_group, add=True)
        mel.eval('parent -r -s')

    for curve in created_curves:
        if not cmds.listRelatives(curve, children=True):
            cmds.delete(curve)
    
    cmds.xform(curve_group, centerPivots=True)
    cmds.select(curve_group, replace=True)
    mel.eval('rename `ls -sl` "{0}";'.format(object_name))
    mel.eval('move -rpr 0 0 0;')
    mel.eval('FreezeTransformations;')
    mel.eval('makeIdentity -apply true -t 1 -r 1 -s 1 -n 0 -pn 1;')

    object_name = cmds.ls(curve_group)[0]
    
    return object_name

circle_18_shape = {"shapes": [{"pos_vectors":[[1.0,0.0,0.0],[0.939693,0.34202,0.0],[0.766044,0.642788,0.0],[0.5,0.866025,0.0],[0.173648,0.984808,0.0],[-0.173648,0.984808,0.0],[-0.5,0.866025,0.0],[-0.766044,0.642788,0.0],[-0.939693,0.34202,0.0],[-1.0,0.0,0.0],[-0.939693,-0.34202,0.0],[-0.766044,-0.642788,0.0],[-0.5,-0.866025,0.0],[-0.173648,-0.984808,0.0],[0.173648,-0.984808,0.0],[0.5,-0.866025,0.0],[0.766044,-0.642788,0.0],[0.939693,-0.34202,0.0],[1.0,0.0,0.0]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,1.195995,1.0]}]}
square_shape  = {"shapes": [{"pos_vectors":[[1.0,1.0,0.0],[-1.0,1.0,0.0],[-1.0,-1.0,0.0],[1.0,-1.0,0.0],[1.0,1.0,0.0]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,-1.0,0.0,0.0,0.0,0.0,0.0,1.0]}]}
cube_shape = {"shapes": [{"pos_vectors":[[-5.150279,5.150279,5.150279],[-5.150279,5.150279,-5.150279],[5.150279,5.150279,-5.150279],[5.150279,5.150279,5.150279],[-5.150279,5.150279,5.150279],[-5.150279,-5.150279,5.150279],[-5.150279,-5.150279,-5.150279],[-5.150279,5.150279,-5.150279],[-5.150279,5.150279,5.150279],[-5.150279,-5.150279,5.150279],[5.150279,-5.150279,5.150279],[5.150279,5.150279,5.150279],[5.150279,5.150279,-5.150279],[5.150279,-5.150279,-5.150279],[5.150279,-5.150279,5.150279],[5.150279,-5.150279,-5.150279],[-5.150279,-5.150279,-5.150279]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0],"form":0,"offset":[0.205628,0.0,0.0,0.0,0.0,0.205628,0.0,0.0,0.0,0.0,0.205628,0.0,0.0,0.0,0.0,1.0]}]}
triangle_shape = {"shapes": [{"pos_vectors":[[-1.062929,-0.0,1.062929],[1.062929,-0.0,1.062929],[0.0,0.0,-1.062929],[-1.062929,-0.0,1.062929]],"degree":1,"knots":[0.0,1.0,2.0,3.0],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]}]}
pyramid_shape = {"shapes": [{"pos_vectors":[[-0.738213,-0.0,-0.738213],[0.738213,-0.0,-0.738213],[0.738213,-0.0,0.738213],[-0.738213,-0.0,0.738213],[-0.738213,-0.0,-0.738213],[-0.0,1.539523,-0.0],[0.738213,-0.0,-0.738213],[0.738213,-0.0,0.738213],[-0.0,1.539523,-0.0],[-0.738213,-0.0,0.738213],[-0.738213,-0.0,-0.738213],[-0.0,1.539523,-0.0],[0.738213,-0.0,-0.738213]],"degree":1,"knots":[0.0,4.0,8.0,12.0,16.0,24.485,32.97,36.97,45.455,53.941,57.941,66.426,74.911],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]}]}
arrow_shape = {"shapes": [{"pos_vectors":[[-0.418175,-1.25,0.0],[-0.418175,-0.25,0.0],[-1.0,-0.25,0.0],[0.0,1.25,0.0],[1.0,-0.25,0.0],[0.418175,-0.25,0.0],[0.418175,-1.25,0.0],[-0.418175,-1.25,0.0]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0],"form":0,"offset":[1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]}]}
cycle_shape = {"shapes": [{"pos_vectors":[[1.821412,-0.0,3.228411],[2.575865,-0.0,2.649498],[3.154778,-0.0,1.895045],[3.518698,-0.0,1.016465],[3.642823,-0.0,0.073633],[3.518698,-0.0,-0.8692],[3.154777,-0.0,-1.74778],[2.575865,-0.0,-2.502233],[1.821411,-0.0,-3.081145],[1.421608,-0.0,-2.462164],[0.717669,-0.0,-4.559907],[0.720485,-0.0,-4.567671],[2.786863,-0.0,-4.843799],[2.45964,-0.0,-4.18659],[3.478457,-0.0,-3.404825],[4.260222,-0.0,-2.386008],[4.75166,-0.0,-1.199571],[4.919281,-0.0,0.073632],[4.751661,-0.0,1.346836],[4.260222,-0.0,2.533273],[3.478457,-0.0,3.55209],[2.459641,-0.0,4.333856],[2.459641,-0.0,4.333856],[2.459641,-0.0,4.333856],[2.459641,-0.0,4.333856]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0,19.0,20.0,21.0,22.0,23.0,24.0],"form":2,"offset":[0.329236,0.0,0.0,0.0,0.0,0.329236,0.0,0.0,0.0,0.0,0.329236,0.0,0.0,0.0,0.0,1.0]},
                          {"pos_vectors":[[-1.821412,-0.0,3.228411],[-1.540693,-0.0,2.763896],[-0.698641,-0.0,4.568377],[-0.702549,-0.0,4.57625],[-2.736469,-0.0,4.843799],[-2.459641,-0.0,4.333856],[-3.478457,-0.0,3.55209],[-4.260222,-0.0,2.533273],[-4.751661,-0.0,1.346836],[-4.919281,-0.0,0.073632],[-4.75166,-0.0,-1.199571],[-4.260222,-0.0,-2.386008],[-3.478457,-0.0,-3.404825],[-2.45964,-0.0,-4.18659],[-1.821411,-0.0,-3.081145],[-2.575865,-0.0,-2.502233],[-3.154777,-0.0,-1.74778],[-3.518698,-0.0,-0.8692],[-3.642823,-0.0,0.073633],[-3.518698,-0.0,1.016465],[-3.154778,-0.0,1.895045],[-2.575865,-0.0,2.649498],[-2.575865,-0.0,2.649498],[-2.575865,-0.0,2.649498],[-2.575865,-0.0,2.649498]],"degree":1,"knots":[0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0,19.0,20.0,21.0,22.0,23.0,24.0],"form":2,"offset":[0.329236,0.0,0.0,0.0,0.0,0.329236,0.0,0.0,0.0,0.0,0.329236,0.0,0.0,0.0,0.0,1.0]}]}

def circle_sc():
    #create_curve('circle',circle_18_shape)
    cmds.circle(c=(0, 0, 0), nr=(0, 1, 0), sw=360, r=1, d=3, ut=0, tol=0.0001, s=8, ch=1)[0]
def square_sc():
    create_curve('square',square_shape)
def cube_sc():
    create_curve('box',cube_shape)
def triangle_sc():
    create_curve('triangle',triangle_shape)
def pyramid_sc():
    create_curve('pyramid',pyramid_shape)
def arrow_sc():
    create_curve('arrow',arrow_shape)
def cycle_sc():
    create_curve('cycle',cycle_shape)
    
