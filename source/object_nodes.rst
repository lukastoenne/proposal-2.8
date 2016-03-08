************
Object Nodes
************

Objects are without doubt the most ubiquitous containers of data in Blender. The storage and processes for generating data in objects are very incoherent:

* Direct attributes: obmat, parenting, visibility, layers, BGE settings, ...

  (most ancient features)

* Optional pointers: Pose data, Proxy links, Sculpt data, Softbody, …
* Lists/Stacks: Modifiers, Constraints, Particle Systems, ...

Stack-based process descriptions are generally inflexible. While parts can be combined and reordered, the individual parts themselves are usually quite complex and hard-coded. Adding or extending functionality leads to “feature creep”: The only way to express new behavior is to add more buttons, and one ends up with overstuffed and incomprehensible panels. More features in turn cause incompatible settings and broken corner cases.

Nodes promise to avoid these problems:

* Sockets and explicit connections allow reusing components beyond simple chains
* Node groups help to organize sets of nodes behind a custom interface
* Basic nodes can become small and concise, larger features work like node groups
* Artists can start with a clean slate or a minimal default setup, then just add what is needed
* Small-scale nodes enforce stateless code without side-effects

Components
----------

To describe common features of data in objects, "components" are introduced. An object component is

* optional:


Workflow Case Studies
---------------------

.. _simple_animation_nodes:

Simple Animation Workflow
==========================

.. note:: linking issues are ignored here, everything assumed to be local, no proxies needed!

1. By default the mesh component (``Mesh`` object data block) is used as render output directly.

.. figure:: /images/animation_workflow_base1.png
 :width: 60%
 :figclass: align-center

2. Armature node deforms the mesh using the Armature object. The Armature object has a pose component. Note that the armature object is not connected to a render node or viewport node, so it will just display bone poses by default.
   .. note:: Proxies would override this pose component, even though it is locked when using a linked object.

.. figure:: /images/animation_workflow_base2.png
 :width: 60%
 :figclass: align-center

3. Rigging workflow can also happen with nodes: The Armature object's "Pose" component contains a node network representing bone constraints.

  .. todo:: It's unclear how this should work in detail. The 'Bone Constraints' node is like a group containing individual constraints.

.. figure:: /images/animation_workflow_base3.png
 :width: 60%
 :figclass: align-center

4. Animate!

  Moving bones in pose mode changes pose bone transforms (in the "Pose" component). Keyframes are stored in the Armature object's animation data.

.. figure:: /images/animation_workflow_base4.png
 :width: 60%
 :figclass: align-center
