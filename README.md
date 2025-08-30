# Breathfang's Geometry Nodes Toolset Pack
![Breathfang Blender GeoNode Pack Logo Universal BG Color HD](https://github.com/user-attachments/assets/a1dcc293-1582-4459-bf55-b928728901b5)

Breathfang's Geometry Nodes Toolset Pack is a open source of Pre-made Geometry Nodes for Blender that can generate, adding modifier into GeoNode which will help you during modelling the model or scenering. This Toolset pack is free for Commercial Use based on GPL-3.

If you're not understand or newbie user want to use nodes and not understand, refer at here: [breathfanggeonodes.readthedocs.io](https://breathfanggeonodes.readthedocs.io/en/latest/)

# Other websites to download our GeoNodes pack
If you want to get other version (not including dev/preview version), here is the link, no worries for my :
- [Gumroad](https://breathfang.gumroad.com/l/LmHKz)
- [Superhivemarket (Blender Market)](https://superhivemarket.com/products/breathfang-node-packs)
- [extensions.blender.org](https://extensions.blender.org/add-ons/breathfangs-geometry-nodes-toolset-pack/)

# Blender Version Requirements
Here is minimum software version requirement to use Breathfang's Geometry Nodes Toolset Pack here:
| Version | Blender Version |
| ------- | ---------------- |
| v0.1.0-alpha | 4.2 LTS |
| v1.0.x-preview | 4.2 LTS |
| v1.1.x-alpha | 4.2 LTS |
| v1.2.x-preview | 4.2 LTS |
| v1.2.x-alpha | 4.2 LTS & 4.5 LTS (Extension Pack) |
| v1.3.x-preview | 4.2 LTS & 4.5 LTS (Extension Pack) |
| v1.3.x-alpha | 4.2 LTS & 4.5 LTS (Extension Pack) |
| v2.0.x-preview | 4.2 LTS & 4.5 LTS (Extension Pack) |
| v2.0.x-beta | 4.2 LTS & 4.5 LTS (Extension Pack) |
| and more | ... |

# How to use
> **Note**: To use Breathfang's Geometry Nodes Pack, refers to [breathfanggeonodes.readthedocs.io](https://breathfanggeonodes.readthedocs.io/en/latest/)
> **Please NEVER download .zip files that has been created by GitHub. Instead use the officially packaged versions.**

To import our geonode, it has two ways:

### Setup as Asset Library
If you want permanently available in Blender, so you can use Breathfang's Geometry Nodes Pack to all project files, here is the steps:
1. Download `Breathfang's Geometry Nodes Pack v1.0.x - Asset Library.zip`
2. Extract it to your desired destination
3. Open `Edit -> Preferences`
4. Go to `File paths -> Asset Libraries` then click `[+]` icon
5. Select `<downloaded_breathfang_geonode_pack_directory>` then press `Add Asset Library`
6. Then you're done! This is like a dragon honor invitiation! Hahaha...

## Setup as Add-on
If you want to use Breathfang's Geometry Nodes Pack as Add-on, here is the steps:
1. Download `Breathfang's Geometry Nodes Pack v1.0.x - Add-on.zip`
2. Extract it to your desired destination
3. Open `Edit -> Preferences`
4. Go to `Add-ons -> Install` then click `[+]` icon
5. Select `<downloaded_breathfang_geonode_pack_directory>` then press `Install`

# Updating
If you want to update Breathfang's Geometry Nodes Pack into newer version, just only download either .blend file or .zip file. But it has note, the note is your existing project that you've already using our Geometry Nodes will remain intact and will not be replaced. To update to newer node, you need to reconnecting again the nodes and re-setup again.

For changelogs, please see in either [Github releases](https://github.com/Breathfang/BreathfangGeoNodes/releases), [extensions.blender.org Changelogs](https://extensions.blender.org/add-ons/breathfangs-geometry-nodes-toolset-pack/versions/) or [breathfanggeonodes.readthedocs.io](https://breathfanggeonodes.readthedocs.io/en/latest/)

# Getting Support
If you have any trouble or problem or a question that means the documentation is not enough or still confused, you can:
- Create a new [issue](https://github.com/Breathfang/BreathfangGeoNodes/issues/new/choose) on Breathfang's Geometry Nodes Toolset Pack page
- Message me in our social media, including [@DrageonDB (X Twitter)](https://x.com/DrageonDB) or via [ArtStation](https://www.artstation.com/breathfang).

Please provide information as much as possible, including the details, problems, such as steps to reproduce the issue, screenshots, and so on.

# Contributing
Pull requests are welcome! If you'be like to add feature inside geometry nodes, new geometry node, fixing the geometry nodes bug, GeoNode icon changes, and so on then you're welcome!

Anyone can simply fork my repo, work on your changes, and then anyone can place .blend file and your icon .png for node icon into `nodes_collab` directory. We will recheck strictly what we allow in.

But all suggestions, recommendations, and more are welcome. If anyone unsure what you want to contribute, then anyone can [open issue](https://github.com/Breathfang/BreathfangGeoNodes/issues/).

I have one my today sentence: "I'm a Breathfang, Fang in your monster, despawn foes!"

# Contributing Requirements
- Blender 4.2 LTS (for base version) or 4.5 LTS (for extension pack)
- Python 3.13 or higher
- Required Packages: (you can auto install required packages by running _PackageAutoSetup.py_)
  - sphinx
  - sphinx-autobuild
  - sphinx_rtd_theme
  - pandas
  - logging

# How to run Guidebook preview before commit to GitHub
You can run .docsbuild.bat for build the documentation and it will host under http://127.0.0.1:8000.

If you update the documentation, it will be automatically refresh by sphinx-autobuild. This is includes save files, delete files, and putting files inside docs folder.

# How to generate .zip packaged file for Node Pack
To generate .zip packaged file for Node Pack, you can run _NodepackZipGenerator.py for generate .zip file.

# Upcoming Features
To see upcoming features, see in [Github Project](https://github.com/Breathfang/BreathfangGeoNodes/projects/)


# License
This project is released under the GPL-3 License. You can read the license in [Github](https://github.com/Breathfang/BreathfangGeoNodes/blob/main/LICENSE)

You can use Nodepack for commercial use freely.