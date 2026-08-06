
# python

import os, shutil
import re, sys, math, json
import lx, modo
from typing import cast
from collections import OrderedDict
from pathlib import Path
from fnpxr import Sdf, Usd, UsdShade, UsdGeom

import lxu.service
import modo.dialogs
import modo.item
import modo.util

from .ShaderFilters import usdInputMap
from .ShaderFilters import usdTypeMap
from .ShaderFilters import channelTypeMap
from .ShaderFilters import stdMatChannelMap

from .normalize import normalize as normalize_shadertree

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
    effectUsdInputNames:dict = {} # effectName (Modo) -> usdInputName, set alongside effectsStack

class shaderConnector:
    name:str
    output:UsdShade.Output
    outType:str
    opacity:float
    modoBlendOperator:str
    usdOperator:str
    path:str

# textureList is used to store the source path of any texture used by the shaders
# in order to later consolidate the scene by copying all these textures to a consolidated folder
textureList = dict()

# Global variables for user preferences
consolidateScene = None
exportGlPreviewMaterial = None
export_json = None
export_xml = None
export_usda = None
export_usd = None
export_diagnostic = None
verbose = None
verbose_modify_tree = None
export_diagnostic = None

xml_diagnostic = None

def _DEBUG_diag(sectionName:str, diagElementName:str, diagtext:str):
    """
    Reports a diagnostic message: prints it to the console (when verbose and verbose_modify_tree are
    both on) and/or records it in the diagnostic XML tree (when export_diagnostic is on). Single entry
    point for both, so call sites don't each need their own `if verbose: print(...)` line.

    Parameters:
        sectionName (str): The name of the section to which the diagnostic element will be added.
        diagElementName (str): The name of the diagnostic element to be created.
        diagtext (str): The message.
    """
    if verbose and verbose_modify_tree:
        print(diagtext)

    if not export_diagnostic: return

    section = xml_diagnostic.find(sectionName)
    if section is None:
        section = ET.Element(sectionName)
        xml_diagnostic.append(section)

    diagElement = ET.Element(diagElementName)
    diagElement.text = diagtext

    section.append(diagElement)
        
def _initialize_preferences():
    """Initialize global variables with user preferences."""
    global consolidateScene, exportGlPreviewMaterial
    global export_json, export_xml, export_usda, export_usd, export_diagnostic
    global verbose, verbose_modify_tree

    consolidateScene = lx.eval('user.value USDExport_consolidateScene ?')
    exportGlPreviewMaterial = lx.eval('user.value USDExport_exportGlPreviewMaterial ?')
    export_json = lx.eval('user.value USDExport_export_json ?')
    export_xml = lx.eval('user.value USDExport_export_xml ?')
    export_usd = lx.eval('user.value USDExport_export_usd ?')
    export_usda = lx.eval('user.value USDExport_export_usda ?')
    export_diagnostic = lx.eval('user.value USDExport_saveDiagnostic ?')
    verbose = lx.eval('user.value USDExport_verbose ?')
    verbose_modify_tree = lx.eval('user.value USDExport_verboseModifyTree ?')
    
# Call this function at the start of your script or before using the preferences
_initialize_preferences()

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
    _DEBUG_diag("Files", "Set", f"filename = {os.path.basename(filename)}.lxo")
    _DEBUG_diag("Files", "Set", f"project path = {os.path.dirname(filename)}")

    renderer_id = scene.items(lx.symbol.sITYPE_POLYRENDER)[0].id
    renderer = scene.item(renderer_id)
    
    xml_shadertree = _XML_export_item(renderer)
    #------- Normalized copy: every advancedMaterial channel gets a usdValue (gtr/principled-overridden
    #------- where normalize_specular_ior applies, a straight copy of value otherwise), plus resolved
    #------- usdOperator/usdProjType/usdInputName attributes from the other 3 passes (see
    #------- Scripts/python_modules/normalize/). USD construction reads only this tree - the mtlx shader
    #------- via usdValue, the glPreview shader via the untouched value on the same tree.
    xml_shadertree_normalized = normalize_shadertree(xml_shadertree)

    #----------- Write files
    #----------- as Json
    json_shadertree = _JSON_export_item(renderer)
    if export_json: _JSON_write_file(filename, json_shadertree)

    #----------- as XML
    if export_xml:
        _XML_write_file(filename, xml_shadertree)
        #------- Also save the normalized XML separately, to compare against the raw one
        _XML_write_file(filename + "_normalized", xml_shadertree_normalized)

    #----------- as usda
    if export_usda or export_usd: _USD_write_file(filename, xml_shadertree_normalized)
    
    #----------- Write diadnostic file
    if export_diagnostic:
        ET.indent(xml_diagnostic, space="   ")
        xmlString = ET.tostring(xml_diagnostic, method="xml", xml_declaration=True).decode()
        fout = open(filename + "_diagnostic.xml",'w') 
        fout.write(xmlString)
        fout.close()
        del xml_diagnostic


#////////////////////////////////////// XML
   
# Write the data as XML
def _XML_write_file(fileName, xml:ET.Element):
    ET.indent(xml, space="   ")
    xmlString = ET.tostring(xml, method="xml", xml_declaration=True).decode()
    fout = open(fileName + ".xml",'w') 
    fout.write(xmlString)
    fout.close()
    
    _DEBUG_diag("Files", "Save", f"{os.path.basename(fileName)}.xml saved succesfully !")

# Recursively convert the shader tree structure to xml
def _XML_export_item(item:modo.Item):
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
    out_xml.set('name', _UTIL_replace_chars(str(item.name), ["(", ")", " "], "_"))
    out_xml.set('name', _UTIL_clean_name(str(item.name)))
    out_xml.set('id', item.id)
    out_xml.set('type', item.type)
    
    #-------------------------------------------------------
    # Store extra item dependencies based on shader tree item itemType
    # some items are linked to shader tree items (like texture locators)
    # but are not directly referenced inside the shader tree item list
    # they are connected through the itemGraph like dependencies
    #-------------------------------------------------------
    if item.type in [lx.symbol.sITYPE_IMAGEMAP, lx.symbol.sITYPE_NOISE, lx.symbol.sITYPE_CELLULAR, lx.symbol.sITYPE_FALLOFF]:
        graph = item.itemGraph(lx.symbol.sGRAPH_SHADELOC)
    
        fwdItem:modo.Item
        for fwdItem in graph.forward(item.name):
            if fwdItem.type == lx.symbol.sITYPE_VIDEOSTILL: #----- Extract image file channels as xml element
                out_xml.append(_XML_export_item(fwdItem))
                    
            elif fwdItem.type == lx.symbol.sITYPE_TEXTURELOC: #----- Extract texture locator channels as xml element
                out_xml.append(_XML_export_item(fwdItem))
    
    #------------------------------- Export channels
    if len(item.channels()) > 0:
        channels = _XML_get_channels(item)
        out_xml.append(channels)
        
    #------------------------------- Export childs
    numChild = item.childCount()
    for i in range(numChild):
        itemChild = item.childAtIndex(i)
        out_xml.append(_XML_export_item(itemChild))
        
    return out_xml

# Grab all channels of an items and write it as separate xml elements in a channels structure
def _XML_get_channels(item:modo.Item):
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
        
        channelsDict:OrderedDict = _JSON_get_channels(item)
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



#////////////////////////////////////// JSON

# Write the data as JSON
def _JSON_write_file(filename, dictionary):
    with open(filename + ".json", 'w') as fout:
        json.dump(dictionary, fout, indent=1)
        fout.flush()
        
    _DEBUG_diag("Files", "Save", f"{os.path.basename(filename)}.json saved succesfully !")

# Recursively convert the shader tree structure to a Dict struccture (for json exoport)
def _JSON_export_item(item:modo.Item):
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
        out_dict["channels"] = _JSON_get_channels(item)
        
    #------------------------------- Export childs
    for i in range(item.childCount()):
        itemChild = item.childAtIndex(i)
        out_dict[itemChild.name] = _JSON_export_item(itemChild)
        
    return out_dict

# Grab all channels of an item and write it as separate Dict
def _JSON_get_channels(item:modo.Item):
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
        d = _UTIL_format_channel(item.channel(chanName), mChan.type, mChan.evalType, mChan.storageType)
        d_channels[chanName] = d
            
    
    alphaSort = OrderedDict(sorted(d_channels.items()))
    return alphaSort



#////////////////////////////////////// USD

# Write the data as USDA
def _USD_write_file(filename:str, normalizedXml:ET.Element):
    _DEBUG_diag("Files", "Save", f"saving usd ... {filename}")

    output_files = []
    if export_usda:
        output_files.append(filename + '.usda')
    if export_usd:
        output_files.append(filename + '.usd')

    if not output_files:
        return

    stage = Usd.Stage.CreateInMemory()
    context = ShadingContext()
    context = _USD_export_shadertree(stage, "/shadertree", context, normalizedXml)

    saved_any = False
    for output_file in output_files:
        try:
            if stage.Export(output_file):
                _DEBUG_diag("Files", "Save", f"{os.path.basename(output_file)} saved succesfully !")
                saved_any = True
            else:
                _DEBUG_diag("Files", "Save", f"{os.path.basename(output_file)} NOT saved succesfully !")
        except Exception as exc:
            _DEBUG_diag("Files", "Save", f"{os.path.basename(output_file)} NOT saved succesfully ({exc})")

    if not saved_any:
        _DEBUG_diag("Files", "Save", "USD not saved")

    #----------- consolidate scene
    if consolidateScene:
        _UTIL_copy_and_clean_files()
        _DEBUG_diag("Files", "Save", f"Consolidation succesful !")

# Recursive traversing of an xml tree representation of the shader tree to build an equivalent USD tree
def _USD_export_shadertree(stage:Usd.Stage, path:str, context:ShadingContext, xml:ET.Element) -> ShadingContext:
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

    `xml` is expected to be the *normalized* tree (see normalize.normalize()): every advancedMaterial
    channel carries both its raw Modo `value` and a `usdValue` (gtr/principled-overridden where
    applicable, a straight copy of `value` otherwise - see normalize_specular_ior). Both the mtlx and the
    glPreview shader read `usdValue` - UsdPreviewSurface needs the same corrected specular/IOR values the
    mtlx BRDFs do, not the raw Modo ones - so both are safe to build from this same tree.

    Args:
        stage (Usd.Stage): The USD stage where the shader tree will be exported.
        path (str): The base path for the shader tree in the USD stage.
        context (ShadingContext): The current shading context, updated as the tree is traversed.
        xml (ET.Element): The (normalized) XML element representing the current node in the shader tree.

    Returns:
        ShadingContext: The updated shading context after processing the shader tree.
    """
    #----------------------------------------------------------- Recursively explotre the shaderTree and update material usd path
    elementName = xml.tag
    
    #TODO : find a way to manage the override system using stacking priority, blending amount and blending type (mult, add, substract etc...)
    
    if elementName == 'polyRender':
        #------------------------------------------------------- If shadertree root, explore all childs set shadertree path
        if (context.material == None):
            newpath = path
        _DEBUG_diag("USD_Create", xml.tag, f"Create SHADERTREE at {path}")
        
        UsdGeom.Scope.Define(stage, newpath)

        for child in xml.findall('*'):
            context = _USD_export_shadertree(stage, newpath, context, child)

    elif elementName == 'mask':
        #------------------------------------------------------- If mask, explore all child layers
        if xml.find("channels/enable").get('value') == "1" :
            ptag = xml.find("channels/ptag").get("value")
            name = _UTIL_clean_name(xml.get('name'))

            #---------------------------------------------------- Save so siblings/the parent mask don't inherit
            #---------------------------------------------------- this mask's material once we're done with it
            savedMaterial = context.material
            savedShader = context.shader
            savedPreviewShader = context.previewShader

            if ptag != "":
                newpath = path + "/" + _UTIL_clean_name(ptag)
                _DEBUG_diag("USD_Create", xml.tag, f"Create MASK at [{newpath}]")
                #---------------------------------------------------- Create material definition
                material = UsdShade.Material.Define(stage, newpath)
                context.material = material

            else:
                newpath = path + "/" + name
                _DEBUG_diag("USD_Create", xml.tag, f"Create SCOPE at [{newpath}]")
                #---------------------------------------------------- Create sub scope definition
                UsdGeom.Scope.Define(stage, newpath)
            
            for child in xml.findall('*'):
                if child.tag != "channels":
                    context = _USD_export_shadertree(stage, newpath, context, child)
                else:
                    pass
            
            #-------------------------------------------------------- Connect child effects together
            _USD_connect_effect_stack(stage, context, path, name)

            #-------------------------------------------------------- Reset stacks
            context.effectsStack = OrderedDict()

            #-------------------------------------------------------- Restore: this mask's material must not
            #-------------------------------------------------------- leak into siblings or the enclosing mask
            context.material = savedMaterial
            context.shader = savedShader
            context.previewShader = savedPreviewShader

    elif elementName == "imageMap":
        #------------------------------------------------------- If imageMap, set USD graph with adjustments based on still image properties and effects
        name = _UTIL_clean_name(xml.get('name'))
        material:UsdShade.Material = context.material
        path:Path = material.GetPath().AppendPath(name)
        shader:UsdShade.Shader = context.shader
        previewShader:UsdShade.Shader = context.previewShader
        
        #---------------------------------------------------- Connect texture to shader and previewShader inputs if possible
        if xml.find('channels/enable').get('value') == "1":
            effectChannel = xml.find('channels/effect')
            effectName = effectChannel.get('value')
            sdfType = usdTypeMap[effectChannel.get('usdInputName')]

            _DEBUG_diag("USD_Create", xml.tag, f"Create IMAGEMAP at [{path}] as [{effectName}]")
            
            textureOutput:UsdShade.Output = _USD_create_texture_output(stage, context, xml, sdfType)
            
            #---------------------------------------------------- Add output to the current effect stack in context
            context = _USD_add_shader_connector_to_context(xml, textureOutput, context)
    
    elif elementName == "noise":
        #------------------------------------------------------- If imageMap, set USD graph with adjustments based on still image properties and effects
        material:UsdShade.Material = context.material
        shader:UsdShade.Shader = context.shader
        
        if xml.find('channels/enable').get('value') == "1":
            effectName = xml.find('channels/effect').get('value')
            materialPath = material.GetPath()
            
            _DEBUG_diag("USD_Create", xml.tag, f"Create 3D NOISE at [{path}] as [{effectName}]")
            
            texLocatorOutput = _USD_create_3D_texture_transform(stage, materialPath, xml)
            textureOutput = _USD_create_3d_texture(stage, materialPath, xml, texLocatorOutput)
            
            #---------------------------------------------------- Connect to shader input
            _USD_connect_texture_output_to_shader_input(stage, context, effectName, textureOutput, xml)

            #---------------------------------------------------- Add output to the current effect stack in context
            context = _USD_add_shader_connector_to_context(xml, textureOutput, context)

    elif elementName == "constant":
        material:UsdShade.Material = context.material
        shader:UsdShade.Shader = context.shader
        
        if xml.find('channels/enable').get('value') == "1":
            effectChannel = xml.find('channels/effect')
            effectName = effectChannel.get('value')
            sdfType = usdTypeMap[effectChannel.get('usdInputName')]
            materialPath = material.GetPath()
            
            _DEBUG_diag("USD_Create", xml.tag, f"Create CONSTANT at [{path}] as [{effectName}]")
            
            constantOutput = _USD_create_constant(stage, materialPath, xml, sdfType)
            
            #---------------------------------------------------- Add output to the current effect stack in context
            context = _USD_add_shader_connector_to_context(xml, constantOutput, context)
        
    elif elementName == 'advancedMaterial':
        #------------------------------------------------------- If material, create shader at defined path
        # -------------------------------------------------- if has no context, then do nothing, as it's probably a shader that's outside a mask
        if context.material is None: return context
        
        material:UsdShade.Material = context.material
        _DEBUG_diag("USD_Create", xml.tag, f"Create ADVANCED MATERIAL at {material.GetPath()}")
        #---------------------------------------------------- Create material definition
        shader = _USD_create_mtlx_standard_surface_shader(stage, material, xml, False)
        context.shader = shader
        context.advancedMaterialChannels = xml.find("channels")
        #---------------------------------------------------- Create gl preview material definition
        if (exportGlPreviewMaterial):
            previewShader = _USD_create_mtlx_standard_surface_shader(stage, material, xml, True)
            context.previewShader = previewShader
    
    elif elementName == "channels":
        pass
    
    else:
        _DEBUG_diag("Unsupported", "Item_Type", f"[{elementName}] is not yet supported (ignored)")
 
    return context

# Create a connector and stack it in context
def _USD_add_shader_connector_to_context(xml:ET.Element, output:UsdShade.Output, context:ShadingContext) -> ShadingContext:
    """
    Adds a shader connector to the specified shading context based on the provided XML element.
    
    Shaders operating the same effect are tacked on top of each others.

    This function checks if an effect stack exists for the given effect in the XML element.
    If not, it creates a new effect stack. It then initializes a shaderConnector instance
    with attributes derived from the XML element and the provided output. The shader connector
    is added to the effect stack within the shading context.
    
    When all layers of a material group are processed,
    the stack is processed by _USD_connect_effect_stack() in _USD_export_shadertree().

    Args:
        xml (ET.Element): An XML element containing shader connection details.
        output (UsdShade.Output): The output to be associated with the shader connector.
        context (ShadingContext): The shading context to which the shader connector will be added.

    Returns:
        ShadingContext: The updated shading context with the new shader connector added.
    """
    
    
    material:UsdShade.Material = context.material
    name = _UTIL_clean_name(xml.get('name'))
    path:Path = material.GetPath().AppendPath(name)
    
    #----------------------------------------------------------- create effectStack if doesn't exist yet for this effect
    effectChannel = xml.find("channels/effect")
    if effectChannel != None:
        effectName = effectChannel.get("value")
        if not effectName in context.effectsStack.keys():
            context.effectsStack[effectName] = []
            context.effectUsdInputNames[effectName] = effectChannel.get("usdInputName")
        
        #----------------------------------------------------------- Set values for the shaderConnection
        blendChannel = xml.find("channels/blend")
        shaderConnection = shaderConnector()
        shaderConnection.name = xml.get("name")
        shaderConnection.path = path
        shaderConnection.output = output
        shaderConnection.outType = output.GetTypeName()
        shaderConnection.modoBlendOperator = blendChannel.get("value")
        shaderConnection.usdOperator = blendChannel.get("usdOperator")
        shaderConnection.opacity = float(xml.find("channels/opacity").get("value"))
        
        #----------------------------------------------------------- Add this connector to the stack
        context.effectsStack[effectName].append(shaderConnection)
        
        _DEBUG_diag("USD_Connect", xml.tag, f"Stacked connector: {name} as {effectName}")

    else:
        _DEBUG_diag("Unsupported", "Effect", f"[{effectName}] in {path} is not yet supported (ignored)")
        
    return context
    
# Set an operator input to a connected shader output, or to a literal value otherwise
def _USD_set_or_connect(operator:UsdShade.Shader, inputName:str, typeName, source) -> UsdShade.Input:
    input = operator.CreateInput(inputName, typeName)
    if type(source) is UsdShade.Output:
        input.ConnectToSource(source)
    else:
        input.Set(eval(source))
    return input

# Connect an effect layer to the last created output for this stack
def _USD_connect_operator(stage, connector:shaderConnector, input:UsdShade.Output) -> UsdShade.Output:
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
    modoBlendOperator:str = connector.modoBlendOperator
    usdOperator:str = connector.usdOperator
    opacity:float = connector.opacity

    output:UsdShade.Output = connector.output
    outType = connector.outType
    path = connector.path

    texturePath = str(path) #+ "/" + name

    _DEBUG_diag("USD_Connect", name, f"CONNECT {name}: {input.GetFullName()} x {opacity} -> {usdOperator} -> OUT")

    #----------------------------------------------------- If blend effect not supported
    if not usdOperator:
        _DEBUG_diag("Unsupported", "Blend_Mode", f"[{modoBlendOperator}] in {texturePath} is not yet supported (ignored)")
        return output

    #----------------------------------------------------- Set effect blend operator (shared by both paths below)
    operator:UsdShade.Shader = UsdShade.Shader.Define(stage, texturePath + "_" + usdOperator)
    operator.CreateIdAttr(usdOperator + _UTIL_get_node_type_prefix(outType))

    if modoBlendOperator in [lx.symbol.sICVAL_TEXTURELAYER_BLEND_MULTIPLY, lx.symbol.sICVAL_TEXTURELAYER_BLEND_DIVIDE]:
        operator.CreateInput('in1', output.GetTypeName()).ConnectToSource(output)
        _USD_set_or_connect(operator, 'in2', output.GetTypeName(), input)
        output = operator.CreateOutput('out', outType)

        #----------------------------------------------------- set opacity as mix
        operator:UsdShade.Shader = UsdShade.Shader.Define(stage, texturePath + "_mix")
        operator.CreateIdAttr("ND_mix" + _UTIL_get_node_type_prefix(outType))
        operator.CreateInput('fg', output.GetTypeName()).ConnectToSource(output)
        _USD_set_or_connect(operator, 'bg', output.GetTypeName(), input)
        operator.CreateInput('mix', Sdf.ValueTypeNames.Float).Set(opacity)

        #----------------------------------------------------- Expose output
        output = operator.CreateOutput('out', outType)

    else:
        #----------------------------------------------------- Set opacity as mix
        operator.CreateInput('fg', output.GetTypeName()).ConnectToSource(output)
        _USD_set_or_connect(operator, 'bg', output.GetTypeName(), input)
        operator.CreateInput('mix', Sdf.ValueTypeNames.Float).Set(opacity)

        #----------------------------------------------------- Expose output
        output = operator.CreateOutput('out', outType)

    return output

# Connect all effect stack layers together
def _USD_connect_effect_stack(stage:Usd.Stage, context:ShadingContext, path:str, name:str)->UsdShade.Output:

    output:UsdShade.Output = None

    for effectName in context.effectsStack.keys():
        # ////////////////////////////////// WEAK - Should be better too use a dedicated mapping table with default value or something
        #----------------------------------------------------- Retrieve the modo input name from effect name using usd name as pivot mapping value
        usdInputName = context.effectUsdInputNames[effectName]
        modoInputName = _UTIL_get_key_from_value(stdMatChannelMap[lx.symbol.sITYPE_ADVANCEDMATERIAL]['principled'], usdInputName)

        if context.advancedMaterialChannels.find(modoInputName) != None:
            materialInputValue = context.advancedMaterialChannels.find(modoInputName).get('value')

            cleaned_value = materialInputValue.strip()
            if cleaned_value.startswith(("(", "[")) and cleaned_value.endswith((")", "]")):
                cleaned_value = cleaned_value[1:-1]
            output = cast(UsdShade.Output, tuple(float(value.strip()) for value in cleaned_value.split(",") if value.strip()))
            output = UsdShade.Output(stage.GetPrimAtPath(path).GetAttribute(usdInputName))

        #----------------------------------------------------- Create connections
        for connectorIndex in range(0, len(context.effectsStack[effectName])):
            connector:shaderConnector = context.effectsStack[effectName][connectorIndex]

            # Create the connector nodes, connect the previous output and expose the new output
            output = _USD_connect_operator(stage, connector, output)

        #---------------------------------------------------- Connect the latest exposed output to the shader input corresponding to the current effect
        _USD_connect_texture_output_to_shader_input(stage, context, effectName, output, name)

    return output
    
# Connect a texture to the relevant shader
def _USD_connect_texture_output_to_shader_input(stage:Usd.Stage, context:ShadingContext, effectName:str, output:UsdShade.Output, name:str) -> UsdShade.Input:
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
    path:Path = material.GetPath().AppendPath(name)
    
    inputName = context.effectUsdInputNames.get(effectName)
    if inputName:
        if effectName == "stencil":
            #---------------------------------------------------- Create texture definition even if modo layer is disabled
            #textureOutput:UsdShade.Shader = _USD_create_3d_texture(stage, context, xml, Sdf.ValueTypeNames.Color3f)
            textureOutput:UsdShade.Shader = output
            outputType = Sdf.ValueTypeNames.Float
            
            #---------------------------------------------------- Trick : Create invert color and connect to texture
            path:Path = material.GetPath().AppendPath(name + "_invert_color")
            invertShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
            invertShader.CreateIdAttr('ND_invert' + str(outputType))
            invertShader.CreateInput("in", outputType).ConnectToSource(textureOutput)
            invertShader.CreateOutput('out', outputType)
            
            #---------------------------------------------------- Trick : Create math round to set colors to 0 or 1 for modo stencil like
            path:Path = material.GetPath().AppendPath(name + "_set_0_or_1")
            roundShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
            roundShader.CreateIdAttr("ND_round_float")
            roundShader.CreateInput("in", outputType).ConnectToSource(invertShader.GetOutput('out'))
            roundShader.CreateOutput('out', outputType)
            
            #---------------------------------------------------- Connect round map to shader input
            shader.CreateInput("opacity", outputType).ConnectToSource(roundShader.GetOutput('out'))
            
        elif effectName == "bump":
            #---------------------------------------------------- Create texture definition even if modo layer is disabled
            #textureOutput:UsdShade.Shader = createUsdTextureOutput(stage, context, xml, Sdf.ValueTypeNames.Vector3f)
            textureOutput = output
            
            #---------------------------------------------------- Retrieve displace value in parent/channels node
            bumpHeight = float(advancedMaterialChannels.find("bumpAmp").get("value"))
            
            #---------------------------------------------------- Create Normal map and connect to tecture out
            path:Path = material.GetPath().AppendPath(name + "_bumpMap")
            normalShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
            normalShader.CreateIdAttr("ND_bump_vector3")
            normalShader.CreateInput("height", Sdf.ValueTypeNames.Vector3f).ConnectToSource(textureOutput)
            normalShader.CreateInput("scale", Sdf.ValueTypeNames.Float).Set(bumpHeight)
            normalShader.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
            
            #---------------------------------------------------- Connect normalMap to shader input
            shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(textureOutput.GetOutput('out'))
            
            #---------------------------------------------------- Connect texture to previewShader input
            if (exportGlPreviewMaterial):
                previewShader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
        
        elif effectName == "normal":
            #---------------------------------------------------- Create texture definition even if modo layer is disabled
            textureOutput:UsdShade.Shader = output
            outputType = Sdf.ValueTypeNames.Color3f
            
            #---------------------------------------------------- Retrieve displace value in parent/channels node
            normalHeight = 1.0 #--------------------------------- unfortunately, this value is not given by modo :: Probaly Bump height is used for normal map too, but not sure, so we set it to 1.0 for now
            
            #---------------------------------------------------- Create Normal map and connect to tecture out
            path:Path = material.GetPath().AppendPath(name + "_normalmap")
            normalShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
            normalShader.CreateIdAttr("ND_normalmap_float")
            normalShader.CreateInput("in", Sdf.ValueTypeNames.Vector3f).ConnectToSource(textureOutput)
            normalShader.CreateInput("scale", Sdf.ValueTypeNames.Float).Set(normalHeight)
            normalShader.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
            
            #---------------------------------------------------- Connect normalMap to shader input
            shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
            
            #---------------------------------------------------- Connect texture to previewShader input
            if (exportGlPreviewMaterial):
                previewShader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
        
        elif effectName == "displace":
            #---------------------------------------------------- Retrieve displace value in parent/channels node
            displacementHeight = float(advancedMaterialChannels.find("displace").get("value"))
            
            #---------------------------------------------------- Create Normal map and connect to tecture out
            path:Path = material.GetPath().AppendPath(name + "_displacement")
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
            return _USD_create_shader_input(shader, inputName, output, usdTypeMap[inputName])
    
    _DEBUG_diag("Unsupported", "Effect", f"[{effectName}] is not yet supported (ignored)")
        
    return None

# Create USD shader for advanced material layer
def _USD_create_mtlx_standard_surface_shader(stage:Usd.Stage, material:UsdShade.Material, xml:ET.Element, isPreview:bool) -> UsdShade.Shader: 
    """
    Create a USD shader from an XML element and add it to a given stage and material.

    This function defines a shader on the specified USD stage using the path derived
    from the material and XML element. It configures the shader based on whether it
    is a preview or not, setting attributes and creating inputs from the XML channels.
    The shader is then connected to the material's output.

    Parameters:
        stage (Usd.Stage): The USD stage where the shader will be defined.
        material (UsdShade.Material): The material to which the shader will be connected.
        xml (ET.Element): The normalized XML element containing shader channel data - each channel
            carries a `usdValue` (gtr/principled-overridden where normalize_specular_ior applies, a
            straight copy of the raw Modo `value` otherwise). Both the mtlx shader and the glPreview
            shader read `usdValue`: UsdPreviewSurface models specular/IOR the same way the mtlx BRDFs
            do, so it needs the same corrected value, not the raw Modo one.
        isPreview (bool): Flag indicating if the shader is a preview shader.

    Returns:
        UsdShade.Shader: The created USD shader.
    """
    
    path:Path = material.GetPath().AppendPath(_UTIL_clean_name(xml.get('name')))
    
    #---------------------------------------------------- Get brdfType value for remapping
    if (isPreview):
        brdfType = 'glPreview'
        path = str(path) + "_preview"
        connectorOut = "surface"
        materialConnector = ""
        surfaceId = "UsdPreviewSurface"
        _DEBUG_diag("createUsdShader", xml.get('name'), "Create PREVIEW SHADER at : %s" % path)
    else:
        brdfType = xml.find('channels/brdfType').get('value')
        connectorOut = 'surface'
        materialConnector = "mtlx:"
        surfaceId = "ND_standard_surface_surfaceshader"
        _DEBUG_diag("createUsdShader", xml.get('name'), "Create SHADER at : %s" % path)
    
        
    shader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
    shader.CreateIdAttr(surfaceId)
    #---------------------------------------------------- Create shader properties and input values
    for channel in xml.findall('channels/*'):
        
        # Convert the channel name to its usdstandard_material equivalent input
        
        modoInputName = channel.tag
        usdValue = channel.get('usdValue')

        usdInputName = _UTIL_get_mapped_channel(modoInputName, xml.get('type'), brdfType)
        if usdInputName != None:
            input = _USD_create_shader_input(shader, usdInputName, usdValue, usdTypeMap[usdInputName])
    
    shaderOutPort = shader.CreateOutput(connectorOut, Sdf.ValueTypeNames.Token)
    surfaceTerminal = material.CreateOutput(materialConnector+connectorOut, Sdf.ValueTypeNames.Token)
    surfaceTerminal.ConnectToSource(shaderOutPort)
    
    return shader

# Create USD Shader input according to modo channel scopped
def _USD_create_shader_input(shaderRef:UsdShade.Shader, usdInputName, usdValue, sdfType) -> UsdShade.Input:
    """
    Create a USD shader input for a given shader reference.

    This function creates an input on the specified UsdShade.Shader object
    using the provided input name, value, and Sdf type. If the value is a
    UsdShade.Output, it connects the input to the source. Otherwise, it
    converts the value to the appropriate type based on the Sdf type and
    sets it on the input.

    Parameters:
        shaderRef (UsdShade.Shader): The shader reference to which the input
            will be added.
        usdInputName: The name of the input to be created.
        usdValue: The value to be set for the input.
        sdfType: The Sdf type of the input.

    Returns:
        UsdShade.Input: The created shader input, or None if the input name
        or value type is None.
    """
    if usdInputName != None and type(usdValue) != None:
        _DEBUG_diag("SetValue", usdInputName, "SET %s = %s as %s" % (str(usdInputName), str(usdValue), sdfType))
        if type(usdValue) is UsdShade.Output:
            return shaderRef.CreateInput(usdInputName, sdfType).ConnectToSource(usdValue)
        else :
            #convert modo's types & values to mtlxStandard and create corresponding usd input
            if sdfType == Sdf.ValueTypeNames.Float:
                sdfValue = float(usdValue)
                    
            elif sdfType == Sdf.ValueTypeNames.Color3f: 
                sdfValue = eval(usdValue)
                    
            elif sdfType == Sdf.ValueTypeNames.Vector3f:
                sdfValue = eval(usdValue)
                    
            elif sdfType == Sdf.ValueTypeNames.String: 
                sdfValue = str(usdValue)
                    
            elif sdfType == Sdf.ValueTypeNames.Int:
                sdfValue = int(usdValue)

            return shaderRef.CreateInput(usdInputName, sdfType).Set(sdfValue)
    
    return None

# Create an USD definition of a modo constant 
def _USD_create_constant(stage:Usd.Stage, path:Path, xml:ET.Element, outType:Sdf.ValueTypeNames) -> UsdShade.Output: 
    #---------------------------------------------------- Create texture definition even if modo layer is disabled
    constantPath:Path = path.AppendPath(_UTIL_clean_name(xml.get('name')))
    constantShader = UsdShade.Shader.Define(stage, constantPath)
    constantShader.CreateIdAttr("ND_constant" + _UTIL_get_node_type_prefix(outType))
    output:UsdShade.Output = constantShader.CreateOutput("out", outType)
    
    return output

# Create an USD definition of a modo 3D texture (noise only actually)
def _USD_create_3d_texture(stage:Usd.Stage, path:Path, xml:ET.Element, texLocatorOutput:UsdShade.Output) -> UsdShade.Output:    
    #---------------------------------------------------- Create texture definition even if modo layer is disabled
    noisePath:Path = path.AppendPath(_UTIL_clean_name(xml.get('name')))
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
    
    # ---------------------------------------------------- Fractal
    noiseShader.CreateInput("octaves", Sdf.ValueTypeNames.Int).Set(int(xml.find('channels/freqs').get('value')))
    noiseShader.CreateOutput("lacunarity", Sdf.ValueTypeNames.Float).Set(float(xml.find('channels/freqRatio').get('value')))
    noiseShader.CreateOutput("diminish", Sdf.ValueTypeNames.Float).Set(float(xml.find('channels/ampRatio').get('value')))
    
    return noiseShader.CreateOutput("out", Sdf.ValueTypeNames.Float)

# Create and connect USD texture Shader when image found in the shader tree
def _USD_create_texture_output(stage:Usd.Stage, context:ShadingContext, xml:ET.Element, outType:Sdf.ValueTypeNames) -> UsdShade.Output:
    """
    Creates a texture output for a given USD stage and shading context.

    This function generates a texture output by defining a texture locator
    based on the projection type specified in the XML data. It supports UV
    and triplanar projection types, creating the necessary texture transform
    and texture nodes accordingly. If the projection type is unsupported,
    it defaults to UV. The function also handles texture path consolidation
    and creates a texture adjustment node graph.

    Parameters:
        stage (Usd.Stage): The USD stage where the texture will be defined.
        context (ShadingContext): The shading context containing material information.
        xml (ET.Element): XML element with texture data.
        outType (Sdf.ValueTypeNames): The output type for the texture.

    Returns:
        UsdShade.Output: The output of the texture adjustment node graph.
    """
    material:UsdShade.Material = context.material
    
    #---------------------------------------------------- Store the texture path for further consolidation
    textureItem = xml.find('videoStill/channels/filename')
    if textureItem != None:
        textureFilePath = textureItem.get('value')
    else:
        textureFilePath = ""
        _DEBUG_diag("Undefined", "Image", f"Missing textire in [{material.GetPath()}]")
    
    if consolidateScene and textureFilePath!="":
        consolidatePath = _UTIL_get_consolidated_path()
        file_name = os.path.basename(textureFilePath)
        consolidatedTextureFilePath = os.path.join(consolidatePath, file_name)
        
        if (textureFilePath not in textureList):
            textureList[textureFilePath] = consolidatedTextureFilePath
    
    #------------------------------------------------------ Change outType depending on texture format
    # tex_format = xml.find('videoStill/channels/format').get('value')
    # if tex_format in ["PNG", "TGA", "EXR"]:
    #     outType = Sdf.ValueTypeNames.Color4f
    # else:
    #     outType = Sdf.ValueTypeNames.Color3f
            
    #---------------------------------------------------- Create the texture locator
    materialPath = material.GetPath()
    texturePath:Path = materialPath.AppendPath(_UTIL_clean_name(xml.get('name')))

    #---------------------------------------------------- Define by projection type
    projTypeChannel = xml.find('txtrLocator/channels/projType')
    projType = projTypeChannel.get('value')
    usdProjType = projTypeChannel.get('usdProjType')

    if usdProjType != projType:
        _DEBUG_diag("Unsupported", "Projection_Type", f"[{projType}] in {texturePath} is not yet supported (switched to default UV)")

    #---------------------------------------------------- Create the texture transform
    textureTransformOutput:UsdShade.Output
    textureOutput:UsdShade.Output

    if usdProjType == "uv":
        #---------------------------------------------------- Create the UV texture transform node
        textureTransformOutput = _USD_create_UV_texture_transform(stage, materialPath, xml)
        #---------------------------------------------------- Create the UV texture node
        textureOutput = _USD_create_UV_texture(stage, materialPath, xml, outType, textureTransformOutput)

    else: # usdProjType == "triplanar"
        #---------------------------------------------------- Create the UV texture transform node
        textureTransformOutput:UsdShade.Output = _USD_create_3D_texture_transform(stage, materialPath, xml)
        #---------------------------------------------------- Create the triplanar texture node
        textureOutput = _USD_create_triplanar_texture(stage, materialPath, xml, outType, textureTransformOutput)
    
    #---------------------------------------------------- Create the texture adjust nodegraph
    textureAdjustNodeGraphOutput = _USD_create_texture_adjust_nodegraph(stage, materialPath, xml, outType, textureOutput)
    
    return textureAdjustNodeGraphOutput

def _USD_create_triplanar_texture(stage:Usd.Stage, materialPath:Path, xml:ET.Element, outType:Sdf.ValueTypeNames, textureTransformInput:UsdShade.Output) -> UsdShade.Output:
    texturePath:Path = materialPath.AppendPath(_UTIL_clean_name(xml.get('name')))
    textureFilePath = xml.find('videoStill/channels/filename').get('value')
    
    #------------------------------------------------------ Override texture filepath with $HIP consolidated path
    if consolidateScene: textureFilePath = _UTIL_get_consolidated_relative_path(textureList[textureFilePath])

    #---------------------------------------------------- Create the geometry normal node
    geometryNormal:UsdShade.Shader = UsdShade.Shader.Define(stage, str(texturePath) + "_geoNormal")
    geometryNormal.CreateIdAttr('ND_normal_vector3')
    geometryNormalOut:UsdShade.Output = geometryNormal.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
    
    #---------------------------------------------------- Create the triplanar texture node
    #                                                     This part needs more love, projection is not perfect
    blend = 1-float(xml.find('txtrLocator/channels/triplanarBlending').get('value'))
    blendApprox = math.pi / (4 * math.sin(blend * math.pi / 4))
    texture:UsdShade.Shader = UsdShade.Shader.Define(stage, str(texturePath) + "_triplanarTexture")
    texture.CreateIdAttr('ND_triplanarprojection' + _UTIL_get_node_type_prefix(outType))
    texture.CreateInput("position", Sdf.ValueTypeNames.Float2).ConnectToSource(textureTransformInput)
    texture.CreateInput('filex', Sdf.ValueTypeNames.Asset).Set(textureFilePath)
    texture.CreateInput('filey', Sdf.ValueTypeNames.Asset).Set(textureFilePath)
    texture.CreateInput('filez', Sdf.ValueTypeNames.Asset).Set(textureFilePath)
    texture.CreateInput('normal', Sdf.ValueTypeNames.Vector3f).ConnectToSource(geometryNormalOut)
    texture.CreateInput('upaxis', Sdf.ValueTypeNames.Int).Set(1)
    texture.CreateInput('blend', Sdf.ValueTypeNames.Float).Set(blendApprox)
    textureOutput:UsdShade.Output = texture.CreateOutput('out', outType)
    
    return textureOutput

def _USD_create_UV_texture(stage:Usd.Stage, materialPath:Path, xml:ET.Element, outType:Sdf.ValueTypeNames, textureTransformInput:UsdShade.Output) -> UsdShade.Output:
    texturePath:Path = materialPath.AppendPath(_UTIL_clean_name(xml.get('name')))
    textureItem = xml.find('videoStill/channels/filename')
    
    textureFilePath = ""
    if textureItem != None: textureFilePath = textureItem.get('value')
    
    #------------------------------------------------------ Override texture filepath with $HIP consolidated path
    if consolidateScene: textureFilePath = _UTIL_get_consolidated_relative_path(textureList[textureFilePath])
    
    #---------------------------------------------------- Create the UV texture node
    texture:UsdShade.Shader = UsdShade.Shader.Define(stage, str(texturePath) + "_uvTexture")
    texture.CreateIdAttr('ND_image' + _UTIL_get_node_type_prefix(outType))
    texture.CreateInput("texcoord", Sdf.ValueTypeNames.Float2).ConnectToSource(textureTransformInput)
    texture.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(textureFilePath)
    texture.CreateInput('wrapS', Sdf.ValueTypeNames.String).Set(usdInputMap['uvTile'][xml.find('txtrLocator/channels/tileU').get('value')])
    texture.CreateInput('wrapT', Sdf.ValueTypeNames.String).Set(usdInputMap['uvTile'][xml.find('txtrLocator/channels/tileV').get('value')])
    textureOutput:UsdShade.Output = texture.CreateOutput('out', outType)
    
    return textureOutput
    
def _USD_create_texture_adjust_nodegraph(stage:Usd.Stage, materialPath:Path, xml:ET.Element, outType:Sdf.ValueTypeNames, textureInput:UsdShade.Output) -> UsdShade.Output:
    #---------------------------------------------------- Create the texture layer
    texturePath:Path = materialPath.AppendPath(_UTIL_clean_name(xml.get('name')))
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
    textureAdjustNodeGraph.CreateInput('outLow', outType).Set(eval(_UTIL_float_to_out_type(srcLow, outType)))
    textureAdjustNodeGraph.CreateInput('outHigh', outType).Set(eval(_UTIL_float_to_out_type(srcHigh, outType)))
    textureAdjustNodeGraph.CreateInput('brightness', outType).Set(eval(_UTIL_float_to_out_type(brightness, outType)))
    textureAdjustNodeGraph.CreateInput('contrast', outType).Set(eval(_UTIL_float_to_out_type(contrast, outType)))
    
    #---------------------------------------------------- Create image adjustments
    textureRange = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/valueRange")
    textureRange.CreateIdAttr('ND_remap' + _UTIL_get_node_type_prefix(outType))
    textureRange.CreateInput("in", outType).ConnectToSource(textureAdjustNodeGraph.GetInput('texture'))
    textureRange.CreateInput('outlow', outType).ConnectToSource(textureAdjustNodeGraph.GetInput('outLow'))
    textureRange.CreateInput('outhigh', outType).ConnectToSource(textureAdjustNodeGraph.GetInput('outHigh'))
    adjustedTextureOutput:UsdShade.Output = textureRange.CreateOutput('out', outType)
    
    #---------------------------------------------------- Create contrast adjustments
    textureContrast = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/contrast")
    textureContrast.CreateIdAttr('ND_contrast' + _UTIL_get_node_type_prefix(outType))
    textureContrast.CreateInput("in", outType).ConnectToSource(adjustedTextureOutput)
    textureContrast.CreateInput('amount', outType).ConnectToSource(textureAdjustNodeGraph.GetInput('contrast'))
    adjustedTextureOutput:UsdShade.Output = textureContrast.CreateOutput('out', outType)
    
    #---------------------------------------------------- Create brightness adjustments
    textureBrightness = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/brightness")
    textureBrightness.CreateIdAttr('ND_multiply' + _UTIL_get_node_type_prefix(outType))
    textureBrightness.CreateInput("in1", outType).ConnectToSource(adjustedTextureOutput)
    textureBrightness.CreateInput('in2', outType).ConnectToSource(textureAdjustNodeGraph.GetInput('brightness'))
    adjustedTextureOutput:UsdShade.Output = textureBrightness.CreateOutput('out', outType)
    
    # --------------------------------------------------- Alpha mode
    alphaMode = xml.find('channels/alpha').get('value')
    if alphaMode == "only":
        #------------------------------------------------ Change output type to float
        outType = Sdf.ValueTypeNames.Float
        extractChannelShader:UsdShade.Shader = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/channel")
        extractChannelShader.CreateIdAttr("ND_separate4_color4")
        extractChannelShader.CreateInput("in", Sdf.ValueTypeNames.Color4f).ConnectToSource(adjustedTextureOutput)
        adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outa', outType)
        
    elif alphaMode == "ignore":
        #------------------------------------------------ Change output type to color3f
        outType = Sdf.ValueTypeNames.Color3f
        
    else:
        #------------------------------------------------ Change output type to color3f
        outType = Sdf.ValueTypeNames.Color3f
            
    # --------------------------------------------------- Invert
    if invert == 1:
        invertShader:UsdShade.Shader = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/invert")
        invertShader.CreateIdAttr('ND_invert' + _UTIL_get_node_type_prefix(outType))
        invertShader.CreateInput("in", outType).ConnectToSource(adjustedTextureOutput)
        adjustedTextureOutput:UsdShade.Output = invertShader.CreateOutput('out', outType)
    
    # --------------------------------------------------- Extract swizzling channel
    if swizzling:
        extractChannelShader:UsdShade.Shader = UsdShade.Shader.Define(stage, str(textureAdjustNodeGraphPath) + "/channel")
        extractChannelShader.CreateIdAttr("ND_separate4_color4")
        extractChannelShader.CreateInput("in", Sdf.ValueTypeNames.Color4f).ConnectToSource(adjustedTextureOutput)
        
        #------------------------------------------------ Change output type to float
        outType = Sdf.ValueTypeNames.Float
        
        if swizzlingOut == "red":
            adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outr', outType)
        elif swizzlingOut == "green":
            adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outg', outType)
        elif swizzlingOut == "blue":
            adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outb', outType)
        elif swizzlingOut == "alpha":
            adjustedTextureOutput:UsdShade.Output = extractChannelShader.CreateOutput('outa', outType)
    
    textureAdjustNodeGraph.CreateOutput('out', outType).ConnectToSource(adjustedTextureOutput)
    
    return textureAdjustNodeGraph.GetOutput('out')

def _USD_create_UV_texture_transform(stage:Usd.Stage, path:Path, xml:ET.Element) -> UsdShade.Output:
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

def _USD_create_3D_texture_transform(stage:Usd.Stage, path:Path, xml:ET.Element) -> UsdShade.Output:
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
    
    textureLocatorName = _UTIL_clean_name(xml.find('txtrLocator').get('name'))
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

#////////////////////////////////////// UTIL

# Format a channel to the right type (lots of weird stuff here, personnal cooking !)
def _UTIL_format_channel(channel:modo.Channel, ctype:int, evalType:str, storageType:str):
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
        try: chan['value'] = str(channel.get())
        except AttributeError: chan['value'] = "This channel has no value!"
        except: chan['value'] = "There was an error!"

    else:
        try: chan['value'] = _UTIL_format_channel_value(channel)
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

def _UTIL_get_key_from_value(dict, value)->str:
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
    return "None"

# Format any channel value to given type
def _UTIL_format_channel_value(channel:modo.Channel): 
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
    if channel.type == lx.symbol.iCHANTYPE_INTEGER:
        return str(channel.get())
        
    elif channel.type == lx.symbol.iCHANTYPE_FLOAT:
        return str(channel.get())
        
    elif channel.type == lx.symbol.iCHANTYPE_GRADIENT:
        return "gradient"
        
    elif channel.type == lx.symbol.iCHANTYPE_STORAGE:
        if channel.storageType == lx.symbol.sTYPE_MATRIX4:
            matrix = modo.Matrix4(channel.get())
            position = matrix.position
            rotation = matrix.asEuler()
            scale = matrix.scale()
            Matrix4 = {
                "Matrix4": {
                    "position": position,
                    "rotation": (rotation[0], rotation[1], rotation[2]),
                    "scale": (matrix.scale().x, matrix.scale().y, matrix.scale().z)
                }
            }
            return Matrix4
                
        elif channel.storageType == lx.symbol.sTYPE_COLOR1:
            color = channel.get()
            Matrix4 = {"Matrix4": {
                "position": matrix.position,
                "rotation": matrix.asEuler(True),
                "scale": matrix.scale()
            }}
            return Matrix4
            
        return str(channel.get())
        
    elif channel.type == lx.symbol.iCHANTYPE_EVAL:
        return "eval"
        
    elif channel.type == lx.symbol.iCHANTYPE_NONE:
        return "None"

def _UTIL_get_mapped_channel(chName:str, itemType:str=None, brdfType:str = None)->str:
    """
    Maps a given channel name to its corresponding mapped name based on the specified item type and BRDF type.

    This function checks the provided item type and BRDF type against a predefined channel map
    to find a corresponding mapped channel name. If no item type is specified, the original
    channel name is returned. If the item type or BRDF type does not exist in the map, or if
    the channel has no mapping, the function returns None. Additionally, it logs unsupported
    channels for diagnostic purposes.

    Parameters:
        chName (str): The name of the channel to be mapped.
        itemType (str, optional): The type of item to which the channel belongs. Defaults to None.
        brdfType (str, optional): The BRDF type for advanced material channels. Defaults to None.

    Returns:
        str: The mapped channel name, or None if no mapping is found.
    """
    #---------------------------------------------- if cno itemType specified, return everything
    if itemType == None:
        return chName
    
    #---------------------------------------------- Ignore if stdMatChannelMap has no itemType entry
    if (itemType not in stdMatChannelMap.keys()): return None

    if itemType == lx.symbol.sITYPE_ADVANCEDMATERIAL:
        #-------------------------------------- Ignore when channel map has no matching brdfType
        if (brdfType not in stdMatChannelMap[itemType].keys()): return None
        chMap = stdMatChannelMap[itemType][brdfType]
    else:
        chMap = stdMatChannelMap[itemType]
    
    #---------------------------------------------- Ignore if Channel has no mapping
    if (len(chMap.keys()) == 0):return None
    
    #---------------------------------------------- Ignore if Channel has no mapping name
    if (str(chName).split('.')[0] not in chMap.keys()):return None
    
    #---------------------------------------------- Sey if Channel has valid mapping value
    if (chMap[str(chName).split('.')[0]] != ""): return chMap[str(chName).split('.')[0]]
    
    #---------------------------------------------- Ignore everything else
    _DEBUG_diag("Unsupported", "Channel", f"[{chName}] is not yet supported (ignored)")
    return None

def _UTIL_float_to_out_type(value:float, outType:Sdf.ValueTypeNames)->str:
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
    if outType in [Sdf.ValueTypeNames.Float, Sdf.ValueTypeNames.Double]:
        return f"{value}"
            
    elif outType in [Sdf.ValueTypeNames.Color3f, Sdf.ValueTypeNames.Vector3f]:
        return f"({value}, {value}, {value})"
            
    elif outType == Sdf.ValueTypeNames.Color4f:
        return f"({value}, {value}, {value}, 1.0)"

def _UTIL_get_node_type_prefix(outType:str):
    """
    Determine the prefix for a node type based on the output type.

    Parameters:
        outType (Sdf.ValueTypeName): The output type to evaluate.

    Returns:
        str: A string prefix corresponding to the node type, such as "_float", "_color3", or "_color4".
    """
    
    if outType in [Sdf.ValueTypeNames.Float, Sdf.ValueTypeNames.Double]:
        return "_float"
            
    elif outType in [Sdf.ValueTypeNames.Color3f, Sdf.ValueTypeNames.Vector3f]:
        return "_color3"
            
    elif outType == Sdf.ValueTypeNames.Color4f:
        return "_color4"

def _UTIL_copy_and_clean_files():
    """
    Copies and cleans texture files in the consolidated path.

    This function creates a destination directory if it doesn't exist,
    lists existing files in the directory, and copies new or updated
    texture files from the `textureList` dictionary. It compares the
    modification dates of existing files to determine if they need
    updating. Unused files are moved to an 'unused' subdirectory or
    deleted if they already exist there. Diagnostic logging is provided
    via _DEBUG_diag().
    """
    
    consolidatePath = _UTIL_get_consolidated_path()

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
                _DEBUG_diag("Consolidate", "file", f"Texture : [{os.path.basename(newPath)}] updated")

            # Remove current file from existing
            _DEBUG_diag("Consolidate", "file", f"Texture : [{os.path.basename(newPath)}] removed form existing files")
            existing_files.pop(existing_files.index(newPath))

        else:
            shutil.copy2(filePath, newPath)
            _DEBUG_diag("Consolidate", "file", f"Texture : [{os.path.basename(newPath)}] copied")

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
                _DEBUG_diag("copy_and_clean_files", "file", f"Texture : [{os.path.basename(old_file)}] moved to 'unused'")

            # If the file already exist in the unused folder, just delete it
            else:
                os.remove(os.path.join(consolidatePath, old_file))
                _DEBUG_diag("copy_and_clean_files", "file", f"Texture : [{os.path.basename(old_file)}] removed (already exists in 'unused')")

# Clean the shadertree layers names (remove white space and parenthesis)
def _UTIL_clean_name(name:str) -> str:
    """_summary_

    Args:
        name (str): _description_

    Returns:
        str: _description_
    """    
    originalName = name
    if (name[0] in ["0", "1", "2", "3", "4", "5", "6", "7","8", "9"]): name  = "_" + name
    name = _UTIL_replace_chars(name, ["(", ")"], "")
    name = _UTIL_replace_chars(name, ["(", ")", " ", "-", ".", ":", "#", ";", "?", ","], "_")
    
    if name != originalName:
        _DEBUG_diag("Renaming", "Item", f"[{os.path.basename(originalName)}] renamed as [{os.path.basename(name)}]")
    return name

def _UTIL_remove_chars(string, chars_to_remove):
    translation_table = str.maketrans("", "", "".join(chars_to_remove))
    return string.translate(translation_table)

def _UTIL_replace_chars(string: str, chars_to_replace: str, replacement: str) -> str:
    pattern = "[" + re.escape("".join(chars_to_replace)) + "]"
    return re.sub(pattern, replacement, string)

def _UTIL_get_consolidated_path() -> str:
    scene = modo.scene.current()
    return basestring(scene.filename).removesuffix(".lxo") + "_textures"

def _UTIL_get_consolidated_relative_path(path:str) -> str:
    scene = modo.scene.current()
    return os.path.join(".", os.path.basename(scene.filename).removesuffix(".lxo") + "_textures", os.path.basename(path))
