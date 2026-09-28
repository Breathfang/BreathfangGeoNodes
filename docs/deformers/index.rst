:orphan:

Deformers
=========

.. image:: /_static/img/nodes/deformers.jpg
   :target: /_static/img/nodes/deformers.jpg
   
Deformer nodes are used to deform meshes in various ways. They can be used to create complex shapes and effects by manipulating the geometry of a mesh.


Deformer Nodes
--------------

Below is a list of available deformer nodes. Each node provides a unique way to manipulate mesh geometry:

.. note::
   Some nodes are exclusively for **Blender 4.5 LTS** and it will be named as **BFangExt** as the part of **Breathfang Geometry Nodes Extension Pack**.

.. warning::
   Nodes marked with * (asterisk) are experimental and **may not work** as expected.

* `BFang_GeoDeform_Bend <./bend>`_
   Bend the mesh around axis.
* `BFang_GeoDeform_Contrast <./contrast>`_
   Amplify or reduce the "contrast" of the mesh.
* `BFang_GeoDeform_FaceOffset <./face_offset>`_
   Offset individual faces.
* `BFang_GeoDeform_MatrixMeshOperations <./matrix_mesh_op>`_
   Deform the mesh with matrix operations.
* `BFang_GeoDeform_MeshOffset <./mesh_offset>`_
   Offset the entire mesh.
* `BFang_GeoDeform_MorphMesh <./morph_mesh>`_
   Morph the mesh between two mesh states using a factor.
* `BFang_GeoDeform_PlanarizeMesh <./planarize_mesh>`_
   Flatten parts of a mesh towards a plane.
* `BFang_GeoDeform_SelectionHook <./selection_hook>`_
   Apply a hook to the selected faces.
* `BFang_GeoDeform_Shear <./shear>`_
   General 3D shear (skew) transform to distort geometry
* `BFang_GeoDeform_Shear_2D <./shear_2d>`_
   2D shear for planar distortion.
* `BFang_GeoDeform_Shear_3D <./shear_3d>`_
   Full 3D shear with more control axes.
* `BFang_GeoDeform_SimpleMatrix <./simple_matrix>`_
   Apply simple matrix transformations.
* `BFang_GeoDeform_Smooth <./smooth>`_
   Smooth the mesh geometry.
* `BFang_GeoDeform_Stretch <./stretch>`_
   Stretch the mesh along an axis.
* `BFang_GeoDeform_StretchHook <./stretch_hook>`_
   Stretch selected faces using a hook.
* `BFang_GeoDeform_Taper <./taper>`_
   Taper the mesh towards an axis.
* `BFang_GeoDeform_ToSphere <./to_sphere>`_
   Transform the mesh towards a spherical shape.
* `BFang_GeoDeform_Twist <./twist>`_
   Twist the mesh around an axis.