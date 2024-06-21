import argparse
import os
import glob

parser = argparse.ArgumentParser()
parser.add_argument("input", type=str, help="Path to obj file")
args = parser.parse_args()

with open("template-link.txt", "r") as file:
    template_link = file.read()

mat_names: list[tuple[str, str]] = []

textures = glob.glob(os.path.join("Materials", "*.mat"))
for i, material in enumerate(textures):
    print(f"\r({i + 1}/{len(textures)}) reading material for {material}")
    name = os.path.splitext(os.path.basename(material))[0]
    with open(material + ".meta", "r") as file:
        guid = file.readlines()[1].split(":")[1].strip()

    mat_names.append((name, guid))

with open(args.input + ".meta", "r") as file:
    obj_meta = file.readlines()

i = 0
while i < len(obj_meta) and obj_meta[i].strip() != "externalObjects: {}":
    i += 1

if i == len(obj_meta):
    print(f"Error! externalObjects line not found in {args.input + '.meta'}. (malformed meta file?)")
    exit(1)

obj_meta[i] = obj_meta[i].replace(" {}", "")
i += 1
for name, guid in mat_names:
    mat_ref = template_link.replace("$$GUID_PLACEHOLDER$$", guid).replace(
        "$$NAME_PLACEHOLDER$$", name
    )

    obj_meta.insert(i, mat_ref)

with open(args.input + ".meta", "w") as file:
    file.writelines(obj_meta)
