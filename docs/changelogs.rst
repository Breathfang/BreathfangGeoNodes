Changelogs
==========

There are some changelogs for |packnamebold|.

.. _v1-1-0-preview:

v1.1.0-preview
--------------

.. caution::
    This is the preview version of |packnamebold|. It may have some buggy nodes or crash nodes. Use with caution.

This is the preview version of |packnamebold|. It has major changes of nodes, such as new deformers, new generators, new modifiers, new math functions, new shapes, new special tools, new UV tools, and new utilities. The total nodes are 105 nodes.

Changes
~~~~~~~
* The nodes are now contains 105 nodes!
* The Asset Library Categories are now contains 9 categories, including:
    * Curve Modifiers
    * Deformers
    * Generators
    * Math Functions
    * Mesh Modifiers
    * Shapes
    * Special Tools
    * UV Tools
    * Utilities

Nodes
~~~~~
* Curve Modifiers:
    * `BFang_AdvancedCurveResampler <./curve_modifiers/bfang_advanced_curve_resampler>`_
    * `BFang_BreakCyclicCurve <./curve_modifiers/bfang_break_cyclic_curve>`_
    * `BFang_CurveCatenaryEffect <./curve_modifiers/bfang_curve_catenary_effect>`_
    * `BFang_LoftSplines <./curve_modifiers/bfang_loft_splines>`_
* Deformers:
    * `BFang_GeoDeform_Bend <./bfang_geo_deform_bend>`_
    * `BFang_GeoDeform_Contrast <./bfang_geo_deform_contrast>`_
    * `BFang_GeoDeform_FaceOffset <./bfang_geo_deform_face_offset>`_
    * `BFang_GeoDeform_MatrixMeshOperations <./bfang_geo_deform_matrix_mesh_operations>`_
    * `BFang_GeoDeform_MeshOffset <./bfang_geo_deform_mesh_offset>`_
    * `BFang_GeoDeform_MorphMesh <./bfang_geo_deform_morph_mesh>`_
    * `BFang_GeoDeform_PlanarizeMesh <./bfang_geo_deform_planarize_mesh>`_
    * `BFang_GeoDeform_SelectionHook <./bfang_geo_deform_selection_hook>`_
    * `BFang_GeoDeform_Shear <./bfang_geo_deform_shear>`_
    * `BFang_GeoDeform_Shear_2D <./bfang_geo_deform_shear_2d>`_
    * `BFang_GeoDeform_Shear_3D <./bfang_geo_deform_shear_3d>`_
    * `BFang_GeoDeform_SimpleMatrix <./bfang_geo_deform_simple_matrix>`_
    * `BFang_GeoDeform_Smooth <./bfang_geo_deform_smooth>`_
    * `BFang_GeoDeform_Stretch <./bfang_geo_deform_stretch>`_
    * `BFang_GeoDeform_StretchHook <./bfang_geo_deform_stretch_hook>`_
    * `BFang_GeoDeform_Taper <./bfang_geo_deform_taper>`_
    * `BFang_GeoDeform_ToSphere <./bfang_geo_deform_to_sphere>`_
    * `BFang_GeoDeform_Twist <./bfang_geo_deform_twist>`_
* Generators:
    * `BFang_3DFillCurves <./generators/bfang_3d_fill_curves>`_
    * `BFang_3DGridInstances <./generators/bfang_3d_grid_instances>`_
    * `BFang_AdvancedArray <./generators/bfang_advanced_array>`_
    * `BFang_AnimFollowCurve <./generators/bfang_anim_follow_curve>`_
    * `BFang_CircularArray <./generators/bfang_circular_array>`_
    * `BFang_ConnectPoints <./generators/bfang_connect_points>`_
    * `BFang_DrakeRemesher <./generators/bfang_drake_remesher>`_
    * `BFang_DynamicRotateObjectByCurve <./generators/bfang_dynamic_rotate_object_by_curve>`_
    * `BFang_DynamicScaleObjectByCurve <./generators/bfang_dynamic_scale_object_by_curve>`_
    * `BFang_GeoLerp <./generators/bfang_geo_lerp>`_
    * `BFang_InstancesInVolume <./generators/bfang_instances_in_volume>`_
    * `BFang_InstancesOnEdge <./generators/bfang_instances_on_edge>`_
    * `BFang_InstancesOnSurface <./generators/bfang_instances_on_surface>`_
    * `BFang_InstancesInVolume <./generators/bfang_instances_in_volume>`_
    * `BFang_SpinFromSplines <./generators/bfang_spin_from_splines>`_
