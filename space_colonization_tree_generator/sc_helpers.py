import bpy
import bmesh
import random
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

def point_inside_mesh(bvh, local_point):
    result = bvh.find_nearest(local_point)
    closest_point = result[0]
    normal = result[1]
    
    if closest_point is None:
        return False

    difference_vec = local_point - closest_point

    if difference_vec.dot(normal) < 0:
        return True
    else:
        return False

def distribute_points(object, num_points):
    bm = bmesh.new()
    bm.from_mesh(object.data)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    bvh = BVHTree.FromBMesh(bm)

    xBounds = [0.0, 0.0]
    yBounds = [0.0, 0.0]
    zBounds = [0.0, 0.0]
    
    for v in bm.verts:
        x = v.co.x
        y = v.co.y
        z = v.co.z
        
        if x < xBounds[0]:
            xBounds[0] = x
        if x > xBounds[1]:
            xBounds[1] = x
            
        if y < yBounds[0]:
            yBounds[0] = y
        if y > yBounds[1]:
            yBounds[1] = y
        
        if z < zBounds[0]:
            zBounds[0] = z
        if z > zBounds[1]:
            zBounds[1] = z
            
    points = []
    while len(points) < num_points:
        random_point = Vector((
            random.uniform(xBounds[0], xBounds[1]),
            random.uniform(yBounds[0], yBounds[1]),
            random.uniform(zBounds[0], zBounds[1])
        ))
        
        if point_inside_mesh(bvh, random_point):
            points.append(object.matrix_world @ random_point)
    
    bm.free()    
    
    return points

def filter_attractors(A, toDelete):
    new_A = []
    for i in range(len(A)):
        if i not in toDelete:
            new_A.append(A[i])
    return new_A

def space_colonization(A, di, dk, initial_thickness, thickness_loss_factor, minThickness, step, gravity, max_i):
    T = bmesh.new()
    
    thickness = initial_thickness
    
    skin_layer = T.verts.layers.skin.verify()

    root_vertex = T.verts.new((0.0, 0.0, 0.0))
    root_vertex[skin_layer].radius = (thickness, thickness)
    T.verts.ensure_lookup_table()
    
    extrusion_dictionary = {}
    # some non relevant content for 0 in the dictionary, just so that it will be included in the kd tree in the first iteration:
    extrusion_dictionary[0] = (Vector((0.0, 0.0, 0.0)), 1)
    
    vertex_id = 0
    vertsHaveBeenAttracted = False    
    
    growth_iteration = 0
    while len(A) > 0 and growth_iteration <= max_i:
        attractors_toDelete_indices = set() 
        
        # construct kd tree from active T vertices.

        kd = KDTree(len(T.verts))
        for i in range(len(T.verts)):
            if i in extrusion_dictionary:
                kd.insert(T.verts[i].co, i)
        kd.balance()
        
        # empty extrusion dictionary after using the one from the iteration before to construct the kd tree.
        extrusion_dictionary = {}
        
        # identify all t which should be extruded. Also identify all a which should be deleted.
        for j in range(len(A)):
            result = kd.find(A[j])
            coords_nearest = result[0] # Is a mathutils Vector
            index_nearest = result[1]
            distance = result[2]
            
            if distance < dk:
                attractors_toDelete_indices.add(j)
            
            if distance < di:
                if not vertsHaveBeenAttracted:
                    vertsHaveBeenAttracted = True
                differenceVector_normalized = Vector((A[j].x - coords_nearest.x, A[j].y - coords_nearest.y, A[j].z - coords_nearest.z)).normalized()
                if index_nearest in extrusion_dictionary:
                    sum_vector = extrusion_dictionary[index_nearest]
                    extrusion_dictionary[index_nearest] = (sum_vector + differenceVector_normalized)
                else:
                    extrusion_dictionary[index_nearest] = (differenceVector_normalized)
        
        if len(extrusion_dictionary) == 0 and vertsHaveBeenAttracted:
            print("No vertices have been attracted anymore, the algorithm seems to have stagnated.")
            # put out the mesh.
            root_vertex[skin_layer].use_root = True
            
            mesh_data = bpy.data.meshes.new("SpaceColonizationMesh")
            T.to_mesh(mesh_data)
            
            T.free()
            
            obj = bpy.data.objects.new("SpaceColonizationTree", mesh_data)
            bpy.context.collection.objects.link(obj)
            
            return obj

        # extrude according to the dictionary; which we just built with all vertices which are the closest to a attractionpoint, and within di.
        for k in range(len(T.verts)):
            if k not in extrusion_dictionary:
                continue
            direction_vector = extrusion_dictionary[k].normalized()
            direction_vector.z -= gravity
            extrusion_vector = direction_vector.normalized() * step
            vertex = T.verts[k]
            geom = bmesh.ops.extrude_vert_indiv(T, verts = [vertex])
            new_vertex = geom['verts'][0]
            new_vertex[skin_layer].radius = (thickness, thickness)
            new_vertex.co += extrusion_vector
            T.verts.ensure_lookup_table()
            
            # from the end of this loop, until the build of the kd tree, extrusion_dictionary is not true to its name. 
            # to keep write accesses as low as possible, I used it to hold 'vertsToBeConsidered' until the kd tree has been built in the next iteration.
            vertex_id += 1
            # some non sensical content for the second list of the dictionary, which is ok, and quicker to write, during the 'vertsToBeConsidered' phase.
            # only during the phase where the name 'extrusion_dictionary' actually fits, from identification of the extrusion until the actual extrusion, 
            # must it be an actual (Vector, count) tuple.
            extrusion_dictionary[vertex_id] = 0 
            
        # check if no attraction yet, and continue growing upwards if the case. (This must be after "extrusion according to dictionary",
        # because, it might add a nonsensical entry into the dictionary, that is just there so that the corresponding vertex is put into the kd tree.)
        if not vertsHaveBeenAttracted:
            geom = bmesh.ops.extrude_vert_indiv(T, verts = [T.verts[vertex_id]])
            new_vertex = geom['verts'][0]
            new_vertex[skin_layer].radius = (thickness, thickness)
            new_vertex.co += Vector((0,0, step))
            T.verts.ensure_lookup_table()
            
            vertex_id += 1
            extrusion_dictionary[vertex_id] = 0

        A = filter_attractors(A, attractors_toDelete_indices)
        
        thickness *= thickness_loss_factor
        if thickness < minThickness:
            thickness = minThickness
        
        growth_iteration += 1

    # put out the mesh.
    root_vertex[skin_layer].use_root = True
    
    mesh_data = bpy.data.meshes.new("SpaceColonizationMesh")
    T.to_mesh(mesh_data)
    
    T.free()
    
    obj = bpy.data.objects.new("SpaceColonizationTree", mesh_data)
    bpy.context.collection.objects.link(obj)
    
    return obj