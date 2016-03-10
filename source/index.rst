.. proposal-2.8 documentation master file, created by
   sphinx-quickstart on Tue Mar  1 11:11:52 2016.

Proposal for Caching, Nodes and Physics Development in Blender 2.8
==================================================================

For the 2.8 development cycle of Blender some major advances are planned in the way animations, simulations and caches are connected by node systems.

It has become clear during past projects that the increased complexity of pipelines including Blender requires much better ways of exporting and importing data. Such use of external caches for data can help to integrate Blender into mixed pipelines with other software, but also simplify Blender-only pipelines by separating stages of production.

Nodes should become a much more universal tool for combining features in Blender. The limits of stack-based configurations have been reached in many areas such as modifiers and simulations. Nodes are much more flexible for tailoring tools to user needs, e.g. by creating groups, branches and interfaces.

Physical simulations in Blender need substantial work to become more usable in productions. Improved caching functionality and a solid node-based framework are important prerequisites. Physics simulations must become part of user tools for rigs and mesh editing, rather than abstract stand-alone concepts. Current systems for fluid and smoke simulation in particular should be supplemented or replaced by more modern techniques which have been developed in recent years.

Contents:

.. toctree::
   :maxdepth: 1

   pipeline.rst
   object_nodes.rst
   caching.rst
   fracture.rst
   todo.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

