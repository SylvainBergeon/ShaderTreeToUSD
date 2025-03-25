# python

import os, shutil
import re, sys, math, json
import lx, modo
from collections import OrderedDict
from pathlib import Path
from pxr import Sdf, Usd, UsdShade, UsdGeom

from .ShaderFilters import usdInputMap
from .ShaderFilters import usdTypeMap
from .ShaderFilters import channelTypeMap
from .ShaderFilters import stdMatChannelMap

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
    
# Fix Python 3 issues
if sys.version_info[0] == 3:
    xrange = range
    basestring = str
    long = int

class ShadingContext:
    """
    A class representing a shading context in a USD environment.

    Attributes:
        material (UsdShade.Material): The material associated with the shading context.
        shader (UsdShade.Shader): The primary shader used in the shading context.
        previewShader (UsdShade.Shader): The shader used for preview purposes.
        path (str): The path to the shading context.
        parentPath (str): The path to the parent of the shading context.
        advancedMaterialChannels (ET.Element): XML element representing advanced material channels.
    """
    
    material: UsdShade.Material = None
    shader: UsdShade.Shader = None
    previewShader: UsdShade.Shader = None
    path: str = ""
    parentPath: str = ""
    advancedMaterialChannels: ET.Element
    effectsStack:OrderedDict = OrderedDict()

class shaderConnector:
    name:str
    output:UsdShade.Output
    opacity:float
    blend:str
    
    def dump(_self) -> str:
        return (f"{_self.name} {_self.output.GetBaseName()} {_self.blend} {_self.opacity}")
    
# textureList is used to store the source path of any texture used by the shaders
# in order to later consolidate the scene by copying all these textures to a consolidated folder
textureList = dict()

# Global variables for user preferences
consolidateScene = None
exportGlPreviewMaterial = None
export_json = None
export_xml = None
export_usda = None
export_diagnostic = None
verbose = None
verbose_set_value = None
verbose_create_shader = None
verbose_override_value = None
verbose_modify_tree = None
verbose_consolidate = None
verbose_unsupported = None
export_diagnostic = None

xml_diagnostic = None

def diag(sectionName:str, diagElementName:str, diagtext:str):
    if not export_diagnostic: return
       
    section = xml_diagnostic.find(sectionName)
    if section is None:
        section = ET.Element(sectionName)
        xml_diagnostic.append(section)
        
    diagElement = ET.Element(diagElementName)
    diagElement.text = diagtext
    
    section.append(diagElement)
        
def initialize_preferences():
    """Initialize global variables with user preferences."""
    global consolidateScene, exportGlPreviewMaterial
    global export_json, export_xml, export_usda, export_diagnostic
    global verbose, verbose_set_value, verbose_create_shader
    global verbose_override_value, verbose_modify_tree
    global verbose_consolidate, verbose_unsupported

    consolidateScene = lx.eval('user.value USDExport_consolidateScene ?')
    exportGlPreviewMaterial = lx.eval('user.value USDExport_exportGlPreviewMaterial ?')
    export_json = lx.eval('user.value USDExport_export_json ?')
    export_xml = lx.eval('user.value USDExport_export_xml ?')
    export_usda = lx.eval('user.value USDExport_export_usda ?')
    export_diagnostic = lx.eval('user.value USDExport_saveDiagnostic ?')
    verbose = lx.eval('user.value USDExport_verbose ?')
    verbose_set_value = lx.eval('user.value USDExport_verboseSetValue ?')
    verbose_create_shader = lx.eval('user.value USDExport_verboseCreateShader ?')
    verbose_override_value = lx.eval('user.value USDExport_verboseOverrideValue ?')
    verbose_modify_tree = lx.eval('user.value USDExport_verboseModifyTree ?')
    verbose_consolidate = lx.eval('user.value USDExport_verboseConsolidate ?')
    verbose_unsupported = lx.eval('user.value USDExport_verboseUnsupported ?')
    
# Call this function at the start of your script or before using the preferences
initialize_preferences()

# Command hook
def export_basic_execute(Cmd_obj, msg):
    """
    Exports the current modo scene's shader tree to JSON, XML, and USDA formats.

    This function retrieves the current modo scene, extracts the shader tree
    associated with the primary renderer, and exports it in three different formats:
    JSON, XML, and USDA. The exported files are saved with the same base name as
    the scene file, but with different extensions based on the format.

    Parameters:
        Cmd_obj: The command object, not used in this function.
        msg: The message object, not used in this function.
    """

    global xml_diagnostic
    if export_diagnostic:
        xml_diagnostic = ET.Element("diagnostic")
    
    scene = modo.scene.current()
    filename = basestring(scene.filename).removesuffix(".lxo")
    diag("Files", "Set", f"filename = {os.path.basename(filename)}.lxo")
    diag("Files", "Set", f"project path = {os.path.dirname(filename)}")

    renderer_id = scene.items(lx.symbol.sITYPE_POLYRENDER)[0].id
    renderer = scene.item(renderer_id)
    
    xml_shadertree = xmlExportItem(renderer)

    #----------- Write files
    #----------- as Json
    json_shadertree = jsonExportItem(renderer)
    if export_json: writeJson(filename, json_shadertree)

    #----------- as XML
    if export_xml: write_xml(filename, xml_shadertree)
    
    #----------- as usda
    if export_usda: write_usda(filename, xml_shadertree)
    
    #----------- Write diadnostic file
    if export_diagnostic:
        ET.indent(xml_diagnostic, space="   ")
        xmlString = ET.tostring(xml_diagnostic, method="xml", xml_declaration=True).decode()
        fout = open(filename + "_diagnostic.xml",'w') 
        fout.write(xmlString)
        fout.close()
        del xml_diagnostic
        
# Write the data as XML
def write_xml(fileName, xml:ET.Element):
    ET.indent(xml, space="   ")
    xmlString = ET.tostring(xml, method="xml", xml_declaration=True).decode()
    fout = open(fileName + ".xml",'w') 
    fout.write(xmlString)
    fout.close()
    
    diag("Files", "Save", f"{os.path.basename(fileName)}.xml saved succesfully !")

# Write the data as USDA
def write_usda(filename:str, xml:ET.Element):
    print("saving usd ...")
    
    stage = Usd.Stage.CreateNew(filename + '.usda')
    
    context = ShadingContext()
    context = USD_export_shadertree(stage, "/shadertree", context, xml)
    
    stage.GetRootLayer().Save()
    print("✅ USD saved")
    diag("Files", "Save", f"{os.path.basename(filename)}.usda saved succesfully !")
    
    #----------- consolidate scene
    if consolidateScene:
        copy_and_clean_files()
        print("✅ Scene consolidated")
        diag("Files", "Save", f"Consolidation succesful !")

# Write the data as JSON
def writeJson(filename, dictionary):
    with open(filename + ".json", 'w') as fout:
        json.dump(dictionary, fout, indent=1)
        fout.flush()
        
    diag("Files", "Save", f"{os.path.basename(filename)}.xm saved succesfully !")

# Recursively convert the shader tree structure to xml
def xmlExportItem(item:modo.Item):
    """
    Exports a modo item and its hierarchy to an XML element.

    This function creates an XML representation of a modo item, including its
    channels and child items. It handles specific item types by exporting
    additional dependencies linked through the item graph. The item's name is
    sanitized using `replace_chars` and `cleanName` functions to ensure valid
    XML attribute values.

    Parameters:
        item (modo.Item): The modo item to be exported to XML.

    Returns:
        xml.etree.ElementTree.Element: An XML element representing the modo item
        and its hierarchy.
    """
    
    out_xml = ET.Element(item.type)
    out_xml.set('name', replace_chars(str(item.name), ["(", ")", " "], "_"))
    out_xml.set('name', clean_name(str(item.name)))
    out_xml.set('id', item.id)
    out_xml.set('type', item.type)
    
    #-------------------------------------------------------
    # Store extra item dependencies based on shader tree item itemType
    # some items are linked to shader tree items (like texture locators)
    # but are not directly referenced inside the shader tree item list
    # they are connected through the itemGraph like dependencies
    #-------------------------------------------------------
    match item.type:
        case lx.symbol.sITYPE_IMAGEMAP | lx.symbol.sITYPE_NOISE | lx.symbol.sITYPE_CELLULAR | lx.symbol.sITYPE_FALLOFF:
            graph = item.itemGraph(lx.symbol.sGRAPH_SHADELOC)
    
            fwdItem:modo.Item
            for fwdItem in graph.forward(item.name):
                match fwdItem.type:
                    case lx.symbol.sITYPE_VIDEOSTILL: #----- Extract image file channels as xml element
                        out_xml.append(xmlExportItem(fwdItem))
                    
                    case lx.symbol.sITYPE_TEXTURELOC: #----- Extract texture locator channels as xml element
                        out_xml.append(xmlExportItem(fwdItem))
    
    #------------------------------- Export channels
    if len(item.channels()) > 0:
        channels = xmlGetChannels(item)
        out_xml.append(channels)
        
    #------------------------------- Export childs
    numChild = item.childCount()
    for i in range(numChild):
        itemChild = item.childAtIndex(i)
        out_xml.append(xmlExportItem(itemChild))
        
    return out_xml

