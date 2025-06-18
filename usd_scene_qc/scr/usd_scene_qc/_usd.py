import os

from pxr import Usd, UsdGeom, Sdf


def get_prim_geo_data_timedep(prim: Usd.Prim, timecode):
    """
     Extracts geometry metadata for a given prim at a specific timecode.
    """
    geom = UsdGeom.Gprim(prim)
    if not geom:
        print(f"{prim.GetPath()} is not a geo primitive")
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


def get_interpolation(attr):
    """
    Checks the interpolation type for a given attribute.
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


def create_interpolation_map(point_count, face_count, vertex_count):
    """
    Creates a mapping of interpolation type to expected value count.
    """
    interp_map = {
        "vertex": point_count,  # points
        "faceVarying": vertex_count,  # vertex
        "uniform": face_count,  # prims
        "constant": 1  # detail
    }
    return interp_map


def qc_attributs(prim: Usd.Prim, attr):
    """
    Performs a quality check on the attribute's value count against geometry,
    based on its interpolation type. Handles time-dependent attributes.

    :return: Dictionary of attribute name → [number of geometry elements, number of attribute values]
    """
    interpolation = get_interpolation(attr)
    if interpolation:
        # times returns [1001.0, 1002.0, 1003.0] frame values if attr is not time-dependent it will return []
        times = attr.GetTimeSamples() or [0]
        # print(f"{attr.GetName()}: {times}")
        qc_primvars_map = {}
        qc_primvars_map[attr.GetName()] = {}

        for t in times:

            point_count, face_count, vertex_count = get_prim_geo_data_timedep(prim, Usd.TimeCode(t))
            interp_map = create_interpolation_map(point_count, face_count, vertex_count)
            value = attr.Get(Usd.TimeCode(t))
            if value is None:
                # print(f"{attr.GetName()} - values is None")
                return
            else:
                attrib_count = len(value)  # check the number of values - this should match the number of points
                if interpolation == 'constant' and attrib_count != 1:
                    qc_primvars_map[attr.GetName()][t] = attrib_count
                else:
                    if interp_map.get(interpolation):
                        geo_value_num = interp_map.get(interpolation)
                        # print(f"{attr.GetName()} - with value {geo_value_num}, value {attrib_count} - time-dependent")

                        if attrib_count:
                            if geo_value_num != attrib_count:
                                qc_primvars_map[attr.GetName()][t] = [attrib_count, geo_value_num]
                                # print(f"{attr.GetName()} - with value {attrib_count}, doesn't match number of values on geometry {geo_value_num}")
        return qc_primvars_map
    else:
        return None


def get_missing_references(usd_layer):
    """
    Check missing refrences on usd layer.
    """
    external_refs = usd_layer.GetExternalReferences()
    missing_refs = []
    for path in external_refs:
        # print("Ext reference:", path)
        abs_path = layer.ComputeAbsolutePath(path)
        if not os.path.exists(abs_path):
            # print(f"============================ \nMissing file: {abs_path}")
            missing_refs.append(abs_path)
    return missing_refs


if __name__ == "__main__":
    # ----- Script entry point -----
    script_dir = os.path.dirname(__file__)
    resources_path = os.path.join(script_dir, "..", "..", "resources")
    resources_path = os.path.normpath(resources_path)
    stage_path = os.path.join(resources_path, "primvars_check_v007.usda")
    stage = Usd.Stage.Open(stage_path)

    # Check broken attributes
    start_prim = stage.GetPseudoRoot()
    iterator = iter(Usd.PrimRange(start_prim))
    for prim in iterator:
        if not iterator.IsPostVisit() and prim.IsA(UsdGeom.Mesh):
            for attr in prim.GetAttributes():
                print(qc_attributs(prim, attr))
                pass

    # Check missing references
    layer = Sdf.Layer.FindOrOpen(stage_path)
    print(get_missing_references(layer))