* Math Functions:
    * `BFang_FangMath_Constants <./math_functions/bfang_fang_math_constants>`_
    * `BFang_FangMath_EulerToQuaternion <./math_functions/bfang_fang_math_euler_to_quaternion>`_
    * `BFang_FangMath_Factorial <./math_functions/bfang_fang_math_factorial>`_
    * `BFang_FangMath_Fibonacci <./math_functions/bfang_fang_math_fibonacci>`_
    * `BFang_FangMath_FlipValue <./math_functions/bfang_fang_math_flip_value>`_
    * `BFang_FangMath_FlipValueVector <./math_functions/bfang_fang_math_flip_value_vector>`_
    * `BFang_FangMath_FloorQuantization <./math_functions/bfang_fang_math_floor_quantization>`_
    * `BFang_FangMath_InRangeBoolean <./math_functions/bfang_fang_math_in_range_boolean>`_
    * `BFang_FangMath_IsUnitQuaternion <./math_functions/bfang_fang_math_is_unit_quaternion>`_
    * `BFang_FangMath_MatrixAllZero <./math_functions/bfang_fang_math_matrix_all_zero>`_
    * `BFang_FangMath_MatrixMath <./math_functions/bfang_fang_math_matrix_math>`_
    * `BFang_FangMath_MatrixNoIdentity <./math_functions/bfang_fang_math_matrix_no_identity>`_
    * `BFang_FangMath_NormalizeVectorAngle <./math_functions/bfang_fang_math_normalize_vector_angle>`_
    * `BFang_FangMath_PythagoreanTheorem <./math_functions/bfang_fang_math_pythagorean_theorem>`_
    * `BFang_FangMath_PythagoreanTheorem3D <./math_functions/bfang_fang_math_pythagorean_theorem_3d>`_
    * `BFang_FangMath_QuaternionToEuler <./math_functions/bfang_fang_math_quaternion_to_euler>`_
    * `BFang_FangMath_Tribonacci <./math_functions/bfang_fang_math_tribonacci>`_
    * `BFang_FangMath_VectorAngleConventer <./math_functions/bfang_fang_math_vector_angle_conventer>`_
    * `BFang_FangMath_VectorClamp <./math_functions/bfang_fang_math_vector_clamp>`_
* Mesh Modifiers:
    * `BFang_DecimateMesh <./modifiers/bfang_decimate_mesh>`_
    * `BFang_DeleteByMeshElements <./modifiers/bfang_delete_by_mesh_elements>`_
    * `BFang_EdgeBisect <./modifiers/bfang_edge_bisect>`_
    * `BFang_EdgeOffset <./modifiers/bfang_edge_offset>`_
    * `BFang_FitSizeFromMeasure <./modifiers/bfang_fit_size_from_measure>`_
    * `BFang_FollowTransform <./modifiers/bfang_follow_transform>`_
    * `BFang_GeoDisplacement <./modifiers/bfang_geo_displacement>`_
    * `BFang_GeoInset <./modifiers/bfang_geo_inset>`_
    * `BFang_GeoMatch_BBoxScale <./modifiers/bfang_geo_match_bbox_scale>`_
    * `BFang_GeometryToOrigin <./modifiers/bfang_geometry_to_origin>`_
    * `BFang_GeoMirror <./modifiers/bfang_geo_mirror_2d>`_
    * `BFang_MeshNormalFix <./modifiers/bfang_mesh_normal_fix>`_
    * `BFang_MeshQuantizer <./modifiers/bfang_mesh_quantizer>`_
    * `BFang_MeshIsland_RandomDisappeareance <./modifiers/bfang_mesh_island_random_disappearance>`_
    * `BFang_MeshIsland_VisibleIndex <./modifiers/bfang_mesh_island_visible_index>`_
    * `BFang_MeshIsland_DeleteIsland <./modifiers/bfang_mesh_island_delete_island>`_
    * `BFang_ObjectToObjectSnapType <./modifiers/bfang_object_to_object_snap_type>`_
* Mesh Shapes:
    * `BFang_GeoShape_Capsule <./shapes/bfang_geo_shape_capsule>`_
    * `BFang_GeoShape_Hexagrid <./shapes/bfang_geo_shape_hexagrid>`_
    * `BFang_GeoShape_Torus <./shapes/bfang_geo_shape_torus>`_
* Special Tools
    * `BFang_Dragonfolk_DonutGenerator <./special_tools/bfang_wyvern_claw_donut_generator>`_
    * `BFang_RaptorMesh_MeshMeasure <./special_tools/bfang_raptor_mesh_mesh_measure>`_
    * `BFang_RaptorMesh_MeshVisualization <./special_tools/bfang_raptor_mesh_mesh_visualization>`_
    * `BFang_WyvernClaw_MeshExporter <./special_tools/bfangext_wyvern_claw_mesh_exporter>`_ - Renamed from BFang_SculptDragonMesh_Exporter
