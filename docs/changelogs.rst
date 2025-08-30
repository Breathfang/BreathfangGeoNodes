Changelogs
==========

There are some changelogs for |packnamebold|.

.. _1-1-0-preview:

v1.1.0-preview
--------------

.. caution::
    This is the preview version of |packnamebold|. It may have some buggy nodes or crash nodes. Use with caution.

This is the preview version of |packnamebold|. It has major changes of nodes, such as new deformers, new generators, new modifiers, new math functions, new shapes, new special tools, new UV tools, and new utilities. The total nodes are 105 nodes.

Changes
~~~~~~~
* The nodes are now contains 105 nodes!
* The Asset Library Categories are now contains 10 categories, including:
    * Curve Modifiers
    * Deformers
    * Generators
    * Math Functions
    * Mesh Modifiers
    * Shapes
    * Special Tools
    * UV Tools
    * Utilities
    * temp

Nodes
~~~~~
* Curves:
    * `BFang_AdvancedCurveResampler <./curve_modifiers/bfang_advanced_curve_resampler>`_
       Advanced curve resampler, useful for resampling curves
    * `BFang_BreakCyclicCurve <./curve_modifiers/bfang_break_cyclic_curve>`_
       Breaking cyclic curve into non-cyclic curves
    * `BFang_CurveBisect <./curve_modifiers/bfang_curve_bisect>`_
       Curve bisect
    * `BFang_CurveCatenaryEffect <./curve_modifiers/bfang_curve_catenary_effect>`_
       Curve catenary effect
    * `BFang_CurveConvert <./curve_modifiers/bfang_curve_convert>`_
       Curve convert such as Auto, Vector, Align, or Free.
    * `BFang_CurveEvenMesh <./curve_modifiers/bfang_curve_even_mesh>`_
       Even mesh as a curve modifier
    * `BFang_CurvePointAngleSelector <./curve_modifiers/bfang_curve_point_angle_selector>`_
       Curve point angle selector
    * `BFang_CurveOffset <./curve_modifiers/bfang_curve_offset>`_
       Offset curve as a curve modifier
    * `BFang_CurveStepDuplicate <./curve_modifiers/bfang_curve_offset_duplicate>`_
       Curve step duplicate
    * `BFang_CurveToPolyArc <./curve_modifiers/bfang_polyarc>`_
       Curve to polyarc
    * `BFang_LoftSplines <./curve_modifiers/bfang_loft_splines>`_
       Loft splines as a curve modifier into mesh geometry
    * `BFang_SetSplineType <./curve_modifiers/bfang_set_spline_type>`_
       Set spline type as a curve modifier, such as Catmull-Rom, Poly, Bézier, NURBS, or Hermite
    * `BFang_SeparateCurve <./curve_modifiers/bfang_separate_curve>`_
       Separate curve into multiple curves as instances
    * `BFang_SplinesAsTube <./curve_modifiers/bfang_splines_as_tube>`_
       Splines as tube
    * `BFang_TrimCurve <./curve_modifiers/bfang_trim_curve>`_
       Trim curve as a curve modifier
    * `BFang_TwistCurve <./curve_modifiers/bfang_twist_curve>`_
       Twist curve as a curve modifier
* Deformers:
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