import argparse
import os
import glob

parser = argparse.ArgumentParser()
parser.add_argument("input", type=str, help="Path to obj file")
args = parser.parse_args()

with open("template-link.txt", "r") as file:
    template_link = file.read()

mat_names: list[tuple[str, str]] = []

print("Reading materials...")
textures = glob.glob(os.path.join("Materials", "*.mat"))
for i, material in enumerate(textures):
    name = os.path.splitext(os.path.basename(material))[0]
    with open(material + ".meta", "r") as file:
        guid = file.readlines()[1].split(":")[1].strip()

    mat_names.append((name, guid))
print("Done.\nLinking materials...")

with open(args.input + ".meta", "r") as file:
    obj_meta = file.readlines()

i = 0
while i < len(obj_meta) and obj_meta[i].strip() != "externalObjects: {}":
    i += 1

if i == len(obj_meta):
    print("Nonempty meta file detected. Resetting...")
    i = 0
    while i < len(obj_meta) and obj_meta[i].strip() != "externalObjects:":
        i += 1

    end = i
    while end < len(obj_meta) and obj_meta[end].strip() != "materials:":
        end += 1

    if end == len(obj_meta):
        print(f"Error! Error parsing {args.input + '.meta'}. (malformed meta file?)")
        exit(1)

    del obj_meta[i + 1:end - 1]

obj_meta[i] = obj_meta[i].replace(" {}", "")
i += 1
for name, guid in mat_names:
    mat_ref = template_link.replace("$$GUID_PLACEHOLDER$$", guid).replace(
        "$$NAME_PLACEHOLDER$$", name
    )

    obj_meta.insert(i, mat_ref)
print("Done.")

with open(args.input + ".meta", "w") as file:
    file.writelines(obj_meta)
