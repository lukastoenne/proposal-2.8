********************************
Overview and ToDo list of topics
********************************

::

  1) Solving the "Ownership" Issue
  Modifying linked objects is not possible, neither is inheriting from a linked object. Simulations have to be setup in the rigging stage, not a feasible pipeline. Existing solutions (proxies, python overrides, alembic caches) are not sufficient and limited to specific areas.
  >> Local, group-based "extensions" of objects are needed to augment an object with additional components: decouple grooming and sims from rigging, allow object variants (e.g. multiple actions in same scene).

  Typical situations:
  - material/lighting py overrides in local scene [Pablo?]
  - typical rigger+animator workflow with proxies [any BI shot really]
  - simple non-dynamic hair setup: conflict avoided only by passing mesh object ownership from rigger to groomer *before animation* [Coro grooming in Caminandes 1 & 2]
  - dynamic hair sim: serious trouble because of linked objects after animation [Victor or Franck hair shot]
  - animation variants impossible due to proxy limitations [multiple sheep in tornado shot]

  Tentative sketch of a solution:
  Object "inheritance" could solve staging problems with ownership, by making a new local object to be used instead of a linked object, while inheriting it's setup. Instead of writing back to the linked object (as in "override"/proxy), the local object is a regular new object, which can then be linked again in later stages.
  Inter-Object relationships need extra attention in the new model (eg. parent/child relations, target objects in modifiers). To ensure consistent relations after making a local extension object, the extension could happen on a group level: one or more objects in the group are replaced by locally extended objects, the relations inside the group are mapped.

  Mockups to describe the new workflow:
  - basic model->rigging->animation->render workflow [some BI shot without hair/cloth/etc?]
  - hair simulation on a character [Victor hair grooming + dynamics]
  - multiple instances of a base object with animation variants [GB sheep flock, Caminandes penguins]
  - complex object groups with helper relations [GB caterpillar?]

  2) Separate process settings from output data
  Modifier and Simulation data is stored in the same place as settings (Object stores ModifierData as well as DerivedMesh/voxels/etc.) => reusing settings becomes impossible, caches are hard to manage, render vs. preview fight for "current" data (very common with particles). Same goes for temporary internal data (e.g. mesh deform weights)
  >> Generalized way of storing results from generative processes in a "scene database" is needed. Could then be used for caching, render export, viewport/previews. Database must be disconnected from DNA settings structs, used as runtime storage.

  In concrete terms: object data is stored in passive "components", rather than being scattered throughout Object struct or part of modifiers:
  - mesh geometry (DerivedMesh)
  - particle systems
  - strands (hair-like geometry, see below)
  - volume grids
  - ...

  Processes such as modifiers and simulations become pure state-less functional descriptions. In principle that could still work with the current stack-based designs, but probably switching to a node design from the start saves redundant work.

  3) Object Nodes
  Stack-based process description is inflexible. Result is feature creep: expressing a different behavior is only possible by adding more buttons. More features in turn creates incompatible combinations, no "syntax check" exists to detect these.
  >> Nodes are better:
    - sockets and explicit connections allow combining and re-using components
    - node groups allow user-defined interfaces (this can be extended to the top level as well!)
    - artists start with a clean slate (or minimal defaults), much less confusing than crammed panels
    - code-wise nodes enforce small-scale local functions, avoiding excessive compatibility issues and paranoid checks

  Design mockups:
  - Object node tree integration with a single button
  - Accessing object component data from an input node
  - Node "groups" for various data types and processes
    * mesh geometry (classic modifiers)
    * particle setup: generate particles like modifiers (not a sim)
    * simulations of various types
    Each of these sub-nodes defines a function that can be called at the appropriate time by the depsgraph, like object update or time steps.

  Generic Node Compiler:
    Nodes are an implicit programming language: every output is a variable, combined into expressions via input links. A node compiler that lowers implicit node language into imperative code, combined with a runtime JIT engine (LLVM, CUDA, OpenCL) would yield optimized functions with adaptable threading, vectorizing, tiling, etc..
    Because nodes are (among other things) a programming language, it also becomes feasible to have proper syntax checks and error messages, as well as some high-level debugging and profiling on the user level.

  4) Particles

  Use cases for "particles" in the broadest sense [with examples]:
  - Sparks, dust, etc: cheap rendering effects using billboards/halos [Sintel desert walk]
  - Instancing (duplis) [GB grass fields]
  - Rigid Body simulation: use object instances (collision shapes) as RBs
  - Fracturing: similar to RB sim, but use mesh parts ("shards") as collision shapes
  - Smoke sim emission basis [GB tornado]
  - Squishy (plasto-elastic) materials: snow, sand, mud, foam, ... [Caminandes 3 snow sim]
  - Point Density basis [any examples in open movies or so?]
  - SPH particles (not really usable without sophisticated particle meshing and a stable efficient solver) [never used for real, too buggy/slow/unconvincing]
  - Marker-and-Cell (MAC) particles (not implemented in Blender yet) [virtually every recent movie production with water or smoke]
  - "Point Clouds", deep compositing, ... [current particles not usable for this purpose, due to massive memory overhead]

  Basic particle systems will carry only minimal amounts of data. Additional attributes are added as required by user tools, modifiers, or simulations. Nodes will be the main interface for controlling particles.

  A particle component ("system") of an object can be accessed as the output of a "Components" input node in object node systems.

  Workflow examples:
  - particles for creating instanced foliage (tree, grass) [add particles, distribute on a mesh with texture map, add "duplis" node, hook up to object(s), render]
  - p. with a simple point mass sim [add particles, define rest positions, add point solver node, bake]
  - p. as rigid bodies controlling fracture physics [add particles, map to fractured shard mesh, add RB solver node, bake]
  - p. as fluid/smoke/MPM marker particles [add particles, link to fluid sim via a node (fluid sim can handle multiple particle systems as markers), bake fluid sim which then defines particle motion, add a p. surface node on a mesh object, render]
  - deep compo point cloud [?? to be investigated]

  Implementation Notes:

  Particles themselves are not a renderable physical entity in any sense, but can take on a large variety of roles. In some cases a render feature directly uses particle input (billboards, instancing, point density), while in other cases they are used only indirectly as input for another kind of process whose result then gets rendered (smoke, mesh surfaces). In some cases a lot of data may be associated with each particle (dupli transforms, motion state, SPH springs, etc.), while in other cases the emphasis is on scale and huge number of particles which requires as little memory footprint per particle as possible (MAC particles, point clouds).

  Particle geometry is stored as a simple set of uninterleaved arrays, like CustomData. Certain attributes will always be present, while others can be lazy-initialized when needed. The topology is that of a simple point cloud or vertex-only mesh, although in some cases edge-like data may be generated (e.g. SPH springs).

  5) Strands/Hair System

  Just as with particles, "Strand"-like geometry can be used for a number of different purposes:
  - long hair, with strands defining the motion of invididual physical hairs or small bundles of hairs
  - short hair, without dynamics simulation
  - hair-like structures on animal skin or plants
  - grass and similar foliage
  - ...

  The name "strands" is used to avoid suggesting a limitation on actual hair. Strands are topologically chains of vertices (each vertex has 1 or 2 edges). Modifiers and simulations can be applied as with particle geometry, by the "Components" object node.

  6) Unified caching API
  Point cache format is unsuitable for meshes (fixed number of points, no custom data), Mesh Cache is limited to deform also and not very efficient. Alembic as a backend has conflicting goals: software interchange vs. Blender caching. Alembic also isn't very efficient for voxel data (use OpenVDB instead).
  >> Define cache API for the scene database (see point 2). Common features:
      - runtime cache vs. persistent disk caching or .blend packing
      - shared output paths for scenes, groups, asset types, users(?)
     Appropriate backends can be chosen for type of data (alembic for meshes/particles/curves/..., openvdb for voxel data, image sequences or MultiEXR).

  Workflow Examples:
  - modifier cache for final mesh animation [select cache library, enable Alembic backend, bake, play back]
  - hair sim cache [create a default strand geometry component, add a hair solver node, append a cache output node, select Alembic backend for motion state]
  - smoke cache [create a default volume component, add a smoke solver node, append a cache output node, select OpenVDB backend for smoke grids]
  - render cache: render output directory as part of the cache library [select cache, render multiple layers, use compositor on cached render results]

  Implementation remarks:

  Note that a "scene database" is itself a cache! Only the last result is stored and previous data is discarded, but the principle is the same as when storing a whole sequence of states.

  The cache API would connect 2 sides:
    1) data "producers" are objects that generate data on top of the basic user editing:
        - objects/pose bones -> obmat (can be useful to cache for costly constraints!)
        - modifiers -> DerivedMesh
        - curves -> displist
        - rendering -> render results
        - compo -> image
        - duplicators -> duplilist (currently not stored at all, except through some specialized Cycles hack)
        - particles/rigidbody/cloth/hair/softbody -> motion states
        - smoke/fluid sim -> voxel grids
    2) data "targets" are subsystems that can store such generated data:
        - "current scene frame" database: avoid recalc on trivial changes for viewport drawing
        - renderer: renderers have their own database, but could use the same API for retrieving the scene data
        - caches: store every frame in a continuous range to avoid the incremental cost of stepping through from a start frame
        - exporters: exporters (alembic) usually want to store raw output rather than a complex scene description

  For some of the targets the data can flow both ways: true caches and some importers can be used to retrieve generated data states to avoid recomputation.

  7) Most physical solvers need a serious upgrade
  - Particles are limited to plain "point mass" simulation >> Implement rigidbody particles, marker-and-cell (MAC) particles for fluid/smoke sim
  - Smoke sim code is old and superseeded by newer methods >> Integrate mantaflow, or rewrite the solver based on OpenVDB
  - Fluid sim code is even more outdated >> Could be handled by same code system as smoke, the methods are very similar. Good particle meshing is essential for realistic fluid sim
  - Cloth and hair sim need a better implementation of collisions, and more modern softbody solvers could help with performance and stability >> Bullet provides much better contact point detection. Papers are available on cloth solver improvements of recent years.
  - No Blender system exists yet for "squishy" plasto-elastic matter (mud, foam, snow, ...) >> Lots of papers available on this, summarily called "Material Point Methods" (MPM)
