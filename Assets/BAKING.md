Here's the [finalised bake.py script](https://github.com/FlynnD273/Line-Up-Calculator/blob/stable/Assets/bake.py) (should be run in the Ascent Blender project. It will take a long time)
Once that's done, you'll need to open Unity, then run the [material generation script](https://github.com/FlynnD273/Line-Up-Calculator/blob/stable/Assets/generate-mats.py) and then the [material linking script](https://github.com/FlynnD273/Line-Up-Calculator/blob/stable/Assets/link-mats.py)

So the workflow looks like this:
I'll be using the Ascent Blender file as an example, but it should work pretty much the same for any other map. 

- Open the Ascent.blend project (it doesn't need to be in the Unity project, it can be wherever)
- Go to the text editor in Blender, and open the `bake.py` file
- Run that file. It will take a long time. It's faster if you have a GPU, but it will still take a while. My friend's PC took like 10 hours with an RTX 3070
	- If you want to increase the final texture resolution, change the `tex_size` variable on line 6 of the `bake.py` script. If you edit the script outside of Blender, make sure to reload the file in Blender to get the new changes
- Copy the `Textures` folder, the `OBj-Ascent.obj` file, and the `OBJ-Ascent.mtl` file into the Unity Assets folder
- Open Unity and let it import all the textures. This will take a while
- Copy the `generate-mats.py` and `link-mats.py` scripts into the Assets Unity folder (if you haven't already)
- You must have Python installed for the next part
- Open command prompt and navigate to the Unity Assets folder. On Windows you can do this by navigating to the folder in File Explorer and click the directory path bar at the top, type in `cmd` and hitting enter. On Linux you'll have to run `cd 'Path to the Unity Assets folder'` in your shell. You can do the same on Mac, I don't know if there's an easier way
- Type `python generate-mats.py` and hit enter in the command prompt window
- Open the Unity project through Unity again (if you didn't close it, just tab over to it and let it import everything)
- Run the `link-materials.py` script
	- In that same command-prompt window as before, type `python link-mats.py OBJ-Ascent.obj` and hit enter
- Tab back to Unity, and all the materials should be linked properly

I've tested this on a smaller file, but my laptop cannot open the full map in Unity
