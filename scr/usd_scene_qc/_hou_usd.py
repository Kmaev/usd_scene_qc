import dataclasses
import os

import hou
from pxr import Usd, UsdGeom, UsdRender, UsdUtils, UsdShade


@dataclasses.dataclass
class ValidationError:
    message: str


def get_prim_geo_data_timedep(prim: Usd.Prim, timecode) -> tuple[int | None, int | None, int | None]:
    """
     Extracts geometry metadata for a given prim at a specific timecode.
     :return: A tuple with the number of points, number of faces, and number of vertices.
    """
    geom = UsdGeom.Gprim(prim)
    if not geom:
        print(f"{prim.GetPath()} is not a geo primitive")
        return None, None, None
    point_count = face_count = vertex_count = None

    pb = UsdGeom.PointBased(prim)
    pts_attr = pb.GetPointsAttr()
    # Check points based interpolation
    if pts_attr and pts_attr.IsDefined():
        pts = pts_attr.Get(timecode)
        point_count = len(pts) if pts else 0

    # Check mesh interpolation
    mesh = UsdGeom.Mesh(prim)
    if mesh:
        face_counts = mesh.GetFaceVertexCountsAttr().Get(timecode)
        face_count = len(face_counts)
        vertex_count = sum(face_counts)
    return point_count, face_count, vertex_count


def get_interpolation(attr: UsdGeom.Primvar) -> str | None:
    """
    Checks the interpolation type for a given attribute.
    :return: Interpolation type as a string or None
    """
    primvar = UsdGeom.Primvar(attr)
    if primvar.IsDefined():
        return primvar.GetInterpolation()

    # Check special cases, attribs:velocities, acceleration and normals separatly
    prim = attr.GetPrim()
    if prim.IsA(UsdGeom.PointBased):
        pb = UsdGeom.PointBased(prim)
        name = attr.GetName()
        normals_attr = pb.GetNormalsAttr()
        if normals_attr.IsDefined() and name == normals_attr.GetName():
            return pb.GetNormalsInterpolation()
        if name in ("velocities", "accelerations"):
            return "vertex"
    return None


def create_interpolation_map(point_count: int, face_count: int, vertex_count: int) -> dict:
    """
    Creates a mapping of interpolation type to expected value count.
    :return: A mapping of interpolation type to expected value.
    """
    interp_map = {
        "vertex": point_count,  # points
        "faceVarying": vertex_count,  # vertex
        "uniform": face_count,  # prims
        "constant": 1  # detail
    }
    return interp_map


def validate_attributes(stage: Usd.Stage) -> list[ValidationError]:
    """
    Performs a quality check on the attribute's value count against geometry,
    based on its interpolation type. Handles time-dependent attributes.

    :return: list of ValidationError instances
    """
    errors = []
    start_prim = stage.GetPseudoRoot()
    iterator = iter(Usd.PrimRange(start_prim))
    for prim in iterator:
        if not iterator.IsPostVisit() and prim.IsA(UsdGeom.Mesh):
            for attr in prim.GetAttributes():

                interpolation = get_interpolation(attr)
                if interpolation:
                    # times returns [1001.0, 1002.0, 1003.0] frame values if attr is not time-dependent it will return []
                    times = attr.GetTimeSamples() or [0]
                    for t in times:
                        point_count, face_count, vertex_count = get_prim_geo_data_timedep(prim, Usd.TimeCode(t))
                        interp_map = create_interpolation_map(point_count, face_count, vertex_count)
                        value = attr.Get(Usd.TimeCode(t))
                        if value is None:
                            continue

                        attrib_count = len(value)  # check the number of values - this should match the number of points
                        if interpolation == 'constant' and attrib_count != 1:
                            errors.append(
                                ValidationError(
                                    f"ATTR: {prim.GetPath()} Value count mismatch: frame {t} expected value: 1 "
                                    f"'{interpolation}' values, but found {attrib_count} in attribute "
                                    f"'{attr.GetName()}'."))
                        else:
                            if interp_map.get(interpolation):
                                geo_value_num = interp_map.get(interpolation)
                                if attrib_count:
                                    if geo_value_num != attrib_count:
                                        errors.append(
                                            ValidationError(
                                                f"ATTR: {prim.GetPath()} Value count mismatch: frame {t} expected {geo_value_num} "
                                                f"'{interpolation}' values, but found {attrib_count} in attribute "
                                                f"'{attr.GetName()}'."
                                            )
                                        )

    return errors


def get_missing_references(stage: Usd.Stage) -> list[ValidationError]:
    """
    Check missing references on usd layer.
    :return: list of ValidationError instances
    """
    errors = []
    usd_layer = stage.GetRootLayer()

    layers, resolved_paths, unresolved_paths = UsdUtils.ComputeAllDependencies(usd_layer.identifier)
    # resolved_paths contains asset dependencies that exist on disk.
    # unresolved_paths include asset references that are present in the stage but point to missing or moved files.
    for layer in layers:
        layer_path = layer.realPath
        if layer_path and not os.path.exists(layer_path):
            errors.append(ValidationError(f"{layer_path} does not exist"))

    for asset_path in unresolved_paths:
        errors.append(ValidationError(f"REF: {asset_path} does not exist"))
    errors = remove_anonymous_errors(errors)
    return errors


def remove_anonymous_errors(errors: list[ValidationError]) -> list[ValidationError]:
    """
    Removes validation errors related to anonymous (in-memory) USD layers.
    :return: cleaned list of ValidationErrors
    """
    return [err for err in errors if "anon:" not in err.message]


def validate_render_primitives(stage: Usd.Stage) -> list[ValidationError]:
    """
    Runs a quality check to ensure that render settings and a camera are present in the scene.
    The camera is validated based on the render settings.

    :return: A list of ValidationError instances.
    """
    render_settings = []
    render_products = []

    errors = []
    for prim in stage.Traverse():
        settings = UsdRender.Settings(prim)
        if settings:
            render_settings.append(prim.GetPath())
            camera = settings.GetCameraRel().GetTargets()
            if camera:

                cam_path = camera[0]  # This is an Sdf.Path
                cam_prim = stage.GetPrimAtPath(cam_path)
                camera = cam_prim

                if not camera:
                    errors.append(ValidationError("CAM: No camera primitive found"))
            else:
                errors.append(ValidationError(f"CAM: No camera selected in render settings node {settings.GetPath()}"))

        if UsdRender.Product(prim):
            render_products.append(prim.GetPath())

    if not render_settings:
        errors.append(ValidationError("REN: No render settings found"))
    if not render_products:
        errors.append(ValidationError("REN: No render products found"))
    return errors


def validate_material_binding(stage: Usd.Stage) -> list[ValidationError]:
    """
    Traverses the USD stage and validates material bindings.
    Includes checking whether the bound material exists and is active.
    :return: list of ValidationError instances
    """
    errors = []
    start_prim = stage.GetPseudoRoot()
    iterator = iter(Usd.PrimRange(start_prim))

    for prim in iterator:
        if not iterator.IsPostVisit() and prim.IsA(UsdGeom.Imageable):

            bound_material, _ = check_prim_material_binding(prim)
            if prim.IsA(UsdGeom.Mesh):
                if not bound_material or not bound_material.GetPrim().IsActive():
                    errors.append(ValidationError(f"MAT: No material binding on {prim.GetPath()}"))

    return errors


def check_prim_material_binding(prim: Usd.Prim) -> tuple[Usd.Prim, UsdShade.Tokens]:
    """
    Checks if a primitive has material binding
    :return: A tuple material binding and token
    """
    mat_bind_api = UsdShade.MaterialBindingAPI(prim)
    bound_material, strength = mat_bind_api.ComputeBoundMaterial()
    return bound_material, strength


def get_hou_selected_node() -> hou.Node:
    """
    Returns the currently selected Houdini node to run QC checks from.

    :return: The selected node if one is selected or, displays an error message.
    """
    if hou.selectedNodes():
        return hou.selectedNodes()[0]

    hou.ui.displayMessage(text="Select a node to run QC", buttons=('OK',), title="Error",
                          severity=hou.severityType.Error)
    raise RuntimeError("No Houdini node selected.")
