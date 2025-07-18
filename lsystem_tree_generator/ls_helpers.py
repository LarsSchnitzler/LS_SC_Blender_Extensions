import bpy
import bmesh
from mathutils import Vector, Matrix
from collections import deque

def rule_condition(rule):
    if '=' in rule:
        return rule.split('=')[0]
    else:
        raise ValueError("Invalid rule: one rule does not have a '=' in it.")

def rule_content(rule):
    if '=' in rule:
        return rule.split('=')[1]
    else:
        raise ValueError("Invalid rule: one rule does not have a '=' in it.") 

def develop_string(axiom, rule1, rule2, rule3, iterations, stringLengthLimit):
    ruleArr = []
        
    if rule1 != '':
        r1_condition = rule_condition(rule1)
        r1_content = rule_content(rule1) 
        len_r1_condition = len(r1_condition)
        len_r1_content = len(r1_content)
        if len_r1_condition != 1:
            raise ValueError("Invalid rule 1: condition must be exactly one character.") 
        if len_r1_content == 0:
            raise ValueError("Invalid rule 1: content can't be nothing.")
        ruleArr.append(r1_condition)
        ruleArr.append(r1_content)
    
    if rule2 != '':
        r2_condition = rule_condition(rule2)
        r2_content = rule_content(rule2) 
        len_r2_condition = len(r2_condition)
        len_r2_content = len(r2_content)
        if len_r2_condition != 1:
            raise ValueError("Invalid rule 2: condition must be exactly one character.") 
        if len_r2_content == 0:
            raise ValueError("Invalid rule 2: content can't be nothing.")
        ruleArr.append(r2_condition)
        ruleArr.append(r2_content)
    
    if rule3 != '':
        r3_condition = rule_condition(rule3)
        r3_content = rule_content(rule3) 
        len_r3_condition = len(r3_condition)
        len_r3_content = len(r3_content)
        if len_r3_condition != 1:
            raise ValueError("Invalid rule 3: condition must be exactly one character.") 
        if len_r3_content == 0:
            raise ValueError("Invalid rule 3: content can't be nothing.")
        ruleArr.append(r3_condition)
        ruleArr.append(r3_content)
    
    len_ruleArr = len(ruleArr)    
    if len_ruleArr == 4:
        if ruleArr[0] == ruleArr[2]:
            raise ValueError("Conflicting rules: 2 rules have the same condition.")
    if len_ruleArr == 6:
        if ruleArr[0] == ruleArr[2] or ruleArr[2] == ruleArr[4] or ruleArr[0] == ruleArr[4]:
            raise ValueError("Conflicting rules: 2 or more rules have the same condition.")
        
    string = list(axiom)
    for _ in range(0, iterations):
        if len(string) > stringLengthLimit:
            raise Exception("The string length limit has been surpassed.")
        
        charIndex = 0
        while charIndex < len(string):
            char = string[charIndex]
            jump = 1
            for i in range(0, len(ruleArr), 2):
                condition = ruleArr[i]
                content = ruleArr[i + 1]
                if char == condition:
                    string[charIndex:charIndex + 1] = content # this replaces the current character with the a list of characters making up content.
                    jump = len(content)    
                    break
            charIndex += jump

    return ''.join(string)

class Turtle:
    def __init__(self, f, l, u, mesh_ref, initT, sl):
        self.mesh = mesh_ref

        self.root_vertex = self.mesh.verts.new((0,0,0))
        self.root_vertex[sl].radius = (initT, initT)
        
        self.current_vertex = self.root_vertex

        self.forward = Vector(f)
        self.left = Vector(l)
        self.up = Vector(u)

    def yaw(self, angle):
        rotation_matrix = Matrix.Rotation(angle, 4, self.up)
        self.forward.rotate(rotation_matrix)
        self.left.rotate(rotation_matrix)
        self.forward.normalize()
        self.left.normalize()

    def pitch(self, angle):
        rotation_matrix = Matrix.Rotation(angle, 4, self.left)
        self.forward.rotate(rotation_matrix)
        self.up.rotate(rotation_matrix)
        self.forward.normalize()
        self.up.normalize()

    def roll(self, angle):
        rotation_matrix = Matrix.Rotation(angle, 4, self.forward)
        self.up.rotate(rotation_matrix)
        self.left.rotate(rotation_matrix)
        self.up.normalize()
        self.left.normalize()

    def walk(self, distance, T, sl):
        geom = bmesh.ops.extrude_vert_indiv(self.mesh, verts=[self.current_vertex])
        new_vertex = geom['verts'][0]
        new_vertex[sl].radius = (T, T)
        
        extrusion_vector = self.forward * distance
        new_vertex.co += extrusion_vector
        
        self.current_vertex = new_vertex

def clamp(number, min_val, max_val):
    return max(min_val, min(number, max_val))

def draw_string(string, initialStepDistance, stepDecr, minimalStep, maximalStep, pitch_angle, roll_angle, yaw_angle, initialThickness, thickDecr, minimalThickness, maximalThickness):    
    bm = bmesh.new()
    skin_layer = bm.verts.layers.skin.verify() # returns the memory offset from the start of any given vertex datastructure in memory, to its skin data. At least, mentaly modeling it like that works.
    
    trtl = Turtle((0, 0, 1), (-1, 0, 0), (0, -1, 0), bm, initialThickness, skin_layer)

    vertex_refS = deque()
    forwardS = deque()
    leftS = deque()
    upS = deque()
    stepS = deque()
    thicknesseS = deque()

    step = initialStepDistance
    thickness = initialThickness
    
    for char in string:
        match char:
            case 'F':
                trtl.walk(step, thickness, skin_layer)
            case '+':
                trtl.pitch(pitch_angle)
            case '-':
                trtl.pitch(-pitch_angle)
            case '>':
                trtl.roll(roll_angle)
            case '<':
                trtl.roll(-roll_angle)
            case '/':
                trtl.yaw(yaw_angle)
            case '\\':
                trtl.yaw(-yaw_angle)
            case '$':
                step += stepDecr
                step = clamp(step, minimalStep, maximalStep)
            case '%':
                step -= stepDecr
                step = clamp(step, minimalStep, maximalStep)
            case '#':
                thickness += thickDecr
                thickness = clamp(thickness, minimalThickness, maximalThickness)
            case '!':
                thickness -= thickDecr
                thickness = clamp(thickness, minimalThickness, maximalThickness)
            case '[':
                vertex_refS.append(trtl.current_vertex)
                forwardS.append(trtl.forward.copy())
                leftS.append(trtl.left.copy())
                upS.append(trtl.up.copy())
                stepS.append(step)
                thicknesseS.append(thickness)
            case ']':
                if vertex_refS:
                    trtl.current_vertex = vertex_refS.pop()
                    trtl.forward = forwardS.pop()
                    trtl.left = leftS.pop()
                    trtl.up = upS.pop()
                    thickness = thicknesseS.pop()
                    step = stepS.pop()
                else:
                    print("WARNING: Unmatched ']' encountered, the stack is empty.")
            case _:
                pass
    
    trtl.root_vertex[skin_layer].use_root = True
    
    mesh_data = bpy.data.meshes.new("LSystemMesh")
    bm.to_mesh(mesh_data)
    bm.free()

    obj = bpy.data.objects.new("LSystemTree", mesh_data)
    bpy.context.collection.objects.link(obj)

    return obj