# Grab all channels of an items and write it as separate xml elements in a channels structure
def xmlGetChannels(item:modo.Item):
    """
    Generate an XML representation of the channels of a given modo item.

    This function creates an XML element containing the channels of the specified
    modo item. It retrieves the channels using the `getChannels` function and
    formats them into XML elements. Each channel is represented as an XML element
    with its attributes, and if a channel is stored as a dictionary, it creates
    a nested XML structure to represent the dictionary's contents.

    Parameters:
        item (modo.Item): The modo item whose channels are to be exported to XML.

    Returns:
        xml.etree.ElementTree.Element: An XML element representing the channels of
        the modo item.
    """
    xml_out = ET.Element('channels')
    
    #------------------------------- Export channels
    if len(item.channels()) > 0:
        
        channelsDict:OrderedDict = getChannels(item)
        for chName in channelsDict:
            xmlChan = ET.Element(chName)
            
            for attName in channelsDict[chName]:
                att = channelsDict[chName][attName]
                if type(att) is dict: # --------------------------- if channel has bee stored as dict (structure)
                    dictName = list(att.keys())[0]
                    xmlChan.set(attName, dictName)
                    el = ET.Element(dictName)# -------------------- create an element containing the structure
                    for valName in att[dictName].keys():
                        el.set(valName, att[dictName][valName])
                    xmlChan.append(el)
                else: #-------------------------------------------- else create a simple attribute
                    xmlChan.set(attName, channelsDict[chName][attName])
            
            xml_out.append(xmlChan)
    
    return xml_out

# Recursively convert the shader tree structure to a Dict struccture (for json exoport)
def jsonExportItem(item:modo.Item):
    """
    Exports a modo item and its hierarchy to a JSON-compatible dictionary.

    This function recursively processes a modo item, extracting its name, ID, 
    type, and channels, and organizes this information into an OrderedDict. 
    If the item has child items, they are also processed and included in the 
    dictionary under their respective names.

    Args:
        item (modo.Item): The modo item to be exported.

    Returns:
        OrderedDict: A dictionary containing the item's details and its 
        children's details, suitable for JSON serialization.
    """
    
    out_dict = OrderedDict()
    out_dict['name'] = item.name
    out_dict['id'] = item.id
    out_dict['type'] = item.type
    
    #------------------------------- Export channels
    if len(item.channels()) > 0:
        out_dict["channels"] = getChannels(item)
        
    #------------------------------- Export childs
    for i in range(item.childCount()):
        itemChild = item.childAtIndex(i)
        out_dict[itemChild.name] = jsonExportItem(itemChild)
        
    return out_dict

# Grab all channels of an item and write it as separate Dict
def getChannels(item:modo.Item):
    """
    Retrieve and format the channels of a given modo item.

    This function iterates over the channels of the specified modo item,
    formats each channel using the `formatChannel` function, and stores
    the results in an ordered dictionary. If `preFilterChannels` is set
    to True, only channels that match the filters for the item's type
    are included. The resulting dictionary is sorted alphabetically by
    channel name before being returned.

    Parameters:
        item (modo.Item): The modo item whose channels are to be retrieved.

    Returns:
        OrderedDict: An ordered dictionary of formatted channels, sorted
        alphabetically by channel name.
    """
    
    d_channels = OrderedDict()

    mChan:modo.Channel
    for mChan in item.channels():
        chanName = str(mChan.name).split(".")[0] # Important ! if not using the first part of the name, channelTriple are treated as 3 channels
        d = formatChannel(item.channel(chanName), mChan.type, mChan.evalType, mChan.storageType)
        d_channels[chanName] = d
            
    
    alphaSort = OrderedDict(sorted(d_channels.items()))
    return alphaSort

# Format a channel to the right type (lots of weird stuff here, personnal cooking !)
def formatChannel(channel:modo.Channel, ctype:int, evalType:str, storageType:str):
    """
    Formats a modo.Channel object into a dictionary containing its properties.

    Parameters:
        channel (modo.Channel): The channel to be formatted.
        ctype (int): The channel type identifier.
        evalType (str): The evaluation type of the channel.
        storageType (str): The storage type of the channel.

    Returns:
        dict: A dictionary containing the channel's value, type, evaltype, and storageType.
        If any attribute is missing or an error occurs, appropriate error messages are included.
    """
    
    if (ctype == None) : ctype = "NONE"
    if (evalType == None) : evalType = "NONE"
    if (storageType == None) : storageType = "NONE"

    
    chan = {} #----------------------------------------------- container to receive the channels properties
    
    if storageType == "color1":storageType='color3'
    if evalType == "color1":evalType='color3'
        
    if type(channel) is modo.ChannelTriple:
        # values = channel.get()
        # for i in range(len(values)):
        #     value = channel.get()[i]
        #     print(type(value))
        
        
        try: chan['value'] = str(channel.get())
        except AttributeError: chan['value'] = "This channel has no value!"
        except: chan['value'] = "There was an error!"

    else:
        try: chan['value'] = formatChannelValue(channel)
        except AttributeError: chan['value'] = "This channel has no value!"
        except: chan['value'] = "There was an error!"
    
    try: chan['type'] = channelTypeMap[ctype]
    except AttributeError: chan['type'] = "This channel has no type!"
    except: chan['type'] = "There was an error!"
    
    try: chan['evaltype'] = evalType
    except AttributeError: chan['type'] = "This channel has no evaltype!"
    except: chan['type'] = "There was an error!"
    
    try: chan['storageType'] = storageType
    except AttributeError: chan['storageType'] = "This channel has no storageType!"
    except: chan['storageType'] = "There was an error!"
    
    return chan