* UV Tools
    * `BFang_BoxUVProject <./uv_tools/bfang_box_uv_project>`_
    * `BFang_GetUVSeams <./uv_tools/bfang_get_uv_seams>`_
    * `BFang_MeshProjectUV <./uv_tools/bfang_mesh_project_uv>`_
    * `BFang_MeshUnwrap <./uv_tools/bfang_mesh_unwrap>`_
    * `BFang_UVUnwrap <./uv_tools/bfang_uv_unwrap>`_
* Utilities
    * `BFang_AdvancedNoiseTools <./utilities/bfang_advanced_noise_tools>`_ - Renamed from BFang_DynamicNoise
    * `BFang_BoundaryEdgeSelection <./utilities/bfang_boundary_edge_selection>`_
    * `BFang_DirectionalBlurAttribute <./utilities/bfang_directional_blur_attribute>`_
    * `BFang_FaceIndex <./utilities/bfang_face_index>`_
    * `BFang_FaceCornerIndex <./utilities/bfang_face_corner_index>`_
    * `BFang_GetMeshType <./utilities/bfang_get_mesh_type>`_
    * `BFang_MeshIntersectChecker <./utilities/bfang_mesh_intersect_checker>`_
    * `BFang_MeshToSelection <./utilities/bfang_mesh_to_selection>`_
    * `BFang_MeshVolumeGetVolume <./utilities/bfang_mesh_volume_get_volume>`_
    * `BFang_ObjectsInfo <./utilities/bfang_objects_info>`_
    * `BFang_PlaneBisectMeshChecker <./utilities/bfang_plane_bisect_mesh_checker>`_
    * `BFang_PositionRangeSelection <./utilities/bfang_position_range_selection>`_
    * `BFang_RotationalAlignment <./utilities/bfang_rotational_alignment>`_
    * `BFang_SelectFacesByAngle <./utilities/bfang_select_faces_by_angle>`_
    * `BFang_ShadowAsSelection <./utilities/bfang_shadow_as_selection>`_
    * `BFang_SimpleRandomSelectionIsland <./utilities/bfang_simple_random_selection_island>`_
    * `BFang_SortElements <./utilities/bfang_sort_elements>`_
    * `BFang_StoreSharpEdge <./utilities/bfang_store_sharp_edge>`_

.. _v1-0-1-preview:

v1.0.1-preview
--------------

.. note::
   This GeoNode pack might be unstable and cause weird behavior. Please always backup before use it.

.. image:: _static/img/changelog/v1_0_1.png
   :width: 100%
   :align: center

A dragon has been spawned! Now this is the first preview version before going to v1.1.0-alpha

Preview/Developer Version Changelogs:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It has some features including:

* New Tools and Modifiers:
   * **BFang_GeoCurveConvert**: This GeoNode purpose is to convert any type of curves into targeted curve type.
   * **BFang_GeoMeshAlongCurves**: Multiple meshes along curves, can scatter, and more
   * **BFang_GeoSolidify**: Even thickness included
   * **BFang_GeoShape_Spiral**: Spiral Generator based on Geometry Nodes.
   * **BFang_GeoShape_QuadSphere**: For making quad sphere based on Geometry Nodes
   * **GeoText To Mesh**: Renamed to BFang_GeoTextToMesh
   * **GeoSubdivision Surface**: Renamed to BFang_GeoSubSurface
   * **SculptDragonMesh Exporter**: Renamed to BFang_SculptDragonMesh_Exporter (NOT Dragon VBM/IMM generator)
* New Utils:
   * **BFang_DynamicNoise**: Advanced Noise tools with Geometry Nodes
   * **BFang_GeoSolidify**: Geometry Node based solidify
   * **BFang_MeshToBool**: Convert from mesh to boolean value
   * **BFang_GeoMeshAlongCurves**: Instances along curves
   * **BFang_SmoothCurve**: Smooth Curves with Geometry Nodes
   * **BFang_VectorAngleConventer**: Vector node Angle Conventer from Degrees into Radian and vice-versa

.. _v0-1-0-alpha:

v0.1.0-alpha
------------

Initial alpha version release, introduce to our dragons! A warrior, or a mesh? Oh yeah, this is our first public release of GeoNodes. But... this is still alpha version. Features:

* **SculptDragonMesh Exporter**
  This is for low poly exportion and sculpy-ready mesh
* **GeoSpiral**
  For spiral generator based on Geometry Nodes
* **GeoSubdivision Surface**
  Subdivision surface based on Geometry Nodes, has additional features including Catmull-Clark factor, and more
* **GeoText to Mesh**
  Dynamic Text to mesh
* **BlendCrashIt!**
  And yeah, this node will crash Blender. But don't worry, it has disclaimer first and needs to tick the checkbox to crash blender. Always backup before use this node.