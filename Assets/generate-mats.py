import glob
import os

with open("template-mat.txt", "r") as file:
    template_mat = file.read()

if not os.path.exists("Materials"):
    os.mkdir("Materials")

textures = glob.glob(os.path.join("Textures", "*.png"))
for i, texture in enumerate(textures):
    print(f"\r({i + 1}/{len(textures)}) Creating material for {texture}")
    name = os.path.splitext(os.path.basename(texture))[0]
    meta_path = texture + ".meta"
    with open(meta_path, "r") as file:
        guid = file.readlines()[1].split(":")[1].strip()

    with open(os.path.join("Materials", name + ".mat"), "w") as file:
        file.write(
            template_mat.replace("$$GUID_PLACEHOLDER$$", guid).replace(
                "$$NAME_PLACEHOLDER$$", name
            )
        )
