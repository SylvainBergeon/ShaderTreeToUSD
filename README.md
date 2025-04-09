# Modo to USD Shadertree exporter v1.0

If you're trying to export Modo scenes to Houdini (as an example but It may be Blender too I think), you're condemned to do over all your shaders tin order to have them rendered with Karma.
This plugin is intended to export your shader tree as a whole into a USDA file that allows to get all your material back in Houdini as a USD layer, and to reassign it automatically to your meshes polygon tag/geom subsets.

## Current support
It's in beta actually, but works quite well on my side (almost for 80% of my needs) :
• Basic shading is supported
• Basic texture layers compositing is supported
• 3d textures and gradients are not yet supported (and will probably never be as they are too much Modo specifics, and not supported by USD/MTLX)
• Automatic assignment is supported through a Python node (available in sample scene package) in houdini (or manually if you like)
• Each material can be overridden manually using a Edit Material Network Node in Houdini Stage Graph.

## Options
Options are available through  preferences :
• Export as (json, xml, usda)
• Filter log outputs
• Output diagnostic xml file for debugging

## How it works
• Click on the USD icon button on top of your shader tree toolbar
• Alt-click to fast select output formats

This kit is still under development, and need testing support, if you run into trouble, feel free to contact me or ask questions here.

The process have been proven working with abc exported mesh, but could also work with FBX i guess and maybe obj.

It's proven to work well with @Yan's models (that are incredibly details and of great quality ... the best in the market I would say) see pictures below
