import bpy
from time import time
from datetime import timedelta
import os

tex_size = 512
bpy.context.scene.render.resolution_x = tex_size
bpy.context.scene.render.resolution_y = tex_size

output_dir = os.path.join(bpy.path.abspath("//"), "Textures")
if not os.path.exists(output_dir):
    os.mkdir(output_dir)

bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.device = "GPU"

start_time = time()
objs = [ o for o in bpy.context.visible_objects if o.material_slots and o.type == "MESH" ]
for i, obj in enumerate(objs):
    avg = (time() - start_time) / (i + 1)
    print(f"\r{i + 1}/{len(objs)} Time left: {timedelta(seconds= avg * (len(objs) - i))}{' '*10}")

    # Select only obj
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Unwrap to new UV map
    uvmap = "bakedUV"
    if uvmap not in obj.data.uv_layers:
        obj.data.uv_layers.new(name=uvmap)
    old_active = obj.data.uv_layers.active.name
    obj.data.uv_layers.active = obj.data.uv_layers[uvmap]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode="OBJECT")

    if obj.material_slots is not None and len(obj.material_slots) > 0:
        # One image per object. This eliminates name collisions and hopefully keeps the file size down
        img_name = obj.name + "-bake"
        bpy.ops.image.new(name=img_name, width=tex_size, height=tex_size)
        bake_image = bpy.data.images[img_name]

        # Add the UV map and the image texture nodes to each material
        for slot in obj.material_slots:
            material = slot.material

            tree = material.node_tree
            nodes = tree.nodes

            uv_map_node = nodes.new(type="ShaderNodeUVMap")
            uv_map_node.uv_map = uvmap
            uv_map_node.location = (-50, 0)
            uv_map_node.select = False

            texture_node = nodes.new(type="ShaderNodeTexImage")
            texture_node.image = bake_image
            output = tree.get_output_node("CYCLES")

            tree.links.new(texture_node.inputs[0], uv_map_node.outputs["UV"])
            nodes.active = texture_node
            texture_node.select = False

        # It's baking time
        bpy.context.scene.cycles.bake_type = "DIFFUSE"
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True
        bpy.ops.object.bake(type="DIFFUSE")
        bake_image.filepath_raw = os.path.join(output_dir, img_name + ".png")
        bake_image.file_format = "PNG"
        bake_image.save()

        # Remove all the materials and add a single blank one
        obj.data.materials.clear()
        new_material = bpy.data.materials.new(name=img_name)
        obj.data.materials.append(new_material)
        new_material.use_nodes = True

        tree = new_material.node_tree
        nodes = tree.nodes

        nodes.remove(nodes.get("Principled BSDF"))

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

        diffuse = tree.nodes.new(type="ShaderNodeBsdfDiffuse")
        diffuse.select = False
        diffuse.location = (500, 0)

        # Link everything together
        tree.links.new(texture_node.inputs[0], uv_map_node.outputs["UV"])
        tree.links.new(diffuse.inputs[0], texture_node.outputs[0])
        tree.links.new(output.inputs[0], diffuse.outputs[0])

# Save the blend file as a copy
folder = os.path.dirname(bpy.context.blend_data.filepath)
name = os.path.splitext(os.path.basename(bpy.context.blend_data.filepath))[0]
newname = "baked-" + name + ".blend"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(folder, newname))

# Export to OBJ
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.context.visible_objects:
    obj.select_set(True)

bpy.ops.wm.obj_export(filepath=os.path.join(folder, f"OBJ-{name}.obj"), export_selected_objects=True)
