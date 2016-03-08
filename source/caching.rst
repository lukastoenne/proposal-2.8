*******************
Unified caching API
*******************

"Caching" has several meanings in the context of CG, which makes the ongoing discussion about it's purpose and implementation a bit confusing:

1. Storing intermediate values of a complex calculation to avoid recomputing when these results are used frequently. An example is a compositor gaussian blur node which has to read the same input value for all neighboring output pixels.
2. Storing results to avoid recomputing when the same (sub-)process is repeated again and again over time. An example is the calculation of mesh deformation during animation, when the animator plays back a single shot over and over.
3. Interchange of data in specific formats for the purpose of sharing assets between different applications. This is usually called "import/export", but shares many similarities with caching. Caching can be viewed as a special case of import/export, where the exporting application is the same as the importing application.

Intermediate value caching (1.) is usually handled with internal data structures and this case is not so relevant on the user level. However, caching of intermediate values may overlap with caching for process optimization (2.). For instance the compositor might also cache an image sequence to cut short computation of unchanged nodes, in addition to internal buffers for intermediate results.

An important case of the "interchange" kind (3.) is exporting to a renderer. In the case of Blender this has been less relevant than in other applications in the past because of the tight integration between renderers and the "host" program. Alembic was developed for the express purpose of modeler-to-renderer communication. Beside making the choice of renderer more flexible, such caching of results has benefits for render farms too: rather than "ask" the modeling software for each frame through an API, the export and import processes can be decoupled. The render farm can much more easily access a central cache file of a shot from each worker ("slave") machine without duplicating the full data. Error-checking a cached export prior to time-consuming rendering becomes a lot easier and can save valuable time and money.

So "caching" in this scope is a combination of

1. Export from a data source to a suitable data format
2. Import to a data target from a suitable data format
3. Utility features to manage storage and validity of cached data

Export and import can also be used separately. For instance a mesh cache can be used to export animation, and then avoid linking complex rigs during the lighting and rendering stage.

Time Sequences and Streaming
----------------------------

Classic export/import in Blender only handles invariant data blocks, i.e. data which does not change over time. With the notable exception of keyframe animation curves, importing only works for static data with a single state for every frame of animation. For the most interesting applications of caching a sequence of data states would be exported:

* animated meshes
* simulation data
* render results

Caching such sequences requires a different workflow than the typical import operator, because it cannot be loaded in a single step. Instead each data frame is loaded whenever it is needed by the scene or a tool working with time sequences (e.g. motion paths). The source of the data (a "stream") must be available permanently, on request of the import target.

The "Point Cache" system is a crude implementation of such a data-streaming feature, but it is hamstrung by a number of aspects:

* Format Limitations: Data types in the format are hardcoded to point-like data (particles, vertices). Some additional "extra" data like smoke voxels have been hacked in, but the format is not designed for general purpose caching.
* Topology fixation: Precludes changes in mesh topology or dynamic particle emission.
* Integration Complexity: Wide range of API calls, flags, half-specified features and side effects need to be handled.
* Inefficiency: Compression is very basic. Many data types (esp. voxel data) would allow much better optimization in specialized formats, e.g. Alembic or VDB.

The widely used "Mesh Cache" modifier suffers from similar issues: It only supports mesh deformation and is not very efficient in terms of storage.

Cacheable Data
--------------

Here's a plain list of stuff in Blender that could benefit from caching and/or export/import in pipelines, in increasing order of exoticness and implementation complexity.

* Meshes (both deformation and full topology)
* Particles (with all associated attributes)
* Hair strands (special case of mesh topology really)
* Smoke/Fluid voxel data
* Poses (could be useful for complex rigs!)
* Object transforms + other properties = Scene layout cache (what "Base" stores in "Scene" datablocks)
* Instances (what actually is an "Object"? Difference of Base and DupliObject in scenes?)
* ...

Cache Backends
--------------

Various file formats can be used for storing cached data efficiently. This is important for large data sets because the amount of data essentially gets multiplied by the number of frames to be cached.

* Alembic: Designed primarily as a modeler-to-renderer pipeline tool. Good general-purpose format for meshes, particles, curves. Supports object hierarchies and instancing.
* OpenVDB: Specialized format for sparse voxel data (fluid and smoke simulation). Very good optimization for empty space. Fast and (cpu-)cache-friendly access for simulations and rendering.
* others?

For a particular type of data the cache backend should be a user choice, with a suitable default.

Storing caches inside .blend files might be of interest in some cases. Cached data might be stored in a plain internal format inside '.blend' files. However, it would be more efficient to "pack" regular cache files (Alembic, OpenVDB) with the .blend file, like we already do with images. That way the compression of the original file types can be utilized and no extra read/write functionality needs to be coded.

Level of Integration
--------------------

Cache export/import can be applied on a number of different levels, depending on the kind of data that is to be cached or the contents of an external cache file.

1. Cache only object components: This is what Blender currently does for individual simulations or a mesh cache. Only the data of a specific component is replaced. No components are added or removed based on the cache file content. Can also be done for a whole object or scene, important thing is that only existing components are touched.
2. Cache a complete Object: Allow the caching system to create/remove/replace components of the cached object, in addition to replacing their internal data. Can also be done for a whole scene, but only existing objects are modified when importing.
3. Cache an entire scene: Allow creation of new objects as well as manipulating existing ones.

Workflow Case Studies
---------------------

Mesh Component Export/Import
============================

We want to simplify lighting and rendering by using cached animation, instead of linking complex rigs and proxies. In this example only the mesh component is cached, while the rest of the object must be copied (appended) from the original.

1) Setup node-based mesh animation pipeline: model->rig->proxify->animate

   These steps are described in more detail in :ref:`simple_animation_nodes`.

2) "Export Components" node is appended after the armature deform node. Export button bakes the whole animation cache in one go for the relevant [defined how?] frame range.

   .. figure:: /images/caching_workflow_animexport.png
     :width: 60%
     :figclass: align-center

   .. note:: A special option "Only Deform" could be an export option to store only deformation layers (vertex offsets) of the mesh, without topology. Would make it essentially like current MMD/PC2 caches. Can break more easily if modifiers change the topology, such modifiers must be left intact when re-importing the cache. The overhead for storing full mesh data once is probably negligable for typical scenarios, so a "only deform" option may not be necessary in practice.

3) Lighting file: The cached mesh data can be imported into a mesh object now. The "Import Components" node loads all available components from the cache file and presents them as sockets. It is similar to a regular "Components" node but uses the cached data instead of local object components.

   .. figure:: /images/caching_workflow_importmesh1.png
     :width: 60%
     :figclass: align-center

4) Cached data can be applied partially to the base mesh, for example if only deformation is wanted.

   .. figure:: /images/caching_workflow_importmesh2.png
     :width: 60%
     :figclass: align-center

   .. note:: Such transfer of attributes between meshes expects matching topology and can otherwise create a garbled mesh. Because this process is non-desctructive, the consequences are minimal.

Full Object Export/Import
=========================

Rather than loading just a single component, we can also just load the complete object from a cache.

1) Setup node-based mesh animation pipeline: model->rig->proxify->animate

   These steps are described in more detail in :ref:`simple_animation_nodes`.

2) Export node supports multiple inputs. Any component plugged in will be stored in the cache.

   .. figure:: /images/caching_workflow_fullexport_nodes.png
     :width: 60%
     :figclass: align-center

3) Lighting file: "Import Components" node is added. It provides all components stored in the object's cache.

   .. figure:: /images/caching_workflow_fullimport_nodes.png
     :width: 60%
     :figclass: align-center
