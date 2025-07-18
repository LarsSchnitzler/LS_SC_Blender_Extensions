bl_info = {
    "name": "L-system tree generator",
    "author": "Lars Schnitzler",
    "version": (1, 0),
    "blender": (4, 3, 2),
    "location": "View3D > Tool Shelf",
    "warning": "You can pretty easily freeze blender with the parameters. Be careful.",
    "description": "A simple add-on which uses LSystems to generate Trees.",
    "category": "Object",
    "support": "COMMUNITY",
}

import bpy
from math import radians
from . import ls_helpers

class LSystemProperties(bpy.types.PropertyGroup):    
    # L System properties
    axiom: bpy.props.StringProperty(name="Axiom", default="F")
    rule1: bpy.props.StringProperty(name="Rule 1", default="F=F[<+F]F[>+F]F")
    rule2: bpy.props.StringProperty(name="Rule 2", default="")
    rule3: bpy.props.StringProperty(name="Rule 3", default="")
    iterations: bpy.props.IntProperty(name="Iterations", default=3, min=0, max=50)
    
    # Turtle drawing properties
    string_length_limit: bpy.props.IntProperty(name="String length limit", default=100000)
    initial_step_distance: bpy.props.FloatProperty(name="Initial step distance", default=1.0, min=0.0, precision=4)
    step_distance_decrement: bpy.props.FloatProperty(name="Step distance decrementation", default=0.075, min=0, precision=4)
    minimal_step_distance: bpy.props.FloatProperty(name="Minimal step distance", default=0.05, min=0.0, precision=4)
    maximal_step_distance: bpy.props.FloatProperty(name="Maximal step distance", default=10, precision=4)
    
    pitch_angle: bpy.props.FloatProperty(name="Pitch angle [degrees]", default=0.0, min=0, max=180)
    roll_angle: bpy.props.FloatProperty(name="Roll angle [degrees]", default=0.0, min=0, max=180)
    yaw_angle: bpy.props.FloatProperty(name="Yaw angle [degrees]", default=0.0, min=0, max=180)
    
    initial_thickness: bpy.props.FloatProperty(name="Initial branch thickness", default=0.2, min=0.0, precision=3)
    thickness_decrementation: bpy.props.FloatProperty(name="Thickness decrementation", default=0.075, min=0.0, precision=4)
    minimal_thickness: bpy.props.FloatProperty(name="Minimal branch thickness", default=0.012, min=0.0, precision=4)
    maximal_thickness: bpy.props.FloatProperty(name="Maximal branch thickness", default=0.6, max=10.0, precision=4)
    
    # Further properties
    skin_skeletton: bpy.props.BoolProperty(name="Skin skeletton", default=False)
    run_lim_dis: bpy.props.BoolProperty(name="Run limited dissolve (reduces faces)", default=False)
    
class SimplePanel(bpy.types.Panel):
    bl_label = "LSystem Tree Generator"
    bl_idname = "LSYSTEM_PT_TreeGenerator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LSystem Tree Generator'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.lsystem_props
        
        box = layout.box()
        col = box.column(align=True)
        col.label(text="The axiom is the starting string.")
        col.label(text="Rules follow 'condition=content' (e.g., F=FF).")
        col.label(text="String length limit prevents Blender freezes.")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="As usual for LSystem implementations, a turtle system has")
        col.label(text="been implemented to translate the string into a 3D tree skeleton.")
        col.label(text="For that, specific characters have specific meanings,")
        col.label(text="from the perspective of the turtle:")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="'F' → Step forward")
        col.label(text="'$'/'%' → Increase/decrease step distance")
        col.label(text="'#'/'!' → Increase/decrease thickness")
        col.label(text="'['/']' → Save/retrieve turtle state")
        col.label(text="'+'/'-' → Pitch down/up")
        col.label(text="'>'/'<' → Roll to the right/left")
        col.label(text="'/' or '\\' → Yaw to the right/left")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Turtle start: (0, 0, 0), facing +Z")
        col.label(text="Left: -X, Up: -Y")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="The branch thickness inputs control")
        col.label(text="the Radius that is set on each vertex.")
        col.label(text="This can later be used by a skin Modifier,")
        col.label(text="to give the tree skeletton thickness.")
        layout.prop(props, "axiom")
        layout.prop(props, "rule1")
        layout.prop(props, "rule2")
        layout.prop(props, "rule3")
        layout.prop(props, "iterations")
        layout.prop(props, "string_length_limit")
        layout.separator()
        layout.prop(props, "initial_step_distance")
        layout.prop(props, "step_distance_decrement")
        layout.prop(props, "minimal_step_distance")
        layout.prop(props, "maximal_step_distance")
        layout.separator()
        layout.prop(props, "pitch_angle")
        layout.prop(props, "roll_angle")
        layout.prop(props, "yaw_angle")
        layout.separator()
        layout.prop(props, "initial_thickness")
        layout.prop(props, "thickness_decrementation")
        layout.prop(props, "minimal_thickness")
        layout.prop(props, "maximal_thickness")
        layout.separator()
        layout.prop(props, "skin_skeletton")
        layout.prop(props, "run_lim_dis")
        layout.separator()
        layout.operator("lsystem_tree.generate_tree")

class GenerateTreeOperator(bpy.types.Operator):
    bl_idname = "lsystem_tree.generate_tree"
    bl_label = "Generate Tree"
    bl_description = "Generate Tree using the given inputs."
    
    def execute(self, context):
        # Implementation        
        axm = context.scene.lsystem_props.axiom
        r1 = context.scene.lsystem_props.rule1
        r2 = context.scene.lsystem_props.rule2
        r3 = context.scene.lsystem_props.rule3
        i = context.scene.lsystem_props.iterations
        strL = context.scene.lsystem_props.string_length_limit
        
        initialStepDistance = bpy.context.scene.lsystem_props.initial_step_distance
        stepDistanceDecrement = bpy.context.scene.lsystem_props.step_distance_decrement
        minStep = bpy.context.scene.lsystem_props.minimal_step_distance
        maxStep = bpy.context.scene.lsystem_props.maximal_step_distance
        p_a = radians(bpy.context.scene.lsystem_props.pitch_angle)
        r_a = radians(bpy.context.scene.lsystem_props.roll_angle)
        y_a = radians(bpy.context.scene.lsystem_props.yaw_angle)
        initialThickness = bpy.context.scene.lsystem_props.initial_thickness
        thicknessDecrement = bpy.context.scene.lsystem_props.thickness_decrementation
        minThickness = bpy.context.scene.lsystem_props.minimal_thickness
        maxThickness = bpy.context.scene.lsystem_props.maximal_thickness
        
        skin_skeletton = bpy.context.scene.lsystem_props.skin_skeletton
        run_lim_dis = bpy.context.scene.lsystem_props.run_lim_dis
        
        try:
            string = ls_helpers.develop_string(axm, r1, r2, r3, i, strL)
            
            tree_skeleton_object = ls_helpers.draw_string(string, initialStepDistance, stepDistanceDecrement, minStep, maxStep, p_a, r_a, y_a, initialThickness, thicknessDecrement, minThickness, maxThickness)
            
            # This block is there to *just* select the tree_skeleton, 
            # so that we only operate on it in the following steps.
            if bpy.context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            tree_skeleton_object.select_set(True)
            bpy.context.view_layer.objects.active = tree_skeleton_object

            if skin_skeletton:
                tree_skeleton_object.modifiers.new("Skin", type='SKIN')

                #bpy.context.view_layer.update()
                depsgraph = bpy.context.evaluated_depsgraph_get()
                evaluated_obj = tree_skeleton_object.evaluated_get(depsgraph)
                new_mesh = bpy.data.meshes.new_from_object(evaluated_obj)
                tree_skeleton_object.data = new_mesh
                tree_skeleton_object.modifiers.clear()

                # This remove-doubles action needs to be done on the skinned mesh, not the skeletton mesh.
                # If we did it on the skeletton mesh, we could cause circles, which would cause the skin modifier to crash.
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles(threshold=0.0001)
                                
                if run_lim_dis:
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.dissolve_limited(angle_limit=0.0872665)  # 5° in radians
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
                    bpy.ops.mesh.tris_convert_to_quads()
                                                        
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.shade_smooth()

        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Unexpected error: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
        
classes = [LSystemProperties, GenerateTreeOperator, SimplePanel]

def register():
    exceptions_occurred = False
    
    # Registering all classes. Meaning that a metadata counterpart of the class is created in blender. 
    # The metadata counterpart points back to the python class blueprint, so Blender can execute its functions.
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            exceptions_occurred = True
            print(f"Exception caught during registration: {e}")

    # Creating actual storage for property values. This will create a third block of data for each property. 
    # Meaning we have a second counterpart (RNAdata) to the python class, which actually holds the values of the properties. 
    try:
        bpy.types.Scene.lsystem_props = bpy.props.PointerProperty(type=LSystemProperties)
    except Exception as e:
        exceptions_occurred = True
        print(f"Exception caught during registration: {e}")
    
    # Print out Registration success message   
    if not exceptions_occurred:
        print("L-system tree generator registration complete")
    else:
        print("L-system tree generator registration incomplete due to errors")

def unregister():
    exceptions_occurred = False
    
    try:
        print("trying to unregister the UI (SimplePanel), thus deleting the python class blueprint and metadata counterpart")
        bpy.utils.unregister_class(SimplePanel)
        print("success")
    except Exception as e:
        exceptions_occurred = True
        print(f"Exception caught during unregistration of 'SimplePanel': {e}")
        
    try:
        print("trying to unregister the Operator (GenerateTreeOperator), thus deleting the python class blueprints, RNAdata and metadata counterpart")
        bpy.utils.unregister_class(GenerateTreeOperator)
        print("success")
    except Exception as e:
        exceptions_occurred = True
        print(f"Exception caught during unregistration of Operator 'GenerateTreeOperator': {e}")
        
    try:
        print("trying to delete the RNAdata counterpart to the property group class (LSystemProperties).")
        del bpy.types.Scene.lsystem_props
        print("success")
    except Exception as e:
        exceptions_occurred = True
        print(f"Exception caught during deletion of RNAdata counterpart to the property group class 'LSystemProperties': {e}")
    
    try:
        print("trying to unregister the property group class, thus deleting the python class blueprints and metadata counterpart")
        bpy.utils.unregister_class(LSystemProperties)
        print("success")
    except Exception as e:
        exceptions_occurred = True
        print(f"Exception caught during unregistration of the property group class 'LSystemProperties': {e}")
        
    if not exceptions_occurred:
        print("L-system tree generator unregistration complete")
    else:
        print("L-system tree generator unregistration incomplete due to errors")

if __name__ == "__main__":
    register()