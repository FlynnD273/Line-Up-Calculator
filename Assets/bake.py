import platform
import bpy
from time import time
from datetime import timedelta
import os
import subprocess
import signal
import bmesh
from bpy.types import NodeTree, ShaderNode

is_shutdown = False


def shutdown() -> None:
    global is_shutdown
    is_shutdown = True


signal.signal(signal.SIGINT, lambda _, b: shutdown())

tex_size = 512

output_dir = os.path.join(bpy.path.abspath("//"), "Textures")
if not os.path.exists(output_dir):
    os.mkdir(output_dir)

bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.device = "GPU"

objs = [o for o in bpy.context.visible_objects if o.material_slots and o.type == "MESH"]

def get_inner_shader(tree) -> tuple[NodeTree, ShaderNode] | tuple[None, None]:
    groups = get_groups(tree)

    while len(groups) > 0:
        grp = groups.pop(0)
        prince = grp.node_tree.nodes.get("Principled BSDF")
        if prince is not None:
            return (grp.node_tree, prince)
        
        new_grps = get_groups(grp.node_tree)
        for g in new_grps:
            groups.append(g)

    return (None, None)


def get_groups(node_tree):
    groups = []
    for node in node_tree.nodes:
        if node.type == "GROUP":
            groups.append(node)
    return groups


def maprange(val, low, high, new_low, new_high, clamp=True):
    if high == low or new_high == new_low:
        return new_high
    newval = (val - low) / (high - low) * (new_high - new_low) + new_low
    if clamp:
        newval = min(max(newval, new_low), new_high)
    return newval


def get_surface_area(obj):
    if obj.type != "MESH":
        print(f"The object {obj.name} is not a mesh.")
        return 0

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    surface_area = sum(f.calc_area() for f in bm.faces)

    bm.free()
    return surface_area

uvmap = "bakedUV"
def process_obj(obj):
    # Select only obj
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.make_single_user(
        object=True, obdata=True, material=True, animation=True, obdata_animation=True
    )

    # Unwrap to new UV map
    if uvmap not in obj.data.uv_layers:
        obj.data.uv_layers.new(name=uvmap)
    old_active = obj.data.uv_layers.active.name
    obj.data.uv_layers.active = obj.data.uv_layers[uvmap]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode="OBJECT")

def obj_to_path(obj):
    img_name = obj.name + "-bake"
    return os.path.join(output_dir, img_name + ".png")


obj_scl = [get_surface_area(o) for o in objs]
max_surf = max(obj_scl)
obj_scl = [s / max_surf for s in obj_scl]
sorted_scl = obj_scl.copy()
sorted_scl.sort()
min_val = sorted_scl[int(len(sorted_scl) * 0.25)]
max_val = sorted_scl[int(len(sorted_scl) * 0.75)]
obj_scl = [maprange(s, min_val, max_val, 0.5, 1) for s in obj_scl]

problems = []
to_process = []

