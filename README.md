# Modo to USD Shadertree exporter v1.0

If you're trying to export Modo scenes to Houdini (as an example but It may be Blender too I think), you're condemned to do over all your shaders tin order to have them rendered with Karma.
This plugin is intended to export your shader tree as a whole into a USD file that allows to get all your material back in Houdini as a USD layer, and to reassign it automatically to your meshes polygon tag/geom subsets.

## Current support
It's in beta actually, but works quite well on my side (almost for 80% of my needs) :  
• Basic shading is supported (gtr and principled BRDFs)  
• Basic texture layers compositing is supported (blend modes, opacity stacking)  
• A secondary, real-time preview material (`UsdPreviewSurface`) can optionally be exported alongside the main MaterialX shader, for viewers/renderers that don't read MaterialX — see "Export Preview Gl" below; textured materials currently show up plain white through this preview path (constant-value materials are fine), this is a known limitation  
• 3d textures and gradients are not yet supported (and will probably never be as they are too much Modo specifics, and not supported by USD/MTLX)  
• Automatic assignment is supported through a Python node (available in sample scene package, see `Scripts/Houdini/AssignMaterials.py`) in houdini (or manually if you like)  
• Each material can be overridden manually using a Edit Material Network Node in Houdini Stage Graph.  

## Options
Options are available through preferences (Shader Tree Export), split into three groups :

**Output properties**  
• Export as JSON — dumps the shader tree structure as a `.json` file, mostly useful for debugging/inspection  
• Export as XML — dumps the shader tree structure as a `.xml` file (raw, as read from Modo)  
• Export as USD — writes a binary/crate `.usd` file (on by default)  
• Export as USDa — writes a human-readable, text `.usda` file  
• (JSON/XML/USD/USDa can all be enabled at the same time; USD and USDa contain the same data, just in different USD file formats)  
• Consolidate Scene — copies all texture files referenced by the shader tree into a `<scene_name>_textures` folder next to the scene file; files in that folder that are no longer referenced get moved into an `unused` sub-folder instead of being deleted  
• Save diagnostic file — writes a `<scene_name>_diagnostic.xml` file listing every conversion/export decision made (created shaders, skipped/unsupported items, blend modes, etc.) — the main tool for troubleshooting an export that doesn't look right (on by default)  

**Event Log Options**  
• Verbose — prints export progress to Modo's Event Log as the shader tree is walked  
• Out Stage Changes — with Verbose on, also logs every USD stage modification (node creation, connections...) — the most detailed log level  

**USD Options**  
• Export Preview Gl — additionally builds a `UsdPreviewSurface` shader for each material (see "Current support" above for its current limitation with textured materials)  

## How it works  
• Click on the USD icon button on top of your shader tree toolbar to export using your current preference settings  
• Alt-click to get a quick popover for toggling the output options above without opening the full preferences panel  

This kit is still under development, and need testing support, if you run into trouble, feel free to contact me or ask questions here.

The process have been proven working with abc exported mesh, but could also work with FBX i guess and maybe obj.

It's proven to work well with @Yan's models (that are incredibly details and of great quality ... the best in the market I would say)
