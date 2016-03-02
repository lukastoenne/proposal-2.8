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

Where should nodes be hooked into Blender?
------------------------------------------

Current nodes:

* shader/material nodes: used when the renderer calculates a surface/volume sample
* texture nodes: used when the renderer calculates a texture sample (integrated into shader nodes in Cycles!)
* compositing nodes: used when the render result is recalculated
