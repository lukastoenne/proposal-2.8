*********
Particles
*********

Overview
--------

Typical use cases for particles include:

.. _blenderdiplom: http://www.blenderdiplom.com/en/shop/611-point-density-magical-fx.html
.. _frozen_snow: https://www.youtube.com/watch?v=9H1gRQ6S7gg

+----------------------------------------------------------+-----------------------------------------------------------+
| .. image:: /images/placeholder.png                       | .. image:: /images/placeholder.png                        |
|   :width: 100%                                           |   :width: 100%                                            |
|                                                          |                                                           |
| Billboards for inexpensive dust, rain or snow            | Instancing large numbers of plants                        |
|                                                          |                                                           |
| .. todo:: Sintel rain/sand/debris?                       | .. todo:: CL grass fields                                 |
|                                                          |                                                           |
+----------------------------------------------------------+-----------------------------------------------------------+
| .. image:: /images/placeholder.png                       | .. image:: /images/placeholder.png                        |
|   :width: 100%                                           |   :width: 100%                                            |
|                                                          |                                                           |
| Rigid Body simulation with collision                     | Crowd simulation                                          |
|                                                          |                                                           |
| .. todo:: ToS robot wall smash                           | .. todo:: any nice examples made with Blender? Alike?     |
|                                                          |                                                           |
+----------------------------------------------------------+-----------------------------------------------------------+
| .. image:: /images/placeholder.png                       | .. image:: /images/placeholder.png                        |
|   :width: 100%                                           |   :width: 100%                                            |
|                                                          |                                                           |
| Volumetric textures (point density)                      | Point clouds for deep compositing                         |
|                                                          |                                                           |
| .. todo:: blenderdiplom_                                 | .. todo:: ??                                              |
|                                                          |                                                           |
+----------------------------------------------------------+-----------------------------------------------------------+
| .. image:: /images/placeholder.png                       | .. image:: /images/placeholder.png                        |
|   :width: 100%                                           |   :width: 100%                                            |
|                                                          |                                                           |
| Smoke or fluid emission                                  | Smoothed Particle Hydrodynamics (SPH)                     |
|                                                          |                                                           |
| .. todo:: GB tornado shot                                | .. todo:: remove this? never seen a working example ...   |
|                                                          |                                                           |
+----------------------------------------------------------+-----------------------------------------------------------+
| .. image:: /images/placeholder.png                       | .. image:: /images/placeholder.png                        |
|   :width: 100%                                           |   :width: 100%                                            |
|                                                          |                                                           |
| Marker-and-Cell (MAC) methods for fluid sim              | Squishy materials like snow, mud or foam                  |
|                                                          |                                                           |
| .. todo:: loads of examples around, just not Blender     | .. todo:: frozen_snow_                                    |
|                                                          |                                                           |
+----------------------------------------------------------+-----------------------------------------------------------+

Particle Data and State
=======================

Particles are discrete points in space with a number of associated attributes (data layers). A few attributes are found in all particle systems, like:

* Position
* Index (a uniquely identifying number for each particle)

Other attributes may or may not exist for a given particle set, depending on its uses and requirements, such as:

* Orientation and Scale, e.g. for instancing
* Velocity and Angular Velocity for physical particle simulation
* Object Reference: an identifier for instancing or rigid body shapes (actual pointers are stored separately in a lookup table)
* Color can be ascribed to each particle for the rendering purposes (Cosmos Laundromat tornado uses colored particles)
* Other physical properties may be used by specialized simulations: Size, Heat, Charge, ...

Most particle attributes can change over time. Any concrete set of particles can therefore only be a snapshot for a particular frame. This is called a particle "state".

The scene in Blender stores a "current state" of particles, which relates to the "current frame" of that scene in the viewport. But other states may be stored or used temporarily:

* Renderers can request a scene state for any arbitrary frame. For motion blur this also includes subframes.
* Simulating over a frame range generates a sequence of states. In current Blender sims the scene frame is actively changed with each iteration, but particles could be calculated on their own with a local state without touching the scene state.

Caches are commonly used to store each frame's state during simulation. The scene can then use the cache to look up the "current" state efficiently.

Extra Topology Elements
=======================
.. todo:: topology (mesh as particles), edge data (SPH)


Workflow Examples: Emitting Particles
-------------------------------------

Plain Particles at a specific frame
===================================

1. Create Particle Component + node tree
2. Node "Create Particles": simple way to add N particles on a specific frame

Emitting particles over time
============================

1. Node "Emit Particles" creates particles over time.
2. Emission rate can either be a variable emission rate or emit a total amount.

Combining existing and newly emitted particles
==============================================

1. Output of basic emitter nodes contains only particles created in that particular frame
2. New particles can be joined with existing particles to form the next particle state
3. Joined particle sets can also be handled in the same frame right after creating new particles, if needed. For instance, one may want to adjust new particles' positions to achieve a uniform density at all times at the end of each update.

Initializing new particles
==========================

1. Emitter node output contains default particles: all positions are ``(0, 0, 0)``.
2. Assign a random position on the unit sphere to each new particle, using the particle index as a seed value.
3. Other particle attributes may be initialized in a similar manner, using the "Set Attribute" node.