def USD_export_shadertree(stage:Usd.Stage, path:str, context:ShadingContext, xml:ET.Element) -> ShadingContext:
    """
    Recursively exports a shader tree to a USD stage based on an XML representation.

    This function traverses the XML structure of a shader tree, creating corresponding
    USD nodes on the specified stage. It handles various shader elements such as
    'polyRender', 'mask', 'imageMap', 'noise', and 'advancedMaterial', constructing
    appropriate USD structures and connections according to the element type and its
    attributes.

    During the traversal, the function utilizes the `context.effectsStack` to manage
    the current stack of shader effects being applied. This stack is crucial for
    maintaining the correct order and hierarchy of effects, ensuring that each shader
    node is processed with the appropriate context. As the tree is traversed, effects
    are pushed onto or popped from the stack, allowing for nested shader operations
    to be correctly represented in the USD stage.

    Args:
        stage (Usd.Stage): The USD stage where the shader tree will be exported.
        path (str): The base path for the shader tree in the USD stage.
        context (ShadingContext): The current shading context, updated as the tree is traversed.
        xml (ET.Element): The XML element representing the current node in the shader tree.

    Returns:
        ShadingContext: The updated shading context after processing the shader tree.
    """
    #----------------------------------------------------------- Recursively explotre the shaderTree and update material usd path
    elementName = xml.tag
    
    #TODO : find a way to manage the override system using stacking priority, blending amount and blending type (mult, add, substract etc...)
    
    match elementName:
        #------------------------------------------------------- If shadertree root, explore all childs set shadertree path
        case 'polyRender':
            if (context.material == None):
                newpath = path
            if (verbose):print("✅ Create SHADERTREE at %s" % (path))
            diag("USD_Create", xml.tag, f"Create SHADERTREE at {path}")
            
            UsdGeom.Scope.Define(stage, newpath)
            
            for child in xml.findall('*'):
                context = USD_export_shadertree(stage, newpath, context, child)

        #------------------------------------------------------- If mask, explore all child layers
        case 'mask':
            if xml.find("channels/enable").get('value') == "1" :
                ptag = xml.find("channels/ptag").get("value")
                
                if ptag != "":
                    newpath = path + "/" + clean_name(ptag)
                    if (verbose and verbose_modify_tree):print("✅ Create MASK at [%s]" % (newpath))
                    diag("USD_Create", xml.tag, f"Create MASK at [{newpath}]")
                    #---------------------------------------------------- Create material definition
                    material = UsdShade.Material.Define(stage, newpath)
                    context.material = material
                
                else:
                    newpath = path + "/" +  clean_name(xml.get('name'))
                    if (verbose and verbose_modify_tree):print("✅ Create SCOPE at [%s]" % (newpath))
                    diag("USD_Create", xml.tag, f"Create SCOPE at [{newpath}]")
                    #---------------------------------------------------- Create sub scope definition
                    UsdGeom.Scope.Define(stage, newpath)
                
                for child in xml.findall('*'):
                    if child.tag != "channels":
                        context = USD_export_shadertree(stage, newpath, context, child)
                    else:
                        pass
                    
                #-------------------------------------------------------- Connect child effects together
                for effectName in context.effectsStack.keys():
                    
                    # ////////////////////////////////// WEAK - Should be better too use a dedicated mapping table with default value or something
                    #----------------------------------------------------- Retrieve the modo input name from effect name using usd name as pivot mapping value
                    usdInputName = usdInputMap['effect'][effectName]
                    modoInputName = get_key_from_value(stdMatChannelMap[lx.symbol.sITYPE_ADVANCEDMATERIAL]['principled'], usdInputName)
                    if context.advancedMaterialChannels.find(modoInputName) != None:
                        materialInputValue = context.advancedMaterialChannels.find(modoInputName).get('value')
                    else:
                        materialInputValue = floatToOutType("0.0", usdTypeMap[usdInputName])
                    
                    output = materialInputValue
                    # ////////////////////////////////// WEAK
                    
                    #----------------------------------------------------- Create connections
                    for connectorIndex in range(0, len(context.effectsStack[effectName])):
                        connector:shaderConnector = context.effectsStack[effectName][connectorIndex]
                        # Create the connector nodes, connect the previous output and expose the new output
                        output = USD_connect_operator(stage, newpath, connector, output)
                
                    #---------------------------------------------------- Connect the latest exposed output to the shader input corresponding to the current effect
                    USD_connect_texture_output_to_shader_input(stage, context, effectName, output, xml)
                
                #-------------------------------------------------------- Reset stacks
                context.effectsStack = OrderedDict()
            
        #------------------------------------------------------- If imageMap, set USD graph with adjustments based on still image properties and effects
        case "imageMap":
            material:UsdShade.Material = context.material
            shader:UsdShade.Shader = context.shader
            previewShader:UsdShade.Shader = context.previewShader
            name = clean_name(xml.get('name'))
            path:Path = material.GetPath().AppendPath(name)
            
            #---------------------------------------------------- Connect texture to shader and previewShader inputs if possible
            if xml.find('channels/enable').get('value') == "1":
                effectName = xml.find('channels/effect').get('value')
                sdfType = usdTypeMap[usdInputMap['effect'][effectName]]
                
                if (verbose and verbose_modify_tree):print("✅ Create IMAGEMAP at %s as %s" % (path, effectName))
                diag("USD_Create", xml.tag, f"Create IMAGEMAP at [{path}] as [{effectName}]")
                
                textureOutput:UsdShade.Output = USD_create_texture_output(stage, context, xml, sdfType)
                
                #---------------------------------------------------- Add output to the current effect stack in context
                context = addShaderConnectorToContext(xml, textureOutput, context)
        
        #------------------------------------------------------- If imageMap, set USD graph with adjustments based on still image properties and effects
        case "noise":
            material:UsdShade.Material = context.material
            shader:UsdShade.Shader = context.shader
            
            if xml.find('channels/enable').get('value') == "1":
                effectName = xml.find('channels/effect').get('value')
                materialPath = material.GetPath()
                
                if (verbose and verbose_modify_tree):print("✅ Create 3D NOISE at %s as %s" % (path, effectName))
                diag("USD_Create", xml.tag, f"Create 3D NOISE at [{path}] as [{effectName}]")
                
                texLocatorOutput = USD_create_3D_texture_transform(stage, materialPath, xml)
                textureOutput = USD_create_3d_texture(stage, materialPath, xml, texLocatorOutput)
                
                #---------------------------------------------------- Connect to shader input
                USD_connect_texture_output_to_shader_input(stage, context, effectName, textureOutput, xml)
    
                #---------------------------------------------------- Add output to the current effect stack in context
                context = addShaderConnectorToContext(xml, textureOutput, context)

        case "constant":
            material:UsdShade.Material = context.material
            shader:UsdShade.Shader = context.shader
            
            if xml.find('channels/enable').get('value') == "1":
                effectName = xml.find('channels/effect').get('value')
                sdfType = usdTypeMap[usdInputMap['effect'][effectName]]
                materialPath = material.GetPath()
                
                if (verbose and verbose_modify_tree):print("✅ Create CONSTANT at %s as %s" % (path, effectName))
                diag("USD_Create", xml.tag, f"Create CONSTANT at [{path}] as [{effectName}]")
                
                constantOutput = USD_create_constant(stage, materialPath, xml, sdfType)
                
                #---------------------------------------------------- Add output to the current effect stack in context
                context = addShaderConnectorToContext(xml, constantOutput, context)
            

        #------------------------------------------------------- If material, create shader at defined path
        case 'advancedMaterial':
            # -------------------------------------------------- if has no context, then do nothing, as it's probably a shader that's outside a mask
            if context.material is None: return context
            
            material:UsdShade.Material = context.material
            if (verbose and verbose_modify_tree):print("✅ Create ADVANCED MATERIAL at %s" % (material.GetPath()))
            diag("USD_Create", xml.tag, f"Create ADVANCED MATERIAL at {material.GetPath()}")
            #---------------------------------------------------- Create material definition
            shader = USD_create_shader(stage, material, xml, False)
            context.shader = shader
            context.advancedMaterialChannels = xml.find("channels")
            #---------------------------------------------------- Create gl preview material definition
            if (exportGlPreviewMaterial):
                previewShader = USD_create_shader(stage, material, xml, True)
                context.previewShader = previewShader
        
        case "channels":
            pass
        
        case _:
            if(verbose and verbose_unsupported): print(f"❎ Unsupported: {elementName} item type is not yet supported")
            diag("Unsupported", "Item_Type", f"[{elementName}] is not yet supported (ignored)")
 
    return context

def USD_create_constant(stage:Usd.Stage, path:Path, xml:ET.Element, outType:Sdf.ValueTypeNames) -> UsdShade.Output: 
    #---------------------------------------------------- Create texture definition even if modo layer is disabled
    constantPath:Path = path.AppendPath(clean_name(xml.get('name')))
    constantShader = UsdShade.Shader.Define(stage, constantPath)
    constantShader.CreateIdAttr("ND_constant" + getNodeTypePrefix(outType))
    output:UsdShade.Output = constantShader.CreateOutput("out", outType)
    
    return output

def USD_create_3d_texture(stage:Usd.Stage, path:Path, xml:ET.Element, texLocatorOutput:UsdShade.Output) -> UsdShade.Output:    
    #---------------------------------------------------- Create texture definition even if modo layer is disabled
    noisePath:Path = path.AppendPath(clean_name(xml.get('name')))
    noiseShader = UsdShade.Shader.Define(stage, noisePath)
    noiseShader.CreateIdAttr("ND_unifiednoise3d_float")
    
    #---------------------------------------------------- Common
    noiseShader.CreateInput("position", Sdf.ValueTypeNames.Vector3f).ConnectToSource(texLocatorOutput)
    noiseShader.CreateInput("freq", Sdf.ValueTypeNames.Vector3f).Set((1.0,1.0,1.0))
    noiseShader.CreateInput("offset", Sdf.ValueTypeNames.Vector3f).Set((0.0,0.0,0.0))
    noiseShader.CreateInput("Jitter", Sdf.ValueTypeNames.Float).Set(1.0)
    noiseShader.CreateInput("type", Sdf.ValueTypeNames.Int).Set(3) # 0:Perlin 1:Cell 2:Worley 3:Fractal
    
    #---------------------------------------------------- Post Process
    noiseShader.CreateInput("outmin", Sdf.ValueTypeNames.Float).Set(float(xml.find('channels/value1').get('value'))/2 + 0.5)
    noiseShader.CreateInput("outmax", Sdf.ValueTypeNames.Float).Set(float(xml.find('channels/value2').get('value')))
    noiseShader.CreateInput("clampoutput", Sdf.ValueTypeNames.Int).Set(0)
    
    #---------------------------------------------------- Fractal
    noiseShader.CreateInput("octaves", Sdf.ValueTypeNames.Int).Set(int(xml.find('channels/freqs').get('value')))
    noiseShader.CreateOutput("lacunarity", Sdf.ValueTypeNames.Float).Set(float(xml.find('channels/freqRatio').get('value')))
    noiseShader.CreateOutput("diminish", Sdf.ValueTypeNames.Float).Set(float(xml.find('channels/ampRatio').get('value')))
    
    return noiseShader.CreateOutput("out", Sdf.ValueTypeNames.Float)
    
