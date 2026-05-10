## Requirements

### For contributing blend file
- Blender 4.5 LTS (for base version)
- Blender 5.2 LTS (for extension pack)
- For contributing .blend file, you will need to create a new blend file and put into `GN_Blend_File` folder.
- I could improve your nodes and merge it into a main file if I've considered your .blend file is ready to merge it (with notification).
- You can comtribute between Geometry Nodes and Shading Nodes.

### For contributing addon file
- Blender 4.5 LTS (for base version)
- Blender 5.2 LTS (for extension pack)
- Addon must be interoperable with Blender 4.5 LTS and 5.2 LTS, but it's not required for newer version of Blender until next Blender LTS released.
- Python 3.13 or higher
- Some required packages that you can install by running _PackageAutoSetup.py_

### For contributing documentation
- Required Packages: (you can auto install required packages by running _PackageAutoSetup.py_)
  - sphinx
  - sphinx-autobuild
  - sphinx_rtd_theme
  - pandas
  - logging
- I recommend to debug documentation using [sphinx-autobuild](https://sphinx-autobuild.readthedocs.io/en/latest/)
- Documentation SHOULD BE READY and COMPLETED before v3.0.0-stable

## Q&A

### How to contribute
To contribute to this project, here are some ways:
- Just by creating a new .blend file. DO NOT edit the main file, I will merge it manually.
- OR you can create issue on Github and upload your created/updated node .blend file.

### How long time does it take to merge?
I will merge your .blend file as soon as possible if I consider your .blend file is ready and your .blend file is okay.

### Do I allow embed python script inside .blend file?
NO, you can't embed python script inside .blend file. This is due to security reasons and how blender works. If you already embed python script inside .blend file, then you're not allowed to contribute to this project or you will be banned from contributing. But you can embed python script inside addon folder, but NOT inside .blend file.

### Why my node isn't merged after getting next update of DragonGraph Toolset Pack?
Here are some reasons why my node isn't merged after getting next update of DragonGraph Toolset Pack:
- Your node isn't ready yet.
- Your node is not okay.
- Your node is buggy or unsafe.
- Your node contains python script.
- Your pull request or issue isn't getting approved (if you have created a pull request or issue).

### Can I contribute to Node Pack for non-geometry nodes (like shading nodes, composite nodes, etc)?
Sure, you can contribute to Node Pack for non-geometry nodes, but you need to create a new category inside Blender Assets for non-geometry nodes.

### Can I use other node from other node pack (Like Bradley's Node Pack, Higgsas's Node Pack, etc) to remake my node for contributing to Node Pack?
Yeah, it's okay as long as you're improving remade node after you already remake it. I don't allow to contribute with remake other node from other node pack and copying to this node pack without significant changes or improvements.

### Can I contribute with newer version of Blender (not base version or extension pack)?
Sure, you can contribute with newer version of Blender. But you will be delayed to get merged into main file until next Blender LTS release. But I will try to get merged as soon as possible after Blender next LTS released. You'll need to create a new category inside Blender Assets for newer version of Blender, like `Collabs > 5.3`.

### Can I use Node Pack for commercial use?
Yes, you can use Node Pack for commercial use. We released Node Pack under GPL-3 license.

### Why I'm getting banned from contributing?
If you're getting banned from contributing, it's because you're not following our [Contributing Requirements](#Contributing-Requirements). If you're getting banned from contributing, DO NOT circumvent it with other github account. Appeal it via social media that i've listed in [Github](https://github.com/Breathfang/BreathfangGeoNodes).