Distributing particles on a mesh surface
========================================

1. Random samples on a mesh surface can be created with a "Sample Mesh Surface" node. Again, the particle index serves as a seed value to create a unique value for each particle.
2. Relation of particles to mesh vertices stored as a particle attribute! This allows particles to "track" a mesh surface when it gets deformed, for example.
3. The particle positions can be continually updated by re-evaluating the stored mesh surface samples. Other useful techniques could be texture or normals interpolation.

Distributing particles in a volume
==================================

1. Similar to mesh surfaces, a volume (like a smoke density grid) can be sampled as well.
2. Samples inside a volume are not as meaningful as surface samples. Tracking positions a volume is more ambiguous than tracking a mesh surface and requires support by a physics solver system. See `Workflow Examples: Simulating Particles`_ for examples.

.. note:: Tracking mesh surfaces is easy because the surface is *defined* by the vertices. Every point on the surface is a linear combination of vertex position vectors (or other attributes), so all we need to do to reconstruct a point on a deformed surface is to store the weights per vertex.
   
   Most volumes don't have a linearization equivalent to mesh surfaces, so there is no direct mapping to a "deformed" volume. Volumetric simulations use integrators to advect particles through a gradient field iteratively.


Workflow Examples: Rendering Particles
--------------------------------------

Particles are an incredibly flexible tool for controlling renderable entities in a scene. Particles themselves are not actually renderable due to their point-like nature. They serve as the basis for other effects to produce renderable geometry.

Billboards
==========

Billboards consist of a simple quad faces generated for each particle. They typically are facing the camera, which provides a cheap way to render uniform "blobs" of matter. The most efficient implementation of billboards is probably through mesh faces.

1. "Billboards" node takes a particle system and generates a mesh.

Instancing Objects
==================

1. "Make Duplis" node takes a particle system and generates a list of object instances (aka. "Dupli List").
2. Like many other complex nodes, "Make Duplis" can be copied and modified for non-standard behavior by editing it like a node group.

Fluid Surface Generation
========================

A more sophisticated method of creating a mesh out of particle data, especially for simulating liquids. Each particle is surrounded by falloff function, the sum of all particle functions defines an implicit surface. `Level Set methods <https://en.wikipedia.org/wiki/Level_set_method>`_ can be used to discretize this surface. Thin sheets of fluid can be handled with methods such as [MUS14]_.

1. "Particle Surface" takes a particle input and outputs a mesh.

Point Density
=============

1. "Point Density" node outputs a special volumetric component, which is renderable.
2. Different point density features such as color and falloff may be defined through inputs.

Deep Compositing
================

.. todo:: Integration into the compositing workflow is unclear


Workflow Examples: Simulating Particles
---------------------------------------

Point Masses
============

Simulating particles as point masses is a comparatively cheap way of producing physical motion. Collision with other objects is limited to the particle center, and self-collision is not possible efficiently. This limits the usefulness of point mass simulation, but it can still serve a purpose in motion graphics, and is included here for its very simplicity.

1. "Simulate Points" node changes only the particle position (no rotational dynamics).
2. Collision in this case is one-way only: Particles can collide with meshes in the scene, but will not have any effect in turn on other objects. For two-way interaction between objects a fully fledged rigid body simulation must be used.

Rigid Bodies
============

1. "Define Rigid Body" registers a rigid body object with the Bullet physics engine. After the physics step the rigid body's location and rotation are then copied back to the particle.
2. The collision shape for rigid bodies can be either a mesh or an implicit primitive shape. Primitive shapes are useful for massive simulations with thousands of colliding objects where full mesh collision would be too costly. Here we use an external object reference to define the shape.
3. For rendering an instancing node is very suitable in this case. It can use the same object as the collision shape (or a more detailed version) to make physics and visuals match.

Fracturing
==========

This workflow is defined in more detail in :ref:`fracture_simulation`.

Fluid Simulation with Particles
===============================

Modern fluid VFX in movie productions and the like is almost exclusively of a "lagrangian" type, meaning that the rendering is based on particle/mesh data rather than directly using density grids. Particles are used as "markers" which are carried along (advected) with the fluid and thus "track" the fluid surface. This approach has the advantage of being very efficient, as well as allowing much more visual detail than would be possible with grids alone. Grids are still an indispensable part of the simulation, but they are used in conjunction with particles to utilize the best of both worlds.



.. note:: Smoothed Particle Hydrodynamics (SPH) is not very useful for simulation purposes in CG. The computational cost is far too great compared to modern lagrangian methods such as FLIP. In it's current implementation in Blender it also tends to become unstable quickly. It should therefore be considered of only theoretical interest.


Workflow Examples: Editing Particles
------------------------------------

.. todo:: Here could be some cases of editing a single particle state as well as potential cache editing features.

.. [MUS14] K. Museth, “A Flexible Image Processing Approach to the Surfacing of Particle-Based Fluid animation”, Mathematical Progress in Expressive Image Synthesis I, Springer Japan,  ISBN 978-4-431-55006-8, Volume 4, pp 81-84, 2014.