def USD_connect_operator(stage, path:str, connector:shaderConnector, input:UsdShade.Output) -> UsdShade.Output:
    """
    Connects a shader output to a specified input using a blend operator.

    This function defines a shader operator based on the blend type and connects
    the shader output to the input. It supports various blend effects and handles
    opacity as a mix factor. If the blend effect is unsupported, it returns the
    original output.

    Parameters:
        stage: The USD stage where the shader is defined.
        path (str): The path to the shader node.
        connector (shaderConnector): Contains the shader connection details.
        input (UsdShade.Output): The input to connect to.

    Returns:
        UsdShade.Output: The resulting shader output after applying the blend.
    """
    name = connector.name
    blend:str = connector.blend
    opacity:float = connector.opacity
    output:UsdShade.Output = connector.output
    outType = output.GetTypeName()
    
    texturePath = str(path) + "/" + name
    
    if verbose and verbose_modify_tree: print(f"✅ CONNECT: {input} x {opacity} -> {blend} -> {connector.name}")
    
    #----------------------------------------------------- If blend effect not supported
    if not (blend in usdInputMap["blend"].keys()) or usdInputMap["blend"][blend] == "":
        if verbose and verbose_unsupported: print(f"❎ Unsupported: {blend} blend effect is not yet supported")
        diag("Unsupported", "Blend_Mode", f"[{blend}] in {texturePath} is not yet supported (ignored)")
        return output
    
    match blend:
        case lx.symbol.sICVAL_TEXTURELAYER_BLEND_MULTIPLY | lx.symbol.sICVAL_TEXTURELAYER_BLEND_DIVIDE:
            #----------------------------------------------------- Set effect blend operator
            operator:UsdShade.Shader = UsdShade.Shader.Define(stage, texturePath + "_blend")
            usdOperatorName = usdInputMap["blend"][blend] + getNodeTypePrefix(outType)
            operator.CreateIdAttr(usdOperatorName)
            operator.CreateInput('in1', output.GetTypeName()).ConnectToSource(output)
            
            #----------------------------------------------------- Set or connect input depending on its type
            if type(input) is UsdShade.Output:
                operator.CreateInput('in2', output.GetTypeName()).ConnectToSource(input)
            else:
                operator.CreateInput('in2', output.GetTypeName()).Set(eval(input))
            
            output = operator.CreateOutput('out', outType)
            
            #----------------------------------------------------- set opacity as mix
            operator:UsdShade.Shader = UsdShade.Shader.Define(stage, texturePath + "_amount")
            usdOperatorName = "ND_mix" + getNodeTypePrefix(outType)
            operator.CreateIdAttr(usdOperatorName)
            operator.CreateInput('fg', output.GetTypeName()).ConnectToSource(output)
            
            #----------------------------------------------------- Set or connect input depending on its type
            if type(input) is UsdShade.Output:
                operator.CreateInput('bg', output.GetTypeName()).ConnectToSource(input)
            else:
                operator.CreateInput('bg', output.GetTypeName()).Set(eval(input))
            
            operator.CreateInput('mix', Sdf.ValueTypeNames.Float).Set(opacity)
            
            #----------------------------------------------------- Expose output
            output = operator.CreateOutput('out', outType)
            
        case _:
            #----------------------------------------------------- Set effect blend operator and opacity as mix
            operator:UsdShade.Shader = UsdShade.Shader.Define(stage, texturePath + "_blend")
            usdOperatorName = usdInputMap["blend"][blend] + getNodeTypePrefix(outType)
            operator.CreateIdAttr(usdOperatorName)
            operator.CreateInput('fg', output.GetTypeName()).ConnectToSource(output)
            
            #----------------------------------------------------- Set or connect input depending on its type
            if type(input) is UsdShade.Output:
                operator.CreateInput('bg', output.GetTypeName()).ConnectToSource(input)
            else:
                operator.CreateInput('bg', output.GetTypeName()).Set(eval(input))
            
            #----------------------------------------------------- Set or connect input depending on its type
            operator.CreateInput('mix', Sdf.ValueTypeNames.Float).Set(opacity)
            
            #----------------------------------------------------- Expose output
            output = operator.CreateOutput('out', outType)
    
    return output

def get_key_from_value(dict, value):
    """
    Retrieve the key associated with a given value in usdInputMap['effects'].

    Parameters:
        value: The value for which the corresponding key is sought.

    Returns:
        The key associated with the given value, or None if not found.
    """
    for key, val in dict.items():
        if val == value:
            return key
    return None

def addShaderConnectorToContext(xml:ET.Element, output:UsdShade.Output, context:ShadingContext) -> ShadingContext:
    #----------------------------------------------------------- create effectStack if doesn't exist yet for this effect
    if xml.find("channels/effect") != None:
        effectName = xml.find("channels/effect").get("value")
        if not effectName in context.effectsStack.keys():
            context.effectsStack[effectName] = []
        
        #----------------------------------------------------------- Set values for the shaderConnection
        shaderConnection = shaderConnector()
        shaderConnection.name = xml.get("name")
        shaderConnection.output = output
        shaderConnection.blend = xml.find("channels/blend").get("value")
        shaderConnection.opacity = float(xml.find("channels/opacity").get("value"))
        
        #----------------------------------------------------------- Add this connector to the stack
        context.effectsStack[effectName].append(shaderConnection)
        
    return context
    
# Create USD shader for advanced material layer
def USD_create_shader(stage:Usd.Stage, material:UsdShade.Material, xml:ET.Element, isPreview:bool) -> UsdShade.Shader: 
    """
    Create a USD shader from an XML element and add it to a given stage and material.

    This function defines a shader on the specified USD stage using the path derived
    from the material and XML element. It configures the shader based on whether it
    is a preview or not, setting attributes and creating inputs from the XML channels.
    The shader is then connected to the material's output.

    Parameters:
        stage (Usd.Stage): The USD stage where the shader will be defined.
        material (UsdShade.Material): The material to which the shader will be connected.
        xml (ET.Element): An XML element containing shader channel data.
        isPreview (bool): Flag indicating if the shader is a preview shader.

    Returns:
        UsdShade.Shader: The created USD shader.
    """
    
    path:Path = material.GetPath().AppendPath(clean_name(xml.get('name')))
    
    #---------------------------------------------------- Get brdfType value for remapping
    if (isPreview):
        brdfType = 'glPreview'
        path = str(path) + "_preview"
        connectorOut = "surface"
        materialConnector = ""
        surfaceId = "UsdPreviewSurface"
        if (verbose and verbose_create_shader) :print ("✅ Create PREVIEW SHADER at : %s" % path)
        diag("createUsdShader", xml.get('name'), "Create PREVIEW SHADER at : %s" % path)
    else:
        brdfType = xml.find('channels/brdfType').get('value')
        connectorOut = 'surface'
        materialConnector = "mtlx:"
        surfaceId = "ND_standard_surface_surfaceshader"
        if (verbose and verbose_create_shader) :print ("✅ Create SHADER at : %s" % path)
        diag("createUsdShader", xml.get('name'), "Create SHADER at : %s" % path)
    
        
    shader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
    shader.CreateIdAttr(surfaceId)
    #---------------------------------------------------- Create shader properties and input values
    for channel in xml.findall('channels/*'):
        
        # Convert the channel name to its usdstandard_material equivalent input
        
        modoInputName = channel.tag
        usdValue = channel.get('value')
        
        usdInputName = getMappedChannel(modoInputName, xml.get('type'), brdfType)
        # print(usdInputName)
        if not isPreview:
            usdValue = applyOverrides(usdValue, brdfType, modoInputName, xml)
        if usdInputName != None:
            input = USD_create_shader_input(shader, usdInputName, usdValue, usdTypeMap[usdInputName])
    
    shaderOutPort = shader.CreateOutput(connectorOut, Sdf.ValueTypeNames.Token)
    surfaceTerminal = material.CreateOutput(materialConnector+connectorOut, Sdf.ValueTypeNames.Token)
    surfaceTerminal.ConnectToSource(shaderOutPort)
    
    return shader

# Apply overrides when things are specific to how the shaderTree works (multiple options due to legacy and updates)
def applyOverrides(usdValue:str, brdfType:str, modoInputName:str, xml:ET.Element) -> str|None: 
    """
    Apply overrides to a given USD value based on the BRDF type and Modo input name.

    This function modifies the USD value according to specific rules defined for
    different BRDF types ('gtr' and 'principled') and Modo input names. It uses
    values from an XML element to determine the necessary transformations.

    Parameters:
        usdValue (str): The original USD value to be potentially overridden.
        brdfType (str): The type of BRDF ('gtr' or 'principled') to determine the
                        override logic.
        modoInputName (str): The name of the Modo input channel to apply the
                            override to.
        xml (ET.Element): An XML element containing channel data used for
                        determining overrides.

    Returns:
        str | None: The overridden USD value if changes were made, otherwise the
                    original value.
    """
    #---------------------------------------------------- Get useRefIdx value for remapping
    useRefIdx = (xml.find('channels/useRefIdx').get('value')=="1")
    specRefIdx = (xml.find('channels/specRefIdx').get('value')=="1")
    
    originalValue = usdValue
    
    match brdfType:
                        
            case "gtr":
                if modoInputName == 'disperse':
                    disperseValue = float(originalValue)
                    if disperseValue != 0: usdValue = abs(.1/float(disperseValue))
                
                if modoInputName == 'tranRough': usdValue = float(originalValue) * 2
                    
                if useRefIdx:
                    if modoInputName == 'specAmt': usdValue = "1.0"
                else:
                    if modoInputName == 'specAmt': usdValue = "1.0"
                    
                    if modoInputName == 'refIndex':
                        specAmnt = float(xml.find('channels/specAmt').get('value'))
                        usdValue =  2 / (1 - math.sqrt(specAmnt * .99999)) - 1
                        
            case "principled":
                if useRefIdx:
                    specAmnt = float(xml.find('channels/specAmt').get('value'))
                    refIdx = float(xml.find('channels/refIndex').get('value'))
                    if specRefIdx:
                        # if modoInputName == 'specAmt': usdValue = 1.0
                        # if modoInputName == 'refIndex': usdValue = 2 / (1 - math.sqrt(specAmnt * .8)) - 1
                        #if modoInputName == 'specCol': usdValue = "(1.0, 1.0, 1.0)"
                        
                        # The formula above is an approximation based on observation, nothing really serious here but that's the best I have
                        x = 2 / (1 - math.sqrt(specAmnt * .8)) - 1 # avoid division by zero
                        k = 100 # magic number, determine how fast the value reaches 1 when refIdx > 1
                        if modoInputName == 'specAmt': usdValue = 1-(1/(k*(x-1)+1))# 1-(1/((k*x)-(k-1)))
                        if modoInputName == 'refIndex': usdValue = x
                        
                    else:
                        # The formula above is an approximation based on observation, nothing really serious here but that's the best I have
                        x = refIdx
                        k = 20 # magic number, determine how fast the value reaches 1 when refIdx > 1
                        if modoInputName == 'specAmt': usdValue = 1-(1/(k*(x-1)+1)) #1-(1/((k*x)-(k-1)))
                        if modoInputName == 'refIndex': usdValue = refIdx
                             
                else:
                    specAmnt = float(xml.find('channels/specAmt').get('value'))
                    refIdx = float(xml.find('channels/refIndex').get('value'))
                    if modoInputName == 'specAmt': usdValue = 1.0
                    if modoInputName == 'refIndex': usdValue =  2 / (1 - math.sqrt(specAmnt * .99999)) - 1
                    
                    if modoInputName == 'specTint': usdValue = xml.find('channels/specTint').get('value')
                    if modoInputName == 'specCol': usdValue = "(1.0, 1.0, 1.0)"
                
                if modoInputName == 'specCol':
                    diffCol = eval(xml.find('channels/diffCol').get('value'))
                    specTint = float(xml.find('channels/specTint').get('value'))
                    #----------------------- get diff color
                    dr = diffCol[0]
                    dg = diffCol[1]
                    db = diffCol[2]
                    
                    #----------------------- Normalize and add
                    m = max(dr, dg, db)
                    sr = 1 + ((dr / m) * specTint)
                    sg = 1 + ((dg / m) * specTint)
                    sb = 1 + ((db / m) * specTint)
                    print("normalized add = (%f, %f, %f) max = %f" % (sr,sg,sb,m))
                    
                    #----------------------- Clamp below 1
                    m = max (sr, sg, sb)-1
                    fr = sr - m
                    fg = sg - m
                    fb = sb - m
                    print("n col = (%f, %f, %f) max = %f" % (fr,fg,fb,m))
                    usdValue = str((fr, fg, fb))
                    
                if modoInputName == 'sheenTint':
                    sheenTint = float(usdValue)
                    usdValue = str((sheenTint, sheenTint, sheenTint))
   
    if  usdValue != originalValue:
        if (verbose and verbose_override_value):print("🔀 Overrided value : %s from %s to %s " % (modoInputName, originalValue, usdValue))
        diag("applyOverrides", f"{xml.get('name')}", f"{modoInputName} from {originalValue} to {usdValue}")
    return usdValue

