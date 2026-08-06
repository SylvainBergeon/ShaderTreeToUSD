# python

# Use the drop down menu to select example code snippets.
node = hou.pwd()

# Add code to fetch node parameters and evaluate primitive patterns.
# This should be done before calling editableStage or editableLayer.
# paths = hou.LopSelectionRule("/*").expandedPaths(node.input(0))

# Add code to modify the stage.
stage = node.editableStage()

from pxr import Usd, Sdf, UsdShade, UsdGeom

matList = {}

def traverse_branch(stage, start_path):
    # Get the root prim of the branch at the specified path
    root_prim = stage.GetPrimAtPath(start_path)
    
    if not root_prim:
        #print(f"Prim at path {start_path} not found!")
        return
    
    traverse_prim(root_prim)

def traverse_prim(prim):
    if prim.GetTypeName() == "Material":
        path = prim.GetPath().pathString
        name = path.split("/")[len(path.split("/"))-1]
        matList[name] = path
        #print ("found %s with path %s" % (name, path))
    # Traverse all child prims
    for child in prim.GetChildren():
        traverse_prim(child)

    
traverse_branch(stage, "/shadertree")

#print("=======================================")
for name in matList:
    p = matList[name]
    #print(name + " = " + p)
#print("=======================================")

for prim in stage.Traverse():
    if prim.GetTypeName() == 'GeomSubset':
        subsetName = prim.GetName()
        matname = subsetName.replace("material_", "")
        prim.CreateAttribute('familyName', Sdf.ValueTypeNames.String).Set('materialBind')
        # Lier le matériau à ce GeomSubset
        if matname in matList.keys():
            print(subsetName + " = " + matname + "->" + matList[matname])
            materialBinding = prim.GetRelationship('material:binding')
            #materialBinding = prim.CreateRelationship('material:binding', True)
            materialBinding.SetTargets([Sdf.Path(matList[matname])])