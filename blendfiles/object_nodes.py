# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>


bl_info = {
    'name': 'Object Node Mockups',
    'author': 'Lukas Tönne',
    'version': (1, 0, 0),
    "blender": (2, 77, 0),
    'location': '',
    'warning': '',
    'description': 'Object node dummies for 2.8 development proposal',
    'category': 'Development'}


import bpy, nodeitems_utils, contextlib
from bpy.types import Operator, NodeTree, Node, NodeSocket, PropertyGroup, Panel, UIList
from bpy.props import *
from nodeitems_utils import NodeCategory, NodeItem
from mathutils import *

def enum_property_copy(bpy_type, name, own_name=None):
    prop = bpy_type.bl_rna.properties[name]
    items = [(i.identifier, i.name, i.description, i.icon, i.value) for i in prop.enum_items]
    return EnumProperty(name=own_name if own_name else prop.name,
                        description=prop.description,
                        default=prop.default,
                        items=items)

def enum_property_value_prop(name):
    def fget(self):
        return self.bl_rna.properties[name].enum_items[getattr(self, name)].value
    return property(fget=fget)


# XXX utility enum to fake an ID selection button
bpy.types.Node.fake_id_ref = enum_property_copy(bpy.types.DriverTarget, "id_type", "Fake ID Ref")

def DummyIDRefProperty(**kw):
    return StringProperty(**kw)

def draw_dummy_id_ref(layout, data, prop):
    row = layout.row(align=True)
    row.alignment = 'LEFT'
    row.prop(data, "fake_id_ref", icon_only=True)
    row.prop(data, prop, text="")


###############################################################################


def node_category_item(items):
    def deco(cls):
        item = NodeItem(nodetype=cls.bl_idname)
        items.append(item)
        return cls

    return deco

_object_node_categories = dict()

def object_node_item(cat_name):
    global _object_node_categories
    cats = _object_node_categories
    
    if cat_name not in cats:
        cats[cat_name] = []
    items = cats[cat_name]
    
    return node_category_item(items)


###############################################################################


class DynamicSocketListNode:
    def update_socket_list(self, socketlist, insert=None):
        ntree = self.id_data

        # build map of connected inputs
        input_links = dict()
        for link in ntree.links:
            if link.to_node == self:
                input_links[link.to_socket] = (link, link.from_socket)

        # remove unconnected sockets
        for socket in socketlist:
            if socket not in input_links and socket != insert:
                socketlist.remove(socket)
            else:
                socket.is_placeholder = False

        # shift sockets to make room for a new link
        if insert is not None:
            nsocket = self.dynamic_socket_append(socketlist)
            for socket in reversed(socketlist[:-1]):
                link, from_socket = input_links.get(socket, (None, None))
                if link is not None:
                    ntree.links.remove(link)
                    ntree.links.new(from_socket, nsocket)
                nsocket = socket
                if socket == insert:
                    break

        socket = self.dynamic_socket_append(socketlist)
        socket.is_placeholder = True

    def init(self, context):
        if self.is_updating:
            return
        with self.update_lock():
            self.update_socket_list(self.inputs)

    def update(self):
        if self.is_updating:
            return
        with self.update_lock():
            self.update_socket_list(self.inputs)

    def insert_link(self, link):
        if self.is_updating:
            return
        with self.update_lock():
            self.update_socket_list(self.inputs, insert=link.to_socket)


###############################################################################


class NodeTreeBase():
    pass

class NodeBase():
    # XXX used to prevent reentrant updates due to RNA calls
    # this should be fixed in future by avoiding low-level update recursion on the RNA side
    is_updating = BoolProperty(options={'HIDDEN'})

    @contextlib.contextmanager
    def update_lock(self):
        self.is_updating = True
        try:
            yield
        finally:
            self.is_updating = False

###############################################################################


class ObjectNodeTree(NodeTreeBase, NodeTree):
    '''Object component nodes'''
    bl_idname = 'ObjectNodeTree'
    bl_label = 'Object Nodes'
    bl_icon = 'OBJECT_DATA'

    '''
    @classmethod
    def get_from_context(cls, context):
        ob = context.object
        if ob:
            return ob.node_tree, ob.node_tree, ob
        else:
            return None, None, None
    '''


class ObjectNodeBase(NodeBase):
    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'ObjectNodeTree'


###############################################################################
# Socket Types

class TransformSocket(NodeSocket):
    '''Affine 3D transformation'''
    bl_idname = 'TransformSocket'
    bl_label = 'Transform'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.59, 0.00, 0.67, 1.00)

class ObjectComponentSocket(NodeSocket):
    '''Object data component'''
    bl_idname = 'ObjectComponentSocket'
    bl_label = 'Component'

    is_readonly = BoolProperty(name="Read Only",
                               default=False)
    is_placeholder = BoolProperty(name="Is Placeholder",
                                  default=False)

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        if self.is_placeholder:
            alpha = 0.0
        elif self.is_readonly:
            alpha = 0.4
        else:
            alpha = 1.0
        return (1.0, 0.4, 0.216, alpha)


###############################################################################

# general-purpose list of component types and various associated strings:
# identifier, UI name, description, socket type, icon, default name
_component_types = [
    ('MESH', 'Mesh', 'Mesh data', 'ObjectComponentSocket', 'MESH_DATA', "Mesh"),
    ('FRACMESH', 'Fracture Mesh', 'Mesh with shard data', 'ObjectComponentSocket', 'MOD_TRIANGULATE', "FracMesh"),
    ('PARTICLES', 'Particles', 'Point data', 'ObjectComponentSocket', 'PARTICLE_DATA', "Particles"),
    ('POSE', 'Pose', 'Bone transformations pose', 'ObjectComponentSocket', 'POSE_DATA', "Pose"),
    ]
_component_types_set = { comp[0] for comp in _component_types }
_component_items = [ (comp[0], comp[1], comp[2], comp[4], i) for i, comp in enumerate(_component_types) ]
_component_icon = { comp[0] : comp[4] for comp in _component_types }
_component_default_name = { comp[0] : comp[5] for comp in _component_types }
class ObjectComponent(PropertyGroup):
    type = EnumProperty(name="Type",
                        description="Type of the component",
                        items=_component_items,
                        default='MESH',
                        )
def components_new(self, type, name):
    assert(type in _component_types_set)

    c = self.components.add()
    c.type = type
    if name:
        c.name = name
    else:
        c.name = _component_default_name[type]

class ObjectComponentSettings(PropertyGroup):
    space_type = EnumProperty(name="Space Type",
                              items=[('BUTS', "Properties", "", 'BUTS', 0)],
                              )

    def _context_type_items(self, context):
        items_base = [
        ("SCENE", "Scene", "Scene", 'SCENE_DATA', 0),
        ("RENDER", "Render", "Render", 'SCENE', 1),
        ("RENDER_LAYER", "Render Layers", "Render layers", 'RENDERLAYERS', 2),
        ("WORLD", "World", "World", 'WORLD', 3),
        ("OBJECT", "Object", "Object", 'OBJECT_DATA', 4),
        #("CONSTRAINT", "Constraints", "Object constraints", 'CONSTRAINT', 5),
        #("MODIFIER", "Modifiers", "Object modifiers", 'MODIFIER', 6),
        ("COMPONENTS", "Components", "Object data components", 'MOD_BUILD', 999),
        ("DATA", "Data", "Object data", 'MESH_DATA', 7),
        #("BONE", "Bone", "Bone", 'BONE_DATA', 8),
        #("BONE_CONSTRAINT", "Bone Constraints", "Bone constraints", 'CONSTRAINT_BONE', 9),
        ("MATERIAL", "Material", "Material", 'MATERIAL', 10),
        ("TEXTURE", "Texture", "Texture", 'TEXTURE', 11),
        #("PARTICLES", "Particles", "Particle", 'PARTICLES', 12),
        #("PHYSICS", "Physics", "Physics", 'PHYSICS', 13),
        ]
        return items_base
    context_type = EnumProperty(name="Context Type",
                                items=_context_type_items,
                                )
def register_object_components():
    Object = bpy.types.Object
    Object.component_settings = PointerProperty(type=ObjectComponentSettings)
    Object.components = CollectionProperty(type=ObjectComponent)
    Object.active_component = IntProperty(name="Active Component")
    Object.components_new = components_new

def unregister_object_components():
    Object = bpy.types.Object
    del Object.component_settings
    del Object.components
    del Object.active_component

class OBJECT_OT_add_component(Operator):
    """Add a data component to an object"""
    bl_idname = "object.add_component"
    bl_label = "Add Component"

    name = StringProperty(name="Name",
                          description="Name of the component",
                          )
    type = EnumProperty(name="Type",
                        description="Component Type",
                        items=_component_items,
                        )

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        ob = context.object
        ob.components_new(self.type, self.name)
        return {'FINISHED'}

class OBJECT_OT_remove_component(Operator):
    """Remove the active data component from an object"""
    bl_idname = "object.remove_component"
    bl_label = "Remove Component"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        ob = context.object
        ob.components.remove(ob.active_component)
        return {'FINISHED'}

class OBJECT_OT_move_component(Operator):
    """Move the active data component up or down"""
    bl_idname = "object.move_component"
    bl_label = "Move Component"

    direction = EnumProperty(name="Direction", items=[('UP', "Up", ""), ('DOWN', "Down", "")])

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        ob = context.object
        index = ob.active_component
        if self.direction == 'UP':
            index = max(ob.active_component - 1, 0)
        else:
            index = min(ob.active_component + 1, len(ob.components) - 1)
        ob.components.move(ob.active_component, index)
        ob.active_component = index
        return {'FINISHED'}

class OBJECT_UL_components(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.alignment = 'LEFT'
            row.label(text="", icon=_component_icon[item.type])
            row.prop(item, "name", text="", emboss=False)
        elif self.layout_type in {'GRID'}:
            layout.label(text="", icon_value=icon)

class FakeSpaceProperties(Panel):
    bl_label = "Fake Properties"
    bl_idname = "PROPERTIES_PT_fake_buttons"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    #bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        ob = context.object
        if not ob:
            return

        # fake button space header
        row = layout.row()
        row.alignment = 'LEFT'
        row.prop(ob.component_settings, "space_type", icon_only=True)
        row.prop(ob.component_settings, "context_type", expand=True, icon_only=True)

        layout.separator()

        row = layout.row()
        
        col = row.column()
        col.template_list("OBJECT_UL_components", "", ob, "components", ob, "active_component")
        
        col = row.column()
        col2 = col.column(align=True)
        col2.operator_menu_enum("object.add_component", "type", text="", icon='ZOOMIN')
        col2.operator("object.remove_component", text="", icon='ZOOMOUT')
        col2 = col.column(align=True)
        props = col2.operator("object.move_component", text="", icon='TRIA_UP')
        props.direction = 'UP'
        props = col2.operator("object.move_component", text="", icon='TRIA_DOWN')
        props.direction = 'DOWN'


###############################################################################


# for manually adding dummy component inputs
class AddComponentInput(Operator):
    bl_idname = "object_nodes.add_component_input"
    bl_label = "Add Component Input"
    bl_options = {'REGISTER', 'UNDO'}

    name = StringProperty(
            name="Name",
            )

    def execute(self, context):
        node = getattr(context, "node", None)
        if not node or not isinstance(node, ObjectNodeBase):
            return {'CANCELLED'}
        node.inputs.new('ObjectComponentSocket', self.name)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)


