Deformers
=========

.. toctree::
    :maxdepth: 2
    :caption: Contents:

.. image:: /_static/img/nodes/deformers.jpg
   :target: /_static/img/nodes/deformers.jpg
   
Deformer nodes are used to deform meshes in various ways. They can be used to create complex shapes and effects by manipulating the geometry of a mesh.


Deformer Nodes
==============

Below is a list of available deformer nodes. Each node provides a unique way to manipulate mesh geometry:

.. note::
   Some nodes are exclusively for **Blender 4.5 LTS** and it will be named as **BFangExt** as the part of **Breathfang Geometry Nodes Extension Pack**.

.. warning::
   Nodes marked with * (asterisk) are experimental and **may not work** as expected.

.. toctree::
   :maxdepth: 2
   :hidden:
   
   bfang_geo_deform_bend
   bfang_geo_deform_contrast
   bfang_geo_deform_face_offset
   bfang_geo_deform_matrix_mesh_operations
   bfang_geo_deform_mesh_offset
   bfang_geo_deform_morph_mesh
   bfang_geo_deform_planarize_mesh
   bfang_geo_deform_selection_hook
   bfang_geo_deform_shear
   bfang_geo_deform_shear_2d
   bfang_geo_deform_shear_3d
   bfang_geo_deform_simple_matrix
   bfang_geo_deform_smooth
   bfang_geo_deform_stretch
   bfang_geo_deform_stretch_hook
   bfang_geo_deform_taper
   bfang_geo_deform_to_sphere
   bfang_geo_deform_twist

* `BFang_GeoDeform_Bend <./bfang_geo_deform_bend>`_
   Bend the mesh around axis.
* `BFang_GeoDeform_Contrast <./bfang_geo_deform_contrast>`_
   Amplify or reduce the "contrast" of the mesh.
* `BFang_GeoDeform_FaceOffset <./bfang_geo_deform_face_offset>`_
   Offset individual faces.
* `BFang_GeoDeform_MatrixMeshOperations <./bfang_geo_deform_matrix_mesh_operations>`_
   Deform the mesh with matrix operations.
* `BFang_GeoDeform_MeshOffset <./bfang_geo_deform_mesh_offset>`_
   Offset the entire mesh.
* `BFang_GeoDeform_MorphMesh <./bfang_geo_deform_morph_mesh>`_
   Morph the mesh between two mesh states using a factor.
* `BFang_GeoDeform_PlanarizeMesh <./bfang_geo_deform_planarize_mesh>`_
   Flatten parts of a mesh towards a plane.
* `BFang_GeoDeform_SelectionHook <./bfang_geo_deform_selection_hook>`_
   Apply a hook to the selected faces.
* `BFang_GeoDeform_Shear <./bfang_geo_deform_shear>`_
   General 3D shear (skew) transform to distort geometry
* `BFang_GeoDeform_Shear_2D <./bfang_geo_deform_shear_2d>`_
   2D shear for planar distortion.
* `BFang_GeoDeform_Shear_3D <./bfang_geo_deform_shear_3d>`_
   Full 3D shear with more control axes.
* `BFang_GeoDeform_SimpleMatrix <./bfang_geo_deform_simple_matrix>`_
   Apply simple matrix transformations.
* `BFang_GeoDeform_Smooth <./bfang_geo_deform_smooth>`_
   Smooth the mesh geometry.
* `BFang_GeoDeform_Stretch <./bfang_geo_deform_stretch>`_
   Stretch the mesh along an axis.
* `BFang_GeoDeform_StretchHook <./bfang_geo_deform_stretch_hook>`_
   Stretch selected faces using a hook.
* `BFang_GeoDeform_Taper <./bfang_geo_deform_taper>`_
   Taper the mesh towards an axis.
* `BFang_GeoDeform_ToSphere <./bfang_geo_deform_to_sphere>`_
   Transform the mesh towards a spherical shape.
* `BFang_GeoDeform_Twist <./bfang_geo_deform_twist>`_
   Twist the mesh around an axis.