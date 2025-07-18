bl_info = {
    "name": "Space colonization tree generator",
    "author": "Lars Schnitzler",
    "version": (1, 0),
    "blender": (4, 3, 2),
    "location": "View3D > Tool Shelf",
    "warning": "You can pretty easily freeze blender with the parameters. Be careful.",
    "description": "A simple add-on which uses the space-colonization approach to generating trees.",
    "category": "Object",
    "support": "COMMUNITY",
}

import bpy
from . import sc_helpers

class SpaceColonizationProperties(bpy.types.PropertyGroup):
    # Space Colonization Properties
    attractorPointAmount: bpy.props.IntProperty(name="Attractor point amount", default=1000, min=0)
    di: bpy.props.FloatProperty(name="Distance of influence", default=1.5, min=0.0, precision=3)
    dk: bpy.props.FloatProperty(name="Kill distance", default=0.3, min=0.0, precision=3)
    step: bpy.props.FloatProperty(name="Step distance", default=0.1, min=0.0, precision=3)
    max_iterations: bpy.props.IntProperty(name="Iteration maximum", default = 100, min=1)
    gravity_tropism: bpy.props.FloatProperty(name="Gravity and tropism", default=0.05, min=-3, max=1)
    initial_thickness: bpy.props.FloatProperty(name="Initial branch thickness", default=0.2, min=0.0, precision=3)
    thickness_loss_factor: bpy.props.FloatProperty(name="Thickness-loss factor per iteration", default=0.95, min=0.0, max=1.0, precision=3)
    minimal_thickness: bpy.props.FloatProperty(name="Minimal branch thickness", default=0.012, min=0.00, precision=4)    
    # Further properties
    skin_skeleton: bpy.props.BoolProperty(name="Skin skeleton", default=False)
    run_lim_dis: bpy.props.BoolProperty(name="Run limited dissolve (reduces faces)", default=True)

class SimplePanel(bpy.types.Panel):
    bl_label = "Space-colonization Tree Generator"
    bl_idname = "SPACECOLONIZATION_PT_TreeGenerator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SpaceColonization Tree Generator'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.spacecolonization_props
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Please select a closed mesh before pressing 'Generate Tree'.")
        col.label(text="A point cloud will be distributed in it, based on the attractor count.")
        col.label(text="Starting from the origin, a tree will colonize this point cloud.")
        col.label(text="Ensure the mesh is above the origin so the trunk")
        col.label(text="eventually reaches the attractor points.")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="The larger the attractor count, the smaller the kill distance,")
        col.label(text="and the smaller the step distance, the longer it will take.")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Use the Iteration Maximum to stop early or prevent freezing.")
        col.label(text="This avoids excessive runtime if conditions are unfavorable.")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="The branch thickness inputs control")
        col.label(text="the Radius that is set on each vertex.")
        col.label(text="This can later be used by a skin Modifier,")
        col.label(text="to give the tree skeletton thickness.")
        layout.prop(props, "attractorPointAmount")
        layout.prop(props, "di")
        layout.prop(props, "dk")
        layout.prop(props, "step")
        layout.prop(props, "gravity_tropism")
        layout.prop(props, "max_iterations")
        layout.separator()
        layout.prop(props, "initial_thickness")
        layout.prop(props, "thickness_loss_factor")
        layout.prop(props, "minimal_thickness")
        layout.separator()
        layout.prop(props, "skin_skeleton")
        layout.prop(props, "run_lim_dis")
        layout.separator()
        layout.operator("spacecolonization_tree.generate_tree")