# for manually adding dummy component outputs
class AddComponentOutput(Operator):
    bl_idname = "object_nodes.add_component_output"
    bl_label = "Add Component Output"
    bl_options = {'REGISTER', 'UNDO'}

    name = StringProperty(
            name="Name",
            )

    def execute(self, context):
        # XXX doesn't work with popus #$*^@*#^%#$!!!
        #node = getattr(context, "node", None)
        node = context.active_node
        if not node or not isinstance(node, ObjectNodeBase):
            return {'CANCELLED'}
        node.outputs.new('ObjectComponentSocket', self.name)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)


@object_node_item('Mockups')
class ComponentsNode(ObjectNodeBase, Node):
    '''Object data components'''
    bl_idname = 'ObjectComponentsNode'
    bl_label = 'Components'

    def draw_buttons_ext(self, context, layout):
        layout.context_pointer_set("node", self)
        layout.operator("object_nodes.add_component_output")

    def init(self, context):
        # component outputs added manually for now
        pass


@object_node_item('Mockups')
class ValueFloatNode(ObjectNodeBase, Node):
    '''Floating point number'''
    bl_idname = 'ObjectValueFloatNode'
    bl_label = 'Float'

    value = FloatProperty(name="Value", default=0.0)

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="")

    def init(self, context):
        self.outputs.new('NodeSocketFloat', "Value")

@object_node_item('Mockups')
class ValueIntNode(ObjectNodeBase, Node):
    '''Integer number'''
    bl_idname = 'ObjectValueIntNode'
    bl_label = 'Integer'

    value = IntProperty(name="Value", default=0)

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="")

    def init(self, context):
        self.outputs.new('NodeSocketInt', "Value")

@object_node_item('Mockups')
class ValueVectorNode(ObjectNodeBase, Node):
    '''3D vector'''
    bl_idname = 'ObjectValueVectorNode'
    bl_label = 'Vector'

    value = FloatVectorProperty(name="Value", size=3, default=(0.0, 0.0, 0.0))

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "value", text="")

    def init(self, context):
        self.outputs.new('NodeSocketVector', "Value")

@object_node_item('Mockups')
class ValueColorNode(ObjectNodeBase, Node):
    '''RGBA color'''
    bl_idname = 'ObjectValueColorNode'
    bl_label = 'Color'

    value = FloatVectorProperty(name="Value", size=4, subtype='COLOR',
                                default=(0.0, 0.0, 0.0, 1.0), min=0.0, max=1.0)

    def draw_buttons(self, context, layout):
        layout.template_color_picker(self, "value", value_slider=True)

    def init(self, context):
        self.outputs.new('NodeSocketColor', "Value")


@object_node_item('Mockups')
class MathNode(ObjectNodeBase, Node):
    '''Math '''
    bl_idname = 'ObjectMathNode'
    bl_label = 'Math'

    _mode_items = [
        ('ADD_FLOAT', 'Add', '', 'NONE', 0),
        ('SUB_FLOAT', 'Subtract', '', 'NONE', 1),
        ('MUL_FLOAT', 'Multiply', '', 'NONE', 2),
        ('DIV_FLOAT', 'Divide', '', 'NONE', 3),
        ('SINE', 'Sine', '', 'NONE', 4),
        ('COSINE', 'Cosine', '', 'NONE', 5),
        ('TANGENT', 'Tangent', '', 'NONE', 6),
        ('ARCSINE', 'Arcsine', '', 'NONE', 7),
        ('ARCCOSINE', 'Arccosine', '', 'NONE', 8),
        ('ARCTANGENT', 'Arctangent', '', 'NONE', 9),
        ('POWER', 'Power', '', 'NONE', 10),
        ('LOGARITHM', 'Logarithm', '', 'NONE', 11),
        ('MINIMUM', 'Minimum', '', 'NONE', 12),
        ('MAXIMUM', 'Maximum', '', 'NONE', 13),
        ('ROUND', 'Round', '', 'NONE', 14),
        ('LESS_THAN', 'Less Than', '', 'NONE', 15),
        ('GREATER_THAN', 'Greater Than', '', 'NONE', 16),
        ('MODULO', 'Modulo', '', 'NONE', 17),
        ('ABSOLUTE', 'Absolute', '', 'NONE', 18),
        ('CLAMP', 'Clamp', '', 'NONE', 19),
        ('SQRT', 'Square Root', '', 'NONE', 20),
    ]
    mode = EnumProperty(name="Mode",
                        items=_mode_items)

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode")

    def init(self, context):
        self.inputs.new('NodeSocketFloat', "Value")
        self.inputs.new('NodeSocketFloat', "Value")
        self.outputs.new('NodeSocketFloat', "Value")


@object_node_item('Mockups')
class VectorMathNode(ObjectNodeBase, Node):
    '''Vector Math'''
    bl_idname = 'ObjectVectorMathNode'
    bl_label = 'Vector Math'

    _mode_items = [
        ('ADD_FLOAT3', 'Add', '', 'NONE', 0),
        ('SUB_FLOAT3', 'Subtract', '', 'NONE', 1),
        ('MUL_FLOAT3', 'Multiply', '', 'NONE', 2),
        ('DIV_FLOAT3', 'Divide', '', 'NONE', 3),
        ('AVERAGE_FLOAT3', 'Average', '', 'NONE', 4),
        ('DOT_FLOAT3', 'Dot Product', '', 'NONE', 5),
        ('CROSS_FLOAT3', 'Cross Product', '', 'NONE', 6),
        ('NORMALIZE_FLOAT3', 'Normalize', '', 'NONE', 7),
        ('LENGTH_FLOAT3', 'Vector Length', '', 'NONE', 8),
    ]
    mode = EnumProperty(name="Mode",
                        items=_mode_items)

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode")

    def init(self, context):
        self.inputs.new('NodeSocketVector', "Vector")
        self.inputs.new('NodeSocketVector', "Vector")
        self.outputs.new('NodeSocketVector', "Vector")
        self.outputs.new('NodeSocketFloat', "Value")


@object_node_item('Mockups')
class SeparateVectorNode(ObjectNodeBase, Node):
    '''Separate vector into elements'''
    bl_idname = 'ObjectSeparateVectorNode'
    bl_label = 'Separate Vector'

    def init(self, context):
        self.inputs.new('NodeSocketVector', "Vector")
        self.outputs.new('NodeSocketFloat', "X")
        self.outputs.new('NodeSocketFloat', "Y")
        self.outputs.new('NodeSocketFloat', "Z")


@object_node_item('Mockups')
class CombineVectorNode(ObjectNodeBase, Node):
    '''Combine vector from component values'''
    bl_idname = 'ObjectCombineVectorNode'
    bl_label = 'Combine Vector'

    def init(self, context):
        self.inputs.new('NodeSocketFloat', "X")
        self.inputs.new('NodeSocketFloat', "Y")
        self.inputs.new('NodeSocketFloat', "Z")
        self.outputs.new('NodeSocketVector', "Vector")

@object_node_item('Mockups')
class TranslationTransformNode(ObjectNodeBase, Node):
    '''Create translation from a vector'''
    bl_idname = 'ObjectTranslationTransformNode'
    bl_label = 'Translation Transform'

    def init(self, context):
        self.inputs.new('TransformSocket', "")
        self.inputs.new('NodeSocketVector', "Vector")
        self.outputs.new('TransformSocket', "")


@object_node_item('Mockups')
class GetTranslationNode(ObjectNodeBase, Node):
    '''Get translation vector from a transform'''
    bl_idname = 'ObjectGetTranslationNode'
    bl_label = 'Get Translation'

    def init(self, context):
        self.inputs.new('TransformSocket', "")
        self.outputs.new('NodeSocketVector', "Vector")


_euler_order_items = [
    ('XYZ', "XYZ", "", 0, 1),
    ('XZY', "XZY", "", 0, 2),
    ('YXZ', "YXZ", "", 0, 3),
    ('YZX', "YZX", "", 0, 4),
    ('ZXY', "ZXY", "", 0, 5),
    ('ZYX', "ZYX", "", 0, 6),
    ]
_prop_euler_order = EnumProperty(name="Euler Order", items=_euler_order_items, default='XYZ')

@object_node_item('Mockups')
class EulerTransformNode(ObjectNodeBase, Node):
    '''Create rotation from Euler angles'''
    bl_idname = 'ObjectEulerTransformNode'
    bl_label = 'Euler Transform'

    euler_order = _prop_euler_order
    euler_order_value = enum_property_value_prop('euler_order')

    def draw_buttons(self, context, layout):
        layout.prop(self, "euler_order")

    def init(self, context):
        self.inputs.new('TransformSocket', "")
        self.inputs.new('NodeSocketVector', "Euler Angles")
        self.outputs.new('TransformSocket', "")


class GetEulerNode(ObjectNodeBase, Node):
    '''Get euler angles from a transform'''
    bl_idname = 'ObjectGetEulerNode'
    bl_label = 'Get Euler Angles'

    euler_order = _prop_euler_order
    euler_order_value = enum_property_value_prop('euler_order')

    def draw_buttons(self, context, layout):
        layout.prop(self, "euler_order")

    def init(self, context):
        self.inputs.new('TransformSocket', "")
        self.outputs.new('NodeSocketVector', "Euler Angles")


@object_node_item('Mockups')
class AxisAngleTransformNode(ObjectNodeBase, Node):
    '''Create rotation from axis and angle'''
    bl_idname = 'ObjectAxisAngleTransformNode'
    bl_label = 'Axis/Angle Transform'

    def init(self, context):
        self.inputs.new('TransformSocket', "")
        self.inputs.new('NodeSocketVector', "Axis")
        self.inputs.new('NodeSocketFloat', "Angle")
        self.outputs.new('TransformSocket', "")


@object_node_item('Mockups')
class GetAxisAngleNode(ObjectNodeBase, Node):
    '''Get axis and angle from a transform'''
    bl_idname = 'ObjectGetAxisAngleNode'
    bl_label = 'Get Axis/Angle'

    def init(self, context):
        self.inputs.new('TransformSocket', "")
        self.outputs.new('NodeSocketVector', "Axis")
        self.outputs.new('NodeSocketFloat', "Angle")


@object_node_item('Mockups')
class ScaleTransformNode(ObjectNodeBase, Node):
    '''Create transform from a scaling vector'''
    bl_idname = 'ObjectScaleTransformNode'
    bl_label = 'Scale Transform'

    def init(self, context):
        self.inputs.new('TransformSocket', "")
        self.inputs.new('NodeSocketVector', "Scale")
        self.outputs.new('TransformSocket', "")


@object_node_item('Mockups')
class GetScaleNode(ObjectNodeBase, Node):
    '''Get scale from a transform'''
    bl_idname = 'ObjectGetScaleNode'
    bl_label = 'Get Scale'

    def init(self, context):
        self.inputs.new('TransformSocket', "")
        self.outputs.new('NodeSocketVector', "Scale")


@object_node_item('Mockups')
class RenderGeometryOutputNode(ObjectNodeBase, Node, DynamicSocketListNode):
    '''Render geometry output'''
    bl_idname = 'RenderGeometryOutputNode'
    bl_label = 'Render Output'

    def dynamic_socket_append(self, socketlist):
        socket = socketlist.new("ObjectComponentSocket", "")
        socket.is_readonly = True
        return socket

@object_node_item('Mockups')
class ViewportGeometryOutputNode(ObjectNodeBase, Node, DynamicSocketListNode):
    '''Viewport geometry output'''
    bl_idname = 'ViewportGeometryOutputNode'
    bl_label = 'Viewport Output'

    def dynamic_socket_append(self, socketlist):
        socket = socketlist.new("ObjectComponentSocket", "")
        socket.is_readonly = True
        return socket

@object_node_item('Mockups')
class ArmatureDeformNode(ObjectNodeBase, Node):
    '''Deform a mesh with an armature pose'''
    bl_idname = 'ArmatureDeformNode'
    bl_label = 'Armature Deform'

    armature = DummyIDRefProperty(name="Armature")

    def draw_buttons(self, context, layout):
        draw_dummy_id_ref(layout, self, "armature")

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Mesh")
        self.outputs.new('ObjectComponentSocket', "Mesh")

@object_node_item('Mockups')
class BoneConstraintsNode(ObjectNodeBase, Node):
    '''System of bone constraints'''
    bl_idname = 'BoneConstraintsNode'
    bl_label = 'Bone Constraints'

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Pose")
        self.outputs.new('ObjectComponentSocket', "Pose")

@object_node_item('Mockups')
class ExportComponentsNode(ObjectNodeBase, Node, DynamicSocketListNode):
    '''Export object components to a cache file'''
    bl_idname = 'ExportComponentsNode'
    bl_label = 'Export Components'

    cachefile = StringProperty(name="Cache File", subtype='FILE_PATH')

    def draw_buttons(self, context, layout):
        layout.prop(self, "cachefile")
        # dummy operator button
        layout.operator("render.render", text="Export")

    def dynamic_socket_append(self, socketlist):
        socket = socketlist.new("ObjectComponentSocket", "")
        socket.is_readonly = True
        return socket

@object_node_item('Mockups')
class ImportComponentsNode(ObjectNodeBase, Node):
    '''Import object data components from a cache file'''
    bl_idname = 'ImportComponentsNode'
    bl_label = 'Import Components'

    cachefile = StringProperty(name="Cache File", subtype='FILE_PATH')

    def draw_buttons(self, context, layout):
        layout.prop(self, "cachefile")

    def draw_buttons_ext(self, context, layout):
        self.draw_buttons(context, layout)

        layout.context_pointer_set("node", self)
        layout.operator("object_nodes.add_component_output")

    def init(self, context):
        # component outputs added manually for now
        pass

@object_node_item('Mockups')
class CacheComponentsNode(ObjectNodeBase, Node, DynamicSocketListNode):
    '''Cache object data components in a file'''
    bl_idname = 'CacheComponentsNode'
    bl_label = 'Cache Components'

    cachefile = StringProperty(name="Cache File", subtype='FILE_PATH')

    def draw_buttons(self, context, layout):
        layout.prop(self, "cachefile")
        # dummy operator button
        layout.operator("render.render", text="Export")

    def draw_buttons_ext(self, context, layout):
        self.draw_buttons(context, layout)

        layout.context_pointer_set("node", self)
        layout.operator("object_nodes.add_component_output")

    def dynamic_socket_append(self, socketlist):
        socket = socketlist.new("ObjectComponentSocket", "")
        return socket


@object_node_item('Mockups')
class ParticleInputNode(ObjectNodeBase, Node):
    '''Existing particles'''
    bl_idname = 'ParticleInputNode'
    bl_label = 'Particle Input'

    def init(self, context):
        self.outputs.new('ObjectComponentSocket', "Particles")

@object_node_item('Mockups')
class ParticleOutputNode(ObjectNodeBase, Node, DynamicSocketListNode):
    '''Define the new particle state after update'''
    bl_idname = 'ParticleOutputNode'
    bl_label = 'Particle Output'

    def dynamic_socket_append(self, socketlist):
        socket = socketlist.new("ObjectComponentSocket", "")
        socket.is_readonly = True
        return socket

@object_node_item('Mockups')
class CreateParticlesNode(ObjectNodeBase, Node):
    '''Create new particles over time'''
    bl_idname = 'CreateParticlesNode'
    bl_label = 'Create Particles'

    def _options_update(self, context):
        use_amount = self.use_fixed_amount
        use_rate = self.use_variable_rate
        if use_amount:
            self.inputs['Amount'].enabled = True
            self.inputs['Rate'].enabled = use_rate
            self.inputs["Frame Start"].enabled = not use_rate
            self.inputs["Frame End"].enabled = not use_rate
        else:
            self.inputs["Amount"].enabled = False
            self.inputs["Rate"].enabled = True
            self.inputs["Frame Start"].enabled = False
            self.inputs["Frame End"].enabled = False
    use_fixed_amount = BoolProperty(name="Use Fixed Amount",
                                     description="Create a fixed total number of particles",
                                     default=False,
                                     update=_options_update)
    use_variable_rate = BoolProperty(name="Use Variable Rate",
                                     description="Use a variable rate instead of a frame range",
                                     default=False,
                                     update=_options_update)

    def draw_buttons(self, context, layout):
        layout.prop(self, "use_fixed_amount")
        if self.use_fixed_amount:
            layout.prop(self, "use_variable_rate")

    def init(self, context):
        amount = self.inputs.new('NodeSocketInt', "Amount")
        amount.default_value = 1000
        rate = self.inputs.new('NodeSocketFloat', "Rate")
        rate.default_value = 10.0
        
        frame_start = self.inputs.new('NodeSocketInt', "Frame Start")
        frame_start.default_value = 1
        frame_end = self.inputs.new('NodeSocketInt', "Frame End")
        frame_end.default_value = 250
        
        self.outputs.new('ObjectComponentSocket', "Particles")

        self._options_update(context)

@object_node_item('Mockups')
class RandomSpherePointNode(ObjectNodeBase, Node):
    '''Get random points on a unit sphere'''
    bl_idname = 'RandomSpherePointNode'
    bl_label = 'Random Sphere Point'

    def init(self, context):
        self.inputs.new('NodeSocketInt', "Seed")
        self.outputs.new('NodeSocketVector', "point")

@object_node_item('Mockups')
class SomeParticleEmitterNode(ObjectNodeBase, Node):
    bl_idname = 'SomeParticleEmitterNode'
    bl_label = 'Some Particle Emitter'

    def init(self, context):
        self.outputs.new('ObjectComponentSocket', "Particles")

@object_node_item('Mockups')
class JoinParticlesNode(ObjectNodeBase, Node, DynamicSocketListNode):
    bl_idname = 'JoinParticlesNode'
    bl_label = 'Join Particles'

    def init(self, context):
        super().init(context)

        self.outputs.new('ObjectComponentSocket', "")

    def dynamic_socket_append(self, socketlist):
        socket = socketlist.new("ObjectComponentSocket", "")
        return socket

@object_node_item('Mockups')
class SplitParticlesNode(ObjectNodeBase, Node):
    bl_idname = 'SplitParticlesNode'
    bl_label = 'Split Particles'

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Particles")
        self.inputs.new('NodeSocketInt', "Condition")
        self.outputs.new('ObjectComponentSocket', "True")
        self.outputs.new('ObjectComponentSocket', "False")

@object_node_item('Mockups')
class MeshSurfaceSampleNode(ObjectNodeBase, Node):
    '''Get random points on a mesh surface'''
    bl_idname = 'MeshSurfaceSampleNode'
    bl_label = 'Mesh Surface Sample'

    surface_object = DummyIDRefProperty(name="Surface Object")

    def draw_buttons(self, context, layout):
        draw_dummy_id_ref(layout, self, "surface_object")

    def init(self, context):
        self.inputs.new('NodeSocketInt', "Seed")
        self.outputs.new('NodeSocketVector', "Point")
        self.outputs.new('NodeSocketVector', "Vertex Weights")

@object_node_item('Mockups')
class MeshSurfaceTrackNode(ObjectNodeBase, Node):
    '''Evaluate sample point on a deformed mesh surface'''
    bl_idname = 'MeshSurfaceTrackNode'
    bl_label = 'Mesh Surface Track'

    surface_object = DummyIDRefProperty(name="Surface Object")

    def draw_buttons(self, context, layout):
        draw_dummy_id_ref(layout, self, "surface_object")

    def init(self, context):
        self.inputs.new('NodeSocketVector', "Vertex Weights")
        self.outputs.new('NodeSocketVector', "Point")

@object_node_item('Mockups')
class VolumeSampleNode(ObjectNodeBase, Node):
    '''Get random points in volume grid'''
    bl_idname = 'VolumeSampleNode'
    bl_label = 'Volume Sample'

    volume_object = DummyIDRefProperty(name="Volume Object")

    def draw_buttons(self, context, layout):
        draw_dummy_id_ref(layout, self, "volume_object")

    def init(self, context):
        self.inputs.new('NodeSocketInt', "Seed")
        self.outputs.new('NodeSocketVector', "Point")


@object_node_item('Mockups')
class ParticleBillboardsNode(ObjectNodeBase, Node):
    '''Create a billboard mesh from particles'''
    bl_idname = 'ParticleBillboardsNode'
    bl_label = 'Particle Billboards'

    align = enum_property_copy(bpy.types.ParticleSettings, "billboard_align", "Alignment")

    def draw_buttons(self, context, layout):
        layout.prop(self, "align")

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Particles")
        self.outputs.new('ObjectComponentSocket', "Mesh")

@object_node_item('Mockups')
class MakeObjectDuplisNode(ObjectNodeBase, Node):
    '''Create object instances from particles'''
    bl_idname = 'MakeObjectDuplisNode'
    bl_label = 'Make Object Duplis'

    object = DummyIDRefProperty(name="Object", description="Object to instantiate")

    def draw_buttons(self, context, layout):
        draw_dummy_id_ref(layout, self, "object")

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Particles")
        self.inputs.new('TransformSocket', "Transform")
        self.outputs.new('ObjectComponentSocket', "Instances")


@object_node_item('Mockups')
class HairSimNode(ObjectNodeBase, Node):
    '''Hair simulation'''
    bl_idname = 'HairSimNode'
    bl_label = 'Hair Simulation'

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Hair")
        self.outputs.new('ObjectComponentSocket', "Hair")

@object_node_item('Mockups')
class ApplyIslandTransformsNode(ObjectNodeBase, Node):
    '''Apply mesh island transforms from particles'''
    bl_idname = 'ObjectApplyMeshIslandsTransformNode'
    bl_label = 'Apply Island Transforms'

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Particles").is_readonly = True
        self.inputs.new('ObjectComponentSocket', "Fracture Mesh").is_readonly = True
        self.outputs.new('ObjectComponentSocket', "Mesh")

@object_node_item('Mockups')
class ParticleRigidBodySimNode(ObjectNodeBase, Node):
    '''Define particles as rigid bodies in the scene'''
    bl_idname = 'ObjectParticleRigidBodySimNodeNode'
    bl_label = 'Particle Rigid Body Simulation'

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Particles")
        self.inputs.new('ObjectComponentSocket', "Fracture Mesh").is_readonly = True
        self.outputs.new('ObjectComponentSocket', "RB Particles")

@object_node_item('Mockups')
class DynamicFractureNode(ObjectNodeBase, Node):
    '''Fracture shards based on collision impacts'''
    bl_idname = 'ObjectDynamicFractureNodeNode'
    bl_label = 'Dynamic Fracture'

    def init(self, context):
        self.inputs.new('ObjectComponentSocket', "Particles")
        self.inputs.new('ObjectComponentSocket', "Fracture Mesh")
        self.outputs.new('ObjectComponentSocket', "Particles")
        self.outputs.new('ObjectComponentSocket', "Fracture Mesh")

def make_attribute_nodes(attribute_set, attr_default, data_name, data_type):
    def attribute_items(self, context):
        return [(attr[0], attr[0], "", 'NONE', 2**i) for i, attr in enumerate(attribute_set)]

    def update_attributes(self, context):
        for socket in self.outputs:
            socket.enabled = (socket.name in self.attributes)

    @object_node_item('Mockups')
    class get_node(ObjectNodeBase, Node):
        __doc__ = "Get attribute from %s" % data_name
        bl_idname = "Get%sAttributeNode" % data_name
        bl_label = "Get %s Attribute" % data_name

        attributes = EnumProperty(name="Attribute",
                                  items=attribute_items,
                                  update=update_attributes,
                                  options={'ENUM_FLAG'})

        def draw_buttons(self, context, layout):
            layout.prop_menu_enum(self, "attributes")

        def init(self, context):
            self.inputs.new(data_type, data_name).is_readonly = True
            for attr in attribute_set:
                self.outputs.new(attr[1], attr[0])

            # set default
            self.attributes = { attr_default }

    @object_node_item('Mockups')
    class set_node(ObjectNodeBase, Node):
        __doc__ = "Set attribute of %s" % data_name
        bl_idname = "Set%sAttributeNode" % data_name
        bl_label = "Set %s Attribute" % data_name

        def update_attributes(self, context):
            for socket in self.inputs[1:]:
                socket.enabled = (socket.name in self.attributes)
        attributes = EnumProperty(name="Attribute",
                                  items=attribute_items,
                                  update=update_attributes,
                                  options={'ENUM_FLAG'})

        def draw_buttons(self, context, layout):
            layout.prop_menu_enum(self, "attributes")

        def init(self, context):
            self.inputs.new(data_type, data_name)
            for attr in attribute_set:
                self.inputs.new(attr[1], attr[0])
            self.outputs.new(data_type, data_name)

            # set default
            self.attributes = { attr_default }

    return get_node, set_node

_mesh_attribute_set = [
    ("vertex.location", 'NodeSocketVector'),
    ("vertex.shard", 'NodeSocketInt'),
    ]
GetMeshAttributeNode, SetMeshAttributeNode = \
    make_attribute_nodes(_mesh_attribute_set, 'vertex.location',
                         "Mesh", 'ObjectComponentSocket')

_particle_attribute_set = [
    ("id", 'NodeSocketInt'),
    ("location", 'NodeSocketVector'),
    ("velocity", 'NodeSocketVector'),
    ("origin", 'NodeSocketVector'),
    ]
GetParticlesAttributeNode, SetParticlesAttributeNode = \
    make_attribute_nodes(_particle_attribute_set, 'location',
                         "Particles", 'ObjectComponentSocket')

@object_node_item('Mockups')
class DefineRigidBodyNode(ObjectNodeBase, Node):
    '''Define rigid bodies for simulation'''
    bl_idname = 'DefineRigidBodyNode'
    bl_label = 'Define Rigid Body'

    def init(self, context):
        self.inputs.new('NodeSocketInt', "ID")
        self.inputs.new('TransformSocket', "transform")
        self.inputs.new('NodeSocketVector', "velocity")
        self.inputs.new('NodeSocketVector', "angular velocity")
        self.outputs.new('TransformSocket', "transform")
        self.outputs.new('NodeSocketVector', "velocity")
        self.outputs.new('NodeSocketVector', "angular velocity")

@object_node_item('Mockups')
class CacheRigidBodyContactsNode(ObjectNodeBase, Node):
    '''Contacts of rigid bodies from the collision step'''
    bl_idname = 'CacheRigidBodyContactsNode'
    bl_label = 'Cache Rigid Body Contacts'

    def init(self, context):
        self.inputs.new('NodeSocketInt', "ID")
        self.outputs.new('ObjectComponentSocket', "contacts")

@object_node_item('Mockups')
class FindMaxImpactNode(ObjectNodeBase, Node):
    '''Find the contact with maximum impact force'''
    bl_idname = 'FindMaxImpactNode'
    bl_label = 'Find Maximum Impact'

    def init(self, context):
        self.inputs.new('NodeSocketInt', "ID")
        self.inputs.new('ObjectComponentSocket', "contacts")
        self.outputs.new('NodeSocketVector', "max impact")

@object_node_item('Mockups')
class SingleImpactFractureNode(ObjectNodeBase, Node):
    '''Fracture shards based on a single impact'''
    bl_idname = 'SingleImpactFractureNode'
    bl_label = 'Single Impact Fracture'

    def init(self, context):
        self.inputs.new('NodeSocketVector', "impact")
        self.inputs.new('NodeSocketFloat', "threshold")
        self.inputs.new('ObjectComponentSocket', "particles")
        self.inputs.new('ObjectComponentSocket', "shards")
        self.outputs.new('ObjectComponentSocket', "particles")
        self.outputs.new('ObjectComponentSocket', "shards")

@object_node_item('Mockups')
class MapValueNode(ObjectNodeBase, Node):
    '''Use an index to map values to a new index domain'''
    bl_idname = 'MapValueNode'
    bl_label = 'Map Value'

    def init(self, context):
        self.inputs.new('NodeSocketInt', "index")
        self.inputs.new('TransformSocket', "values")
        self.outputs.new('TransformSocket', "mapped values")

@object_node_item('Mockups')
class ApplyTransformNode(ObjectNodeBase, Node):
    '''Apply transform to a vector'''
    bl_idname = 'ApplyTransformNode'
    bl_label = 'Apply Transform'

    def init(self, context):
        self.inputs.new('TransformSocket', "transform")
        self.inputs.new('NodeSocketVector', "vector")
        self.outputs.new('NodeSocketVector', "vector")


###############################################################################


# our own base class with an appropriate poll function,
# so the categories only show up in our own tree type
class ObjectNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        tree = context.space_data.edit_tree
        return tree and tree.bl_idname == 'ObjectNodeTree'


class ObjectNodesNew(Operator):
    """Create new object node tree"""
    bl_idname = "object_nodes.object_nodes_new"
    bl_label = "New"
    bl_options = {'REGISTER', 'UNDO'}

    name = StringProperty(
            name="Name",
            )

    def execute(self, context):
        return bpy.ops.node.new_node_tree(type='ObjectNodeTree', name="ObjectNodes")


class ObjectNodeEdit(Operator):
    """Open a node for editing"""
    bl_idname = "object_nodes.node_edit"
    bl_label = "Edit"
    bl_options = {'REGISTER', 'UNDO'}

    exit = BoolProperty(name="Exit", description="Exit current node tree", default=False)

    @staticmethod
    def get_node(context):
        if hasattr(context, "node"):
            return context.node
        else:
            return getattr(context, "active_node", None)

    @classmethod
    def poll(cls, context):
        space = context.space_data
        if space.type != 'NODE_EDITOR':
            return False
        treetype = getattr(bpy.types, space.tree_type)
        if not issubclass(treetype, NodeTreeBase):
            return False
        return True

    def execute(self, context):
        space = context.space_data
        node = self.get_node(context)
        has_tree = node and node.id and isinstance(node.id, NodeTreeBase)
        exit = self.exit or not has_tree

        if exit:
            space.path.pop()
        else:
            space.path.append(node.id, node)

        return {'FINISHED'}


###############################################################################


keymaps = []

def register():
    global _object_node_categories

    bpy.utils.register_module(__name__)
    register_object_components()

    node_categories = []
    for name, items in _object_node_categories.items():
        cat = ObjectNodeCategory(name.upper(), name, items=items)
        node_categories.append(cat)
    nodeitems_utils.register_node_categories("OBJECT_NODES", node_categories)

    # create keymap
    wm = bpy.context.window_manager
    km = wm.keyconfigs.default.keymaps.new(name="Node Generic", space_type='NODE_EDITOR')
    
    kmi = km.keymap_items.new(bpy.types.OBJECT_NODES_OT_node_edit.bl_idname, 'TAB', 'PRESS')
    kmi.properties.exit = False
    
    kmi = km.keymap_items.new(bpy.types.OBJECT_NODES_OT_node_edit.bl_idname, 'TAB', 'PRESS', ctrl=True)
    kmi.properties.exit = True
    
    keymaps.append(km)

def unregister():
    nodeitems_utils.unregister_node_categories("OBJECT_NODES")

    # remove keymap
    wm = bpy.context.window_manager
    for km in keymaps:
        wm.keyconfigs.default.keymaps.remove(km)
    keymaps.clear()

    unregister_object_components()
    bpy.utils.unregister_module(__name__)