# Create USD Shader input according to modo channel scopped
def USD_create_shader_input(shaderRef:UsdShade.Shader, usdInputName, usdValue, sdfType) -> UsdShade.Input: 
    if usdInputName != None and type(usdValue) != None:
        if (verbose and verbose_set_value):print("🔁 SET %s = %s as %s" % (str(usdInputName), str(usdValue), sdfType))
        if type(usdValue) is UsdShade.Output:
            return shaderRef.CreateInput(usdInputName, sdfType).ConnectToSource(usdValue)
        else :
            #convert modo's types & values to mtlxStandard and create corresponding usd input
            match sdfType:
                case Sdf.ValueTypeNames.Float:
                    sdfValue = float(usdValue)
                        
                case Sdf.ValueTypeNames.Color3f: 
                    sdfValue = eval(usdValue)
                        
                case Sdf.ValueTypeNames.Vector3f:
                    sdfValue = eval(usdValue)
                        
                case Sdf.ValueTypeNames.String: 
                    sdfValue = str(usdValue)
                        
                case Sdf.ValueTypeNames.Int: 
                    sdfValue = int(usdValue)
            
            # print(usdValue)
            return shaderRef.CreateInput(usdInputName, sdfType).Set(sdfValue)
    
    return None

# Create and connect USD texture Shader when image found in the shader tree
def USD_create_texture_output(stage:Usd.Stage, context:ShadingContext, xml:ET.Element, outType:Sdf.ValueTypeNames) -> UsdShade.Output:
    material:UsdShade.Material = context.material
    
    #---------------------------------------------------- Store the texture path for further consolidation
    textureFilePath = xml.find('videoStill/channels/filename').get('value')
    
    if consolidateScene :
        consolidatePath = get_consolidated_path()
        file_name = os.path.basename(textureFilePath)
        consolidatedTextureFilePath = os.path.join(consolidatePath, file_name)
        
        if (textureFilePath not in textureList):
            textureList[textureFilePath] = consolidatedTextureFilePath
            
    #---------------------------------------------------- Create the texture locator
    materialPath = material.GetPath()
    texturePath:Path = materialPath.AppendPath(clean_name(xml.get('name')))

    #---------------------------------------------------- Define by projection type
    projType = xml.find('txtrLocator/channels/projType').get('value')
    
    #---------------------------------------------------- Create the texture transform
    textureTransformOutput:UsdShade.Output
    textureOutput:UsdShade.Output
    
    match projType:
        case "uv":
            #---------------------------------------------------- Create the UV texture transform node
            textureTransformOutput = USD_create_UV_texture_transform(stage, materialPath, xml)
            #---------------------------------------------------- Create the UV texture node
            textureOutput = USD_create_UV_texure(stage, materialPath, xml, outType, textureTransformOutput)
            
        case "triplanar":
            #---------------------------------------------------- Create the UV texture transform node
            textureTransformOutput:UsdShade.Output = USD_create_3D_texture_transform(stage, materialPath, xml)
            #---------------------------------------------------- Create the triplanar texture node
            textureOutput = USD_create_triplanar_texture(stage, materialPath, xml, outType, textureTransformOutput)
            
        case _:
            if(verbose and verbose_unsupported): print(f"❎ Unsupported: {projType} projection type is not yet supported (switched to default UV)")
            diag("Unsupported", "Projection_Type", f"[{projType}] in {texturePath} is not yet supported (switched to default UV)")
            #---------------------------------------------------- Create the UV texture transform node
            textureTransformOutput = USD_create_UV_texture_transform(stage, materialPath, xml)
            #---------------------------------------------------- Create the UV texture node
            textureOutput = USD_create_UV_texure(stage, materialPath, xml, outType, textureTransformOutput)
    
    #---------------------------------------------------- Create the texture adjust nodegraph
    textureAdjustNodeGraphOutput = USD_create_texture_adjust_nodegraph(stage, materialPath, xml, outType, textureOutput)
    
    return textureAdjustNodeGraphOutput

def USD_create_triplanar_texture(stage:Usd.Stage, materialPath:Path, xml:ET.Element, outType:Sdf.ValueTypeNames, textureTransformInput:UsdShade.Output) -> UsdShade.Output:
    texturePath:Path = materialPath.AppendPath(clean_name(xml.get('name')))
    textureFilePath = xml.find('videoStill/channels/filename').get('value')

    #---------------------------------------------------- Create the geometry normal node
    geometryNormal:UsdShade.Shader = UsdShade.Shader.Define(stage, str(texturePath) + "_geoNormal")
    geometryNormal.CreateIdAttr('ND_normal_vector3')
    geometryNormalOut:UsdShade.Output = geometryNormal.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
    
    #---------------------------------------------------- Create the triplanar texture node
    #                                                     This part needs more love, projection is not perfect
    blend = 1-float(xml.find('txtrLocator/channels/triplanarBlending').get('value'))
    blendApprox = math.pi / (4 * math.sin(blend * math.pi / 4))
    texture:UsdShade.Shader = UsdShade.Shader.Define(stage, str(texturePath) + "_triplanarTexture")
    texture.CreateIdAttr('ND_triplanarprojection' + getNodeTypePrefix(outType))
    texture.CreateInput("position", Sdf.ValueTypeNames.Float2).ConnectToSource(textureTransformInput)
    texture.CreateInput('filex', Sdf.ValueTypeNames.Asset).Set(textureFilePath)
    texture.CreateInput('filey', Sdf.ValueTypeNames.Asset).Set(textureFilePath)
    texture.CreateInput('filez', Sdf.ValueTypeNames.Asset).Set(textureFilePath)
    texture.CreateInput('normal', Sdf.ValueTypeNames.Vector3f).ConnectToSource(geometryNormalOut)
    texture.CreateInput('upaxis', Sdf.ValueTypeNames.Int).Set(1)
    texture.CreateInput('blend', Sdf.ValueTypeNames.Float).Set(blendApprox)
    textureOutput:UsdShade.Output = texture.CreateOutput('out', outType)
    
    return textureOutput

def USD_create_UV_texure(stage:Usd.Stage, materialPath:Path, xml:ET.Element, outType:Sdf.ValueTypeNames, textureTransformInput:UsdShade.Output) -> UsdShade.Output:
    texturePath:Path = materialPath.AppendPath(clean_name(xml.get('name')))
    textureFilePath = xml.find('videoStill/channels/filename').get('value')
    
    texture:UsdShade.Shader = UsdShade.Shader.Define(stage, str(texturePath) + "_uvTexture")
    texture.CreateIdAttr('ND_image' + getNodeTypePrefix(outType))
    texture.CreateInput("texcoord", Sdf.ValueTypeNames.Float2).ConnectToSource(textureTransformInput)
    texture.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(textureFilePath)
    texture.CreateInput('wrapS', Sdf.ValueTypeNames.String).Set(usdInputMap['uvTile'][xml.find('txtrLocator/channels/tileU').get('value')])
    texture.CreateInput('wrapT', Sdf.ValueTypeNames.String).Set(usdInputMap['uvTile'][xml.find('txtrLocator/channels/tileV').get('value')])
    textureOutput:UsdShade.Output = texture.CreateOutput('out', outType)
    
    return textureOutput
    
def USD_create_texture_adjust_nodegraph(stage:Usd.Stage, materialPath:Path, xml:ET.Element, outType:Sdf.ValueTypeNames, textureInput:UsdShade.Output) -> UsdShade.Output:
    #---------------------------------------------------- Create the texture layer
    texturePath:Path = materialPath.AppendPath(clean_name(xml.get('name')))
    invert = int(xml.find("channels/invert").get('value'))
    srcLow = float(xml.find('channels/min').get('value'))
    srcHigh = float(xml.find('channels/max').get('value'))
    brightness = float(xml.find('channels/brightness').get('value'))
    contrast = float(xml.find('channels/contrast').get('value'))
    swizzling = xml.find('channels/swizzling').get('value') == "1"
    swizzlingOut = xml.find('channels/rgba').get('value')

    #---------------------------------------------------- Create texture adjustments nodegraph
    textureAdjustNodeGraphPath = str(texturePath) + "_adjust"
    textureAdjustNodeGraph = UsdShade.NodeGraph.Define(stage, textureAdjustNodeGraphPath)
    textureAdjustNodeGraph.CreateInput('texture', outType).ConnectToSource(textureInput)
    textureAdjustNodeGraph.CreateInput('invert', Sdf.ValueTypeNames.Int).Set(invert)
    textureAdjustNodeGraph.CreateInput('outLow', outType).Set(floatToOutType(srcLow, outType))
    textureAdjustNodeGraph.CreateInput('outHigh', outType).Set(floatToOutType(srcHigh, outType))
    textureAdjustNodeGraph.CreateInput('brightness', outType).Set(floatToOutType(brightness, outType))
    textureAdjustNodeGraph.CreateInput('contrast', outType).Set(floatToOutType(contrast, outType))
    
    #---------------------------------------------------- Create image adjustments
    textureRange = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/valueRange")
    textureRange.CreateIdAttr('ND_remap' + getNodeTypePrefix(outType))
    textureRange.CreateInput("in", outType).ConnectToSource(textureAdjustNodeGraph.GetInput('texture'))
    textureRange.CreateInput('outlow', outType).ConnectToSource(textureAdjustNodeGraph.GetInput('outLow'))
    textureRange.CreateInput('outhigh', outType).ConnectToSource(textureAdjustNodeGraph.GetInput('outHigh'))
    adjustedTextureOutput:UsdShade.Output = textureRange.CreateOutput('out', outType)
    
    #---------------------------------------------------- Create contrast adjustments
    textureContrast = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/contrast")
    textureContrast.CreateIdAttr('ND_contrast' + getNodeTypePrefix(outType))
    textureContrast.CreateInput("in", outType).ConnectToSource(adjustedTextureOutput)
    textureContrast.CreateInput('amount', outType).ConnectToSource(textureAdjustNodeGraph.GetInput('contrast'))
    adjustedTextureOutput:UsdShade.Output = textureContrast.CreateOutput('out', outType)
    
    #---------------------------------------------------- Create brightness adjustments
    textureBrightness = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/brightness")
    textureBrightness.CreateIdAttr('ND_multiply' + getNodeTypePrefix(outType))
    textureBrightness.CreateInput("in1", outType).ConnectToSource(adjustedTextureOutput)
    textureBrightness.CreateInput('in2', outType).ConnectToSource(textureAdjustNodeGraph.GetInput('brightness'))
    adjustedTextureOutput:UsdShade.Output = textureBrightness.CreateOutput('out', outType)
    
    # --------------------------------------------------- Alpha mode
    alphaMode = xml.find('channels/alpha').get('value')
    if alphaMode == "only":
        extractChannelShader:UsdShade.Shader = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/channel")
        extractChannelShader.CreateIdAttr("ND_separate4_color4")
        extractChannelShader.CreateInput("in", Sdf.ValueTypeNames.Color4f).ConnectToSource(adjustedTextureOutput)
        adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outa', Sdf.ValueTypeNames.Float)
            
    # --------------------------------------------------- Invert
    if invert == 1:
        invertShader:UsdShade.Shader = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/invert")
        invertShader.CreateIdAttr('ND_invert' + getNodeTypePrefix(outType))
        invertShader.CreateInput("in", outType).ConnectToSource(adjustedTextureOutput)
        adjustedTextureOutput:UsdShade.Output = invertShader.CreateOutput('out', outType)
    
    # --------------------------------------------------- Extract swizzling channel
    if swizzling:
        extractChannelShader:UsdShade.Shader = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/channel")
        extractChannelShader.CreateIdAttr("ND_separate4_color4")
        extractChannelShader.CreateInput("in", Sdf.ValueTypeNames.Color4f).ConnectToSource(adjustedTextureOutput)
        
        #------------------------------------------------ Change output type to float
        outType = Sdf.ValueTypeNames.Float
        
        match swizzlingOut:
            case "red":
                adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outr', outType)
            case "green":
                adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outg', outType)
            case "blue":
                adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outb', outType)
            case "alpha":
                adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outa', outType)
    
    textureAdjustNodeGraph.CreateOutput('out', outType).ConnectToSource(adjustedTextureOutput)
    
    return textureAdjustNodeGraph.GetOutput('out')

def USD_create_UV_texture_transform(stage:Usd.Stage, path:Path, xml:ET.Element) -> UsdShade.Output:
    """
    Create a UV texture locator on the given USD stage.

    This function defines a texture reader and a UV coordinate transformer
    shader on the specified USD stage. It uses XML data to set the scale,
    translation, and rotation inputs for the UV transformation. The function
    returns the output of the UV transformation shader.

    Parameters:
        stage (Usd.Stage): The USD stage where the shaders will be defined.
        path (Path): The path used to name the shaders.
        xml (ET.Element): XML element containing texture locator data.

    Returns:
        UsdShade.Output: The output of the UV transformation shader.
    """
    texturePath = str(path) + "/" + xml.get('name')
    #---------------------------------------------------- Create the texture reader
    stReader = UsdShade.Shader.Define(stage, texturePath + "_streader")
    stReader.CreateIdAttr('ND_texcoord_vector2')
    stReader.CreateInput('index', Sdf.ValueTypeNames.Int).Set(0)
    stOutput:UsdShade.Output = stReader.CreateOutput('out', Sdf.ValueTypeNames.TexCoord2f)
    
    #---------------------------------------------------- Create the uv coordinates
    uvTransform = UsdShade.Shader.Define(stage, texturePath + "_transform")
    uvTransform.CreateIdAttr('UsdTransform2d')
    uvTransform.CreateInput('in', Sdf.ValueTypeNames.TexCoord2f).ConnectToSource(stOutput)
    uvTransform.CreateInput('scale', Sdf.ValueTypeNames.Float2).Set((float(xml.find('txtrLocator/channels/wrapU').get('value')),float(xml.find('txtrLocator/channels/wrapV').get('value'))))
    uvTransform.CreateInput('translation', Sdf.ValueTypeNames.Float2).Set((float(xml.find('txtrLocator/channels/m02').get('value')),float(xml.find('txtrLocator/channels/m12').get('value'))))
    uvTransform.CreateInput('rotation', Sdf.ValueTypeNames.Float).Set(360 * float(xml.find('txtrLocator/channels/uvRotation').get('value')) / (2 * math.pi))
    textureTransformOutput:UsdShade.Output = uvTransform.CreateOutput('result', Sdf.ValueTypeNames.TexCoord2f)
    
    return textureTransformOutput

def USD_create_3D_texture_transform(stage:Usd.Stage, path:Path, xml:ET.Element) -> UsdShade.Output:
    """
    Creates a 3D texture locator within a USD stage at the specified path using
    data from an XML element. This function constructs a node graph to handle
    3D textures, defining inputs for space, scale, position, rotation, and axis,
    and outputs a transformed texture locator. The function returns the final
    output of the texture transformation.

    Parameters:
        stage (Usd.Stage): The USD stage where the node graph will be defined.
        path (Path): The path where the node graph will be appended.
        xml (ET.Element): The XML element containing texture locator data.

    Returns:
        UsdShade.Output: The output of the texture transformation node graph.
    """
    # this implements a basic node structure to allow for 3d textures,
    # but the lack of documentation and the complexity of the modo coordinate system makes it weird
    # maybe someone here can help sort this out
    localMatrix = xml.find('txtrLocator/channels/localMatrix/Matrix4')
    
    textureLocatorName = clean_name(xml.find('txtrLocator').get('name'))
    nodeGraphPath = path.AppendPath(textureLocatorName)
    localMatrix = xml.find('txtrLocator/channels/localMatrix/Matrix4')
    
    texLocNodeGraph = UsdShade.NodeGraph.Define(stage, nodeGraphPath)
    texLocNodeGraph.CreateInput('space', Sdf.ValueTypeNames.String).Set("world") # can be "model" | "object" | "world"
    scale:tuple = localMatrix.get("scale")
    texLocNodeGraph.CreateInput('scale', Sdf.ValueTypeNames.Vector3f).Set((1/scale[0], 1/scale[1], 1/scale[2])) # act as frequency -> the greater, the small
    texLocNodeGraph.CreateInput('position', Sdf.ValueTypeNames.Vector3f).Set(localMatrix.get("position"))
    texLocNodeGraph.CreateInput('rotation', Sdf.ValueTypeNames.Float).Set(0.0)
    texLocNodeGraph.CreateInput('axis', Sdf.ValueTypeNames.Vector3f).Set(localMatrix.get("rotation"))
    textureTransformOutput = texLocNodeGraph.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
    
    #---------------------------------------------------- Create texture locator in nodeGraph
    locatorScale = UsdShade.Shader.Define(stage, nodeGraphPath.AppendPath("set"))
    locatorScale.CreateIdAttr('ND_position_vector3')
    locatorScale.CreateInput('space', Sdf.ValueTypeNames.String).ConnectToSource(texLocNodeGraph.GetInput('space'))
    output = locatorScale.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
    
    #---------------------------------------------------- Create texture locator scale in nodeGraph
    locatorScale = UsdShade.Shader.Define(stage, nodeGraphPath.AppendPath("scale"))
    locatorScale.CreateIdAttr('ND_multiply_vector3')
    locatorScale.CreateInput('in1', Sdf.ValueTypeNames.Vector3f).ConnectToSource(output)
    locatorScale.CreateInput('in2', Sdf.ValueTypeNames.Vector3f).ConnectToSource(texLocNodeGraph.GetInput('scale'))
    output = locatorScale.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
    
    #---------------------------------------------------- Create texture locator rotate in nodeGraph
    locatorRotation = UsdShade.Shader.Define(stage, nodeGraphPath.AppendPath("rotation"))
    locatorRotation.CreateIdAttr('ND_rotate3d_vector3')
    locatorRotation.CreateInput('in', Sdf.ValueTypeNames.Vector3f).ConnectToSource(output)
    locatorRotation.CreateInput('amount', Sdf.ValueTypeNames.Float).ConnectToSource(texLocNodeGraph.GetInput('rotation'))
    locatorRotation.CreateInput('axis', Sdf.ValueTypeNames.Vector3f).ConnectToSource(texLocNodeGraph.GetInput('axis'))
    output = locatorRotation.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
    
    #---------------------------------------------------- Create texture locator position in nodeGraph
    locatorTranslate = UsdShade.Shader.Define(stage, nodeGraphPath.AppendPath("translate"))
    locatorTranslate.CreateIdAttr('ND_add_vector3')
    locatorTranslate.CreateInput('in1', Sdf.ValueTypeNames.Vector3f).ConnectToSource(output)
    locatorTranslate.CreateInput('in2', Sdf.ValueTypeNames.Vector3f).ConnectToSource(texLocNodeGraph.GetInput('position'))
    output = locatorTranslate.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
    
    textureTransformOutput.ConnectToSource(output)
    
    return textureTransformOutput
    
# Connect a texture to the relevant shader
def USD_connect_texture_output_to_shader_input(stage:Usd.Stage, context:ShadingContext, effectName:str, output:UsdShade.Output, xml:ET.Element) -> UsdShade.Input:
    """
    Connects a texture output to a shader input based on the specified effect name.

    This function handles different effects such as "stencil", "bump", "normal", 
    and "displace" by creating and connecting appropriate shaders and inputs 
    within a USD stage. It utilizes the context and XML data to determine 
    the connections and shader configurations.

    Parameters:
        stage (Usd.Stage): The USD stage where the shader and connections are defined.
        context (ShadingContext): The shading context containing material and shader information.
        effectName (str): The name of the effect to be applied.
        output (UsdShade.Output): The output to be connected to the shader input.
        xml (ET.Element): XML element containing additional configuration data.

    Returns:
        UsdShade.Input: The connected shader input, or None if the effect is not found.
    """
    material:UsdShade.Material = context.material
    shader:UsdShade.Shader = context.shader
    advancedMaterialChannels:ET.Element = context.advancedMaterialChannels
    previewShader:UsdShade.Shader = context.previewShader
    path:Path = material.GetPath().AppendPath(clean_name(xml.get('name')))
    
    if effectName in usdInputMap['effect'].keys():
        inputName = usdInputMap['effect'][effectName]
        
        match effectName:
            case "stencil":
                #---------------------------------------------------- Create texture definition even if modo layer is disabled
                #textureOutput:UsdShade.Shader = createUsdTextureOutput(stage, context, xml, Sdf.ValueTypeNames.Color3f)
                textureOutput = output
                #---------------------------------------------------- Trick : Create invert color and connect to texture
                path:Path = material.GetPath().AppendPath(clean_name(xml.get('name')+ "_invert_color"))
                mathShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                mathShader.CreateIdAttr("ND_subtract_float")
                mathShader.CreateInput("in1", Sdf.ValueTypeNames.Color3f).Set((1.0, 1.0, 1.0))
                mathShader.CreateInput("in2", Sdf.ValueTypeNames.Color3f).ConnectToSource(textureOutput)
                mathShader.CreateOutput('out', Sdf.ValueTypeNames.Color3f)
                
                #---------------------------------------------------- Trick : Create math round to set colors to 0 or 1 for modo stencil like
                path:Path = material.GetPath().AppendPath(clean_name(xml.get('name')+ "_set_0_or_1"))
                roundShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                roundShader.CreateIdAttr("ND_round_float")
                roundShader.CreateInput("in", Sdf.ValueTypeNames.Color3f).ConnectToSource(mathShader.GetOutput('out'))
                roundShader.CreateOutput('out', Sdf.ValueTypeNames.Color3f)
                
                #---------------------------------------------------- Connect round map to shader input
                shader.CreateInput("opacity", Sdf.ValueTypeNames.Vector3f).ConnectToSource(roundShader.GetOutput('out'))
                
            case "bump":
                #---------------------------------------------------- Create texture definition even if modo layer is disabled
                #textureOutput:UsdShade.Shader = createUsdTextureOutput(stage, context, xml, Sdf.ValueTypeNames.Vector3f)
                textureOutput = output
                
                #---------------------------------------------------- Retrieve displace value in parent/channels node
                bumpHeight = float(advancedMaterialChannels.find("bumpAmp").get("value"))
                
                #---------------------------------------------------- Create Normal map and connect to tecture out
                path:Path = material.GetPath().AppendPath(clean_name(xml.get('name')+ "_bumpMap"))
                normalShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                normalShader.CreateIdAttr("ND_bump_vector3")
                normalShader.CreateInput("height", Sdf.ValueTypeNames.Vector3f).ConnectToSource(textureOutput)
                normalShader.CreateInput("scale", Sdf.ValueTypeNames.Float).Set(bumpHeight)
                normalShader.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
                
                #---------------------------------------------------- Connect normalMap to shader input
                shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
                
                #---------------------------------------------------- Connect texture to previewShader input
                if (exportGlPreviewMaterial):
                    previewShader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
            
            case "normal":
                #---------------------------------------------------- Create texture definition even if modo layer is disabled
                #textureOutput:UsdShade.Shader = createUsdTextureOutput(stage, context, xml, Sdf.ValueTypeNames.Color3f)
                textureOutput = output
                
                #---------------------------------------------------- Retrieve displace value in parent/channels node
                normalHeight = 0.0 #--------------------------------- unfortynately, this value is not given by modo
                
                #---------------------------------------------------- Create Normal map and connect to tecture out
                path:Path = material.GetPath().AppendPath(clean_name(xml.get('name')+ "_normalmap"))
                normalShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                normalShader.CreateIdAttr("ND_normalmap")
                normalShader.CreateInput("in", Sdf.ValueTypeNames.Vector3f).ConnectToSource(textureOutput)
                normalShader.CreateInput("scale", Sdf.ValueTypeNames.Float).Set(normalHeight)
                normalShader.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
                
                #---------------------------------------------------- Connect normalMap to shader input
                shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
                
                #---------------------------------------------------- Connect texture to previewShader input
                if (exportGlPreviewMaterial):
                    previewShader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
            
            case "displace":
                #---------------------------------------------------- Create texture definition even if modo layer is disabled
                #textureOutput:UsdShade.Shader = createUsdTextureOutput(stage,context, xml, Sdf.ValueTypeNames.Float)
                
                #---------------------------------------------------- Retrieve displace value in parent/channels node
                displacementHeight = float(advancedMaterialChannels.find("displace").get("value"))
                
                #---------------------------------------------------- Create Normal map and connect to tecture out
                path:Path = material.GetPath().AppendPath(clean_name(xml.get('name')+ "_displacement"))
                displacementShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                displacementShader.CreateIdAttr("ND_displacement_float")
                displacementShader.CreateInput("displacement", Sdf.ValueTypeNames.Float).ConnectToSource(output)
                displacementShader.CreateInput("scale", Sdf.ValueTypeNames.Float).Set(displacementHeight)
                output = displacementShader.CreateOutput('out', Sdf.ValueTypeNames.Float)
                
                #---------------------------------------------------- Connect normalMap to shader input
                material.CreateOutput("mtlx:displacement", Sdf.ValueTypeNames.Token).ConnectToSource(output)
            
        
        input = shader.GetInput(inputName)
        if input.Get() != None:
            return input.ConnectToSource(output)
        else:
            return USD_create_shader_input(shader, inputName, output, usdTypeMap[inputName])
    
    print("⁉️ Effect %s not found in stringMap" % effectName)
    return None

# Format any channel value to given type
def formatChannelValue(channel:modo.Channel): 
    """
    Formats the value of a modo.Channel object based on its type.

    Parameters:
        channel (modo.Channel): The channel whose value needs to be formatted.

    Returns:
        str or dict: A string representation of the channel's value for integer,
        float, and eval types. For gradient type, returns "gradient". For storage
        types, returns a dictionary with matrix details if the storage type is
        MATRIX4, or a string representation otherwise. Returns "None" for none type.
    """
    match channel.type:
        case lx.symbol.iCHANTYPE_INTEGER:
            return str(channel.get())
        
        case lx.symbol.iCHANTYPE_FLOAT:
            return str(channel.get())
        
        case lx.symbol.iCHANTYPE_GRADIENT:
            return "gradient"
        
        case lx.symbol.iCHANTYPE_STORAGE:
            match channel.storageType:
                case lx.symbol.sTYPE_MATRIX4:
                    matrix = modo.Matrix4(channel.get())
                    position = matrix.position
                    rotation = matrix.asEuler()
                    scale = matrix.scale()
                    Matrix4 = {
                        "Matrix4":
                            {
                            "position": position,
                            "rotation": (rotation[0], rotation[1], rotation[2]),
                            "scale": (matrix.scale().x, matrix.scale().y, matrix.scale().z)
                            }
                        }
                    return Matrix4
                
                case lx.symbol.sTYPE_COLOR1:
                    color = channel.get()
                    Matrix4 = {"Matrix4":
                        {
                        "position": matrix.position,
                        "rotation": matrix.asEuler(True),
                        "scale": matrix.scale()
                        }}
                    return Matrix4
            
            return str(channel.get())
        
        case lx.symbol.iCHANTYPE_EVAL:
            return "eval"
        
        case lx.symbol.iCHANTYPE_NONE:
            return "None"

# For a given modo channel name, retrieve the usd equivalent input name using a map Dict type table (stdMatChannelMap)
def getMappedChannel(chName:str, itemType:str=None, brdfType:str = None)->str:
    # print("Looking for mapping value for channel: %s for brdfType: %s" % (chName, brdfType))
    #---------------------------------------------- if cno itemType specified, return everything
    if itemType == None:
        return chName
    
    #---------------------------------------------- Ignore if stdMatChannelMap has no itemType entry
    if (itemType not in stdMatChannelMap.keys()): return None

    match itemType:
        case lx.symbol.sITYPE_ADVANCEDMATERIAL :
            #-------------------------------------- Ignore when channel map has no matching brdfType
            if (brdfType not in stdMatChannelMap[itemType].keys()): return None
            chMap = stdMatChannelMap[itemType][brdfType]
        case _:
            chMap = stdMatChannelMap[itemType]
    
    #---------------------------------------------- Ignore if Channel has no mapping
    if (len(chMap.keys()) == 0):return None
    
    #---------------------------------------------- Ignore if Channel has no mapping name
    if (str(chName).split('.')[0] not in chMap.keys()):return None
    
    #---------------------------------------------- Sey if Channel has valid mapping value
    if (chMap[str(chName).split('.')[0]] != ""): return chMap[str(chName).split('.')[0]]
    
    #---------------------------------------------- Ignore everything else
    print("Failed finding mapping for channel %s" % chName)
    return None

def floatToOutType(value:float, outType:Sdf.ValueTypeNames):
    """
    Convert a float value to a specified Sdf.ValueTypeNames type.

    Parameters:
        value (float): The float value to be converted.
        outType (Sdf.ValueTypeNames): The target type for conversion.

    Returns:
        Union[float, Tuple[float, float, float], Tuple[float, float, float, float]]:
        - Returns the original float if the target type is Float or Double.
        - Returns a tuple of three identical float values if the target type is Color3f or Vector3f.
        - Returns a tuple of three identical float values with an additional 1.0 if the target type is Color4f.
    """
    match outType:
        case Sdf.ValueTypeNames.Float | Sdf.ValueTypeNames.Double:
            return value
            
        case Sdf.ValueTypeNames.Color3f | Sdf.ValueTypeNames.Vector3f:
            return (value, value, value)
            
        case Sdf.ValueTypeNames.Color4f:
            return (value, value, value, 1.0)

def getNodeTypePrefix(outType):
    """
    Determine the prefix for a node type based on the output type.

    Parameters:
        outType (Sdf.ValueTypeName): The output type to evaluate.

    Returns:
        str: A string prefix corresponding to the node type, such as "_float", "_color3", or "_color4".
    """
    
    match outType:
        case Sdf.ValueTypeNames.Float | Sdf.ValueTypeNames.Double:
            return "_float"
            
        case Sdf.ValueTypeNames.Color3f | Sdf.ValueTypeNames.Vector3f:
            return "_color3"
            
        case Sdf.ValueTypeNames.Color4f:
            return "_color4"

def copy_and_clean_files():
    """
    Copies and cleans texture files in the consolidated path.

    This function creates a destination directory if it doesn't exist,
    lists existing files in the directory, and copies new or updated
    texture files from the `textureList` dictionary. It compares the
    modification dates of existing files to determine if they need
    updating. Unused files are moved to an 'unused' subdirectory or
    deleted if they already exist there. Verbose logging is provided
    based on the `verbose` and `verboseConsolidate` flags.
    """
    
    consolidatePath = get_consolidated_path()

    # Create destination path if not existing
    if not os.path.exists(consolidatePath):
        os.makedirs(consolidatePath)

    # Store all existing files in destination path
    existing_files = []
    for f in os.listdir(consolidatePath):
        fPath = os.path.join(consolidatePath, f)
        if os.path.isfile(fPath):
            existing_files.append(fPath)
    
    # Copy or update files from original path to consolidated path
    for filePath, newPath in textureList.items():
        
        # Check if file already exist in consolidated path
        if (newPath in existing_files):
            src_mtime = os.path.getmtime(filePath)
            dest_mtime = os.path.getmtime(newPath)
            
            # if file is ùore recent copy it
            if src_mtime > dest_mtime:
                shutil.copy2(filePath, newPath)
                if (verbose and verbose_consolidate):print(f"🖼️ Texture : [{os.path.basename(newPath)}] updated")
                diag("Consolidate", "file", f"Texture : [{os.path.basename(newPath)}] updated")

            # Remove current file from existing
            if (verbose and verbose_consolidate):print(f"🖼️ Texture : [{os.path.basename(newPath)}] removed form existing files")
            existing_files.pop(existing_files.index(newPath))
            
        else:
            shutil.copy2(filePath, newPath)
            if (verbose and verbose_consolidate):print(f"🖼️  texture : [{os.path.basename(newPath)}] copied")
            diag("Consolidate", "file", f"Texture : [{os.path.basename(newPath)}] copied")

    # If files are still present in existing files, they are not useful anymore
    if len(existing_files) > 0:
        # Create a "unused" sub folder
        unusedPath = os.path.join(consolidatePath, "unused")
        if not os.path.exists(unusedPath):
            os.makedirs(unusedPath)
            
        # Move the useless files to the unused folder
        for old_file in existing_files:
            unused_file = os.path.join(unusedPath, os.path.basename(old_file))
            # if doesn't exist in the unused folder copy it
            if not os.path.exists(unused_file):
                shutil.move(os.path.join(consolidatePath, old_file), unused_file)
                if (verbose and verbose_consolidate):print(f"🖼️ Texture : [{os.path.basename(old_file)}] moved to 'unused'")
                diag("copy_and_clean_files", "file", f"Texture : [{os.path.basename(newPath)}]  moved to 'unused'")
                
            # If the file already exist in the unused folder, just delete it
            else:
                os.remove(os.path.join(consolidatePath, old_file))
                if (verbose and verbose_consolidate):print(f"🖼️ Texture : [{os.path.basename(old_file)}] removed (already exists in 'unused')")
                diag("copy_and_clean_files", "file", f"Texture : [{os.path.basename(old_file)}] removed (already exists in 'unused')")

# Clean the shadertree layers names (remove white space and parenthesis)
def clean_name(name:str) -> str:
    originalName = name
    if (name[0] in ["0", "1", "2", "3", "4", "5", "6", "7","8", "9"]): name  = "_" + name
    name = replace_chars(name, ["(", ")"], "")
    name = replace_chars(name, ["(", ")", " ", "-", ".", ":", "#", ";", "?", ","], "_")
    
    if name != originalName:
        diag("Renaming", "Item", f"[{os.path.basename(originalName)}] renamed as [{os.path.basename(name)}]")
    return name

def remove_chars(string, chars_to_remove):
    translation_table = str.maketrans("", "", "".join(chars_to_remove))
    return string.translate(translation_table)

def replace_chars(string: str, chars_to_replace: str, replacement: str) -> str:
    pattern = "[" + re.escape("".join(chars_to_replace)) + "]"
    return re.sub(pattern, replacement, string)

def get_consolidated_path() -> str:
    scene = modo.scene.current()
    fileName = basestring(scene.filename).removesuffix(".lxo")
    suffix = fileName.split("/").pop(len(fileName.split("/"))-1)
    projectPath = basestring(fileName).removesuffix(suffix)
    return projectPath + suffix + "_textures"