class GenerateTreeOperator(bpy.types.Operator):
    bl_idname = "spacecolonization_tree.generate_tree"
    bl_label = "Generate Tree"
    bl_description = "Generate Tree using the given inputs."
    
    def execute(self, context):
        # Implementation        
        attrPointAmount = bpy.context.scene.spacecolonization_props.attractorPointAmount
        di = bpy.context.scene.spacecolonization_props.di
        dk = bpy.context.scene.spacecolonization_props.dk
        step = bpy.context.scene.spacecolonization_props.step
        maxIterations = bpy.context.scene.spacecolonization_props.max_iterations
        gravity = bpy.context.scene.spacecolonization_props.gravity_tropism
        
        initial_thickness = bpy.context.scene.spacecolonization_props.initial_thickness
        thickness_loss_factor = bpy.context.scene.spacecolonization_props.thickness_loss_factor
        minThickness = bpy.context.scene.spacecolonization_props.minimal_thickness

        skin_skeleton = bpy.context.scene.spacecolonization_props.skin_skeleton
        run_lim_dis = bpy.context.scene.spacecolonization_props.run_lim_dis
        
        try:
            obj = bpy.context.active_object
            
            if obj is None:
                raise ValueError("No object is the active object.")
            if obj.type != 'MESH':
                raise ValueError("The active object is not a mesh.")
            if len(obj.data.polygons) <= 2:
                raise ValueError("The active object does not have enough faces.")
            if dk >= di:
                raise ValueError("The distance of influence should always be larger than the kill distance.")
            
            bpy.ops.object.mode_set(mode='OBJECT')
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
        
            A = sc_helpers.distribute_points(eval_obj, attrPointAmount)
            
            tree_skeleton_object = sc_helpers.space_colonization(A, di, dk, initial_thickness, thickness_loss_factor, minThickness, step, gravity, maxIterations)

            # Making sure we will operate on the tree skeleton when going into edit mode or shading smooth            
            bpy.ops.object.select_all(action='DESELECT')
            tree_skeleton_object.select_set(True)
            bpy.context.view_layer.objects.active = tree_skeleton_object

            # Deleting doubles
            # With l-systems, you pretty much wont ever produce double extrusions, but you could produce overlapping lines. 
            # When skinning those lines, you will get "double faces", which should be deleted after that. 
            # Deleting doubles should not be done before skinning, because that could produce circles in the case of l-system trees,
            # which would cause the skin modifier to not work.
            
            # This delete-doubles block is here, before skinning the mesh though. That is because this space colonization add-on can sometimes produce
            # double extrusions, which i dont understand - but it happens. So i delete those here, so that we dont 'drag' them through all the
            # following mesh postprocessing steps and only then merge them. 
            # There is practically no risk of making circles, since the space colonization method is based on self organisation of the branch-growth
            # based on space (There should never be any overlapping branches, besides those strange multiple extrusions of the same vertex).
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            if skin_skeleton:
                tree_skeleton_object.modifiers.new("Skin", type='SKIN')
                
                #bpy.context.view_layer.update()
                depsgraph = bpy.context.evaluated_depsgraph_get()
                evaluated_obj = tree_skeleton_object.evaluated_get(depsgraph)
                new_mesh = bpy.data.meshes.new_from_object(evaluated_obj)

                tree_skeleton_object.data = new_mesh
                tree_skeleton_object.modifiers.clear()
                
                bpy.ops.object.mode_set(mode='EDIT')                    
                if run_lim_dis:
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.dissolve_limited(angle_limit=0.0872665)  # 5° in radians
                    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
                    bpy.ops.mesh.tris_convert_to_quads()
                    
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.shade_smooth()

            obj.hide_set(True)

        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:        
            self.report({'ERROR'}, f"Unexpected error: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

classes = [SpaceColonizationProperties, GenerateTreeOperator, SimplePanel]

def register():
    exceptions_occurred = False
    
    # Registering all classes. Meaning that a metadata counterpart of the class is created in blender. 
    # The metadata counterpart ponts back to the python class blueprint, so Blender can execute its functions.
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            exceptions_occurred = True
            print(f"Exception caught during registration: {e}")

    # Creating actual storage for property values. This will create a third block of data for each property. 
    # Meaning we have a second counterpart (RNAdata) to the python class, which actually holds the values of the properties. 
    try:
        bpy.types.Scene.spacecolonization_props = bpy.props.PointerProperty(type=SpaceColonizationProperties)
    except Exception as e:
        exceptions_occurred = True
        print(f"Exception caught during registration: {e}")
    
    # Print out Registration success message   
    if not exceptions_occurred:
        print("Space colonization tree generator registration complete")
    else:
        print("Space colonization tree generator registration incomplete due to errors")

def unregister():
    exceptions_occurred = False
    
    # Unregister the UI (SimplePanel), thus deleting the python class blueprint and metadata counterpart
    try:
        print("trying to unregister the UI (SimplePanel), thus deleting the python class blueprint and metadata counterpart")
        bpy.utils.unregister_class(SimplePanel)
        print("success")
    except Exception as e:
        exceptions_occured = True
        print(f"Exception caught during unregistration of SimplePanel: {e}")
    
    # Unregister the Operator (GenerateTreeOperator), thus deleting the python class blueprints and metadata counterpart
    try:
        print("trying to unregister the Operator (GenerateTreeOperator), thus deleting the python class blueprints, RNAdata and metadata counterpart")
        bpy.utils.unregister_class(GenerateTreeOperator)
        print("success")
    except Exception as e:
        exceptions_occured = True
        print(f"Exception caught during unregistration of Operator 'GenerateTreeOperator': {e}")
        
    # Delete the RNAdata counterpart to the property group class (LSystemProperties).
    try:
        print("trying to delete the RNAdata counterpart to the property group class (SpaceColonizationProperties).")
        del bpy.types.Scene.spacecolonization_props
        print("success")
    except Exception as e:
        exceptions_occurred = True
        print(f"Exception caught during deletion of RNAdata counterpart to the property group class 'SpaceColonizationProperties': {e}")
    
    # Unregister the property group class, thus deleting the python class blueprints and metadata counterpart
    try:
        print("trying to unregister the property group class, thus deleting the python class blueprints and metadata counterpart")
        bpy.utils.unregister_class(SpaceColonizationProperties)
        print("success")
    except Exception as e:
        exceptions_occurred = True
        print(f"Exception caught during unregistration of the property group class 'SpaceColonizationProperties': {e}")
    
    # Print out Unregistration success message        
    if not exceptions_occurred:
        print("Space colonization tree generator unregistration complete")
    else:
        print("Space colonization tree generator unregistration incomplete due to errors")

if __name__ == "__main__":
    register()