start_time = time()
for i, obj in enumerate(objs):
    if is_shutdown:
        break

    if obj.material_slots is None or len(obj.material_slots) == 0:
        continue

    avg = (time() - start_time) / (i + 1)
    print(
        f"\rBaking {obj.name} | {i + 1}/{len(objs)} Time left: {timedelta(seconds= avg * (len(objs) - i))}{' '*10}"
    )


    if is_shutdown:
        break

    diffuse_path = obj_to_path(obj)
    if os.path.exists(diffuse_path):
        to_process.append(obj)
        continue

    process_obj(obj)
    uvmap = "bakedUV"

    img_name = obj.name + "-bake"
    scl_size = int(max(tex_size * obj_scl[i], 1))
    bpy.context.scene.render.resolution_x = scl_size
    bpy.context.scene.render.resolution_y = scl_size
    bpy.ops.image.new(name=img_name, width=scl_size, height=scl_size)
    bake_image = bpy.data.images[img_name]

    to_delete = []

    # Add the UV map and the image texture nodes to each material
    for slot in obj.material_slots:
        material = slot.material

        tree, prince = get_inner_shader(material.node_tree)
        if tree is None or prince is None:
            problems.append(f"Object: {obj.name} Material: {material.name}")
            continue

        nodes = tree.nodes

        uv_map_node = nodes.new(type="ShaderNodeUVMap")
        uv_map_node.uv_map = uvmap
        uv_map_node.location = (-50, 0)
        uv_map_node.select = False

        texture_node = nodes.new(type="ShaderNodeTexImage")
        texture_node.image = bake_image

        tree.links.new(texture_node.inputs[0], uv_map_node.outputs["UV"])
        nodes.active = texture_node
        texture_node.select = False

        to_delete.append((nodes, uv_map_node))
        to_delete.append((nodes, texture_node))

        output_socket = nodes.get("Group Output").inputs[0]

        for link in tree.links:
            if link.to_socket == prince.inputs["Base Color"]:
                tree.links.new(link.from_socket, output_socket)

    # It's baking time
    bpy.context.scene.cycles.bake_type = "EMIT"
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True
    bpy.ops.object.bake(type="EMIT")
    bake_image.file_format = "PNG"
    bake_image.filepath_raw = diffuse_path
    bake_image.save()

    for slot in obj.material_slots:
        material = slot.material

        tree, prince = get_inner_shader(material.node_tree)
        if tree is None or prince is None:
            problems.append(f"Object: {obj.name} Material: {material.name}")
            continue

        nodes = tree.nodes

        output_socket = nodes.get("Group Output").inputs[0]

        for link in tree.links:
            if link.to_socket == prince.inputs["Alpha"]:
                tree.links.new(link.from_socket, output_socket)

    bpy.ops.object.bake(type="EMIT")
    alpha_path = os.path.join(output_dir, img_name + "_ALPHA.png")
    bake_image.filepath_raw = alpha_path
    bake_image.save()

    if platform.system() == "Windows":
        magick_cmd = ["magick", "convert"]
    else:
        magick_cmd = ["convert"]
    cmd = magick_cmd + [
        alpha_path,
        "-colorspace",
        "gray",
        alpha_path,
    ]
    subprocess.run(cmd)
    cmd = magick_cmd + [
        diffuse_path,
        alpha_path,
        "-alpha",
        "Off",
        "-compose",
        "CopyOpacity",
        "-composite",
        diffuse_path,
    ]
    subprocess.run(cmd)
    os.remove(alpha_path)

    for nodes, node in to_delete:
        nodes.remove(node)

    bpy.data.images[img_name].gl_free()
    bpy.data.images.remove(bake_image)
    bpy.ops.outliner.orphans_purge(
        do_local_ids=True, do_linked_ids=True, do_recursive=True
    )


if not is_shutdown:
    start_time = time()
    for i, obj in enumerate(to_process):
        avg = (time() - start_time) / (i + 1)
        print(
            f"\rProcessing {obj.name} | {i + 1}/{len(objs)} Time left: {timedelta(seconds= avg * (len(objs) - i))}{' '*10}"
        )
        process_obj(obj)
    print("Replacing materials...")
    start_time = time()
    for i, obj in enumerate(objs):
        avg = (time() - start_time) / (i + 1)
        print(
            f"\rReplacing {obj.name} | {i + 1}/{len(objs)} Time left: {timedelta(seconds= avg * (len(objs) - i))}{' '*10}"
        )
        obj.data.materials.clear()
        img_name = obj.name + "-bake"
        print(img_name)
        bake_image = bpy.data.images.load(obj_to_path(obj))
        new_material = bpy.data.materials.new(name=img_name)
        obj.data.materials.append(new_material)
        new_material.use_nodes = True

        tree = new_material.node_tree
        nodes = tree.nodes

        prince = nodes.get("Principled BSDF")
        prince.location = (500, 0)

        # Add the UV map, image texture, and diffuse nodes
        output = tree.get_output_node("CYCLES")
        output.location = (700, 0)

        uv_map_node = nodes.new(type="ShaderNodeUVMap")
        uv_map_node.uv_map = uvmap
        uv_map_node.location = (-50, 0)
        uv_map_node.select = False

        texture_node = nodes.new(type="ShaderNodeTexImage")
        texture_node.image = bake_image
        texture_node.select = False
        texture_node.location = (150, 0)

        # Link everything together
        tree.links.new(texture_node.inputs[0], uv_map_node.outputs["UV"])
        tree.links.new(prince.inputs["Base Color"], texture_node.outputs[0])
        tree.links.new(prince.inputs["Alpha"], texture_node.outputs[1])
        tree.links.new(output.inputs[0], prince.outputs[0])
    print("Done")
    # Save the blend file as a copy
    folder = os.path.dirname(bpy.context.blend_data.filepath)
    name = os.path.splitext(os.path.basename(bpy.context.blend_data.filepath))[0]
    newname = "baked-" + name + ".blend"
    bpy.ops.outliner.orphans_purge(
        do_local_ids=True, do_linked_ids=True, do_recursive=True
    )
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(folder, newname))

    # Export to OBJ
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.visible_objects:
        obj.select_set(True)

    bpy.ops.wm.obj_export(
        filepath=os.path.join(folder, f"OBJ-{name}.obj"), export_selected_objects=True
    )
    if len(problems) > 0:
        print("Could not parse materials:")
        for p in problems:
            print(p)
