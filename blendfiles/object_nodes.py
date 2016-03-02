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


import bpy
import nodeitems_utils
from bpy.types import Operator, NodeTree, Node, NodeSocket
from bpy.props import *
from nodeitems_utils import NodeCategory, NodeItem
from mathutils import *

def enum_property_copy(bpy_type, name):
    prop = bpy_type.bl_rna.properties[name]
    items = [(i.identifier, i.name, i.description, i.icon, i.value) for i in prop.enum_items]
    return EnumProperty(name=prop.name,
                        description=prop.description,
                        default=prop.default,
                        items=items)

def enum_property_value_prop(name):
    def fget(self):
        return self.bl_rna.properties[name].enum_items[getattr(self, name)].value
    return property(fget=fget)


###############################################################################


def node_category_item(items):
    def deco(cls):
        item = NodeItem(nodetype=cls.bl_idname)
        items.append(item)

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
    def add_extender(self, socketlist, sockettype):
        socket = socketlist.new(sockettype, "")
        socket.is_placeholder = True
        return socket

    def update_socket_list(self, socketlist, sockettype, insert=None):
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
            socketlist.new(sockettype, "")
            nsocket = socketlist[-1]
            for socket in reversed(socketlist[:-1]):
                link, from_socket = input_links.get(socket, (None, None))
                if link is not None:
                    ntree.links.remove(link)
                    ntree.links.new(from_socket, nsocket)
                nsocket = socket
                if socket == insert:
                    break

        self.add_extender(socketlist, sockettype)

    def compile_socket_list(self, compiler, socketlist, passtype, jointype, valuetype):
        ntree = self.id_data

        # list of connected inputs
        used_inputs = set()
        for link in ntree.links:
            if link.to_node == self:
                used_inputs.add(link.to_socket)
        # make a sorted index list
        used_inputs = [ i for i,socket in enumerate(socketlist) if socket in used_inputs ]

        if len(used_inputs) > 0:
            node = compiler.add_node(passtype)
            compiler.map_input(used_inputs[0], node.inputs[0])
            result = node.outputs[0]
        
            for index in used_inputs[1:]:
                node = compiler.add_node(jointype)
                compiler.link(result, node.inputs[0])
                compiler.map_input(index, node.inputs[1])
                result = node.outputs[0]

        else:
            node = compiler.add_node(valuetype)
            result = node.outputs[0]

        return result


###############################################################################


class NodeTreeBase():
    pass

class NodeBase():
    pass


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

    is_readonly = BoolProperty(name="Is Placeholder",
                               default=False)

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        alpha = 0.4 if self.is_readonly else 1.0
        return (1.0, 0.4, 0.216, alpha)


###############################################################################


@object_node_item('Mockups')
class ComponentsNode(ObjectNodeBase, Node):
    '''Object data components'''
    bl_idname = 'ObjectComponentsNode'
    bl_label = 'Components'

    def init(self, context):
        self.outputs.new('ObjectComponentSocket', "Particles")
        self.outputs.new('ObjectComponentSocket', "Fracture Mesh")

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

    bpy.utils.unregister_module(__name__)
