# python

import sys
import lx
import lxu
import lxu.meta
import lxu.object
import lxu.select
import lxu.service
import lxifc
import modo
import json
import math
from collections import OrderedDict
from typing import NamedTuple

from pathlib import Path

from pxr import Sdf, Usd, UsdShade, UsdGeom

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
    
parser = ET.XMLParser(encoding='Unicode')
    
if sys.version_info[0] == 3:
    xrange = range
    basestring = str
    long = int

# preFilterChannels option allows to prefilter channels in xmlgetChannels
# if True, only the channels that are referenced in filters will be kept
# false is mostly intended for raw export and debug, it should be a little bit slower
# and should generate bigger xml output file but it can be usefull for importing data
# in software that are not usd compliant

preFilterChannels = False

# exportGlPreviewMaterial writes Gl shaders
exportGlPreviewMaterial = False

class ShadingContext:
    material: UsdShade.Material = None
    shader: UsdShade.Shader = None
    previewShader: UsdShade.Shader = None
    path: str = ""
    parentPath: str = ""
    advancedMaterialChannels: ET.Element

filters = {}
filters [lx.symbol.sITYPE_ADVANCEDMATERIAL] = [
    "useRefIdx", # Important
    "brdfType",  #Important
    "specRefIdx",#boolean toggle refIndex/specAmount ?
    "diffAmt",
    "diffCol",
    "specAmt",
    "specCol",
    "refIndex",
    "aniso",
    "rough",
    "specFres",
    "specTint",
    "coatAmt",
    "coatRough",
    "radiance",
    "luminousAmt",
    "luminousCol",
    "metallic",
    "specCol",
    "scatterAmt",
    "disperse",
    "tranRough",
    "subsAmt",
    "subsCol",
    "subsDepth",
    "subsDist",
    "sheen",
    "sheenTint",
    "opacity",
    "disperse",
    "metallic",
    "tranAmt",
    "tranCol",
    "tranDist",
    "tranAmt",
    "tranRough",
    "normal"
    ]

filters[lx.symbol.sITYPE_MASK] = [
    "blend",
    "effect",
    "enable",
    "filter",
    "invert",
    "opacity",
    "ptag",
    "ptyp",
    "render",
    "submask"
    ]
filters[lx.symbol.sITYPE_CONSTANT] = []
filters[lx.symbol.sITYPE_IMAGEMAP] = [
    "aa",
    "aaVal",
    "alpha",
    "blend",
    "blueInv",
    "brightness",
    "clamp",
    "contrast",
    "effect",
    "enable",
    "filter",
    "gamma",
    "greenInv",
    "ignSclGrp",
    "invert",
    "max",
    "min",
    "minSpot",
    "opacity",
    "pixBlend",
    "rawTextureAlpha",
    "rawTextureColor",
    "rawTextureValue",
    "redInv",
    "render",
    "rgba",
    "sourceHigh",
    "sourceLow",
    "swizzling",
    "textureAlpha",
    "textureColor",
    "textureValue"
    ]
filters[lx.symbol.sITYPE_DEFAULTSHADER] = []
filters[lx.symbol.sITYPE_RENDEROUTPUT] = []
filters[lx.symbol.sITYPE_VIDEOSTILL] = [
    "enable",
    "blend",
    "opacity",
    "filename",
    "format",
    "udim",
    "alphaMode",
    "colorRange",
    "colorspace",
    "fps",
    "imageStack",
    "interlace",
    "playback"
    ]
filters[lx.symbol.sITYPE_TEXTURELOC] = [
    "projType",
    #------------------------------------------------------ UV Projection
    "uvMap", "useUDIM",  "uvRotation", "wrapU", "wrapV", "tileU", "tileV",
    #------------------------------------------------------ Solid, Planar, spherical, Cylindrical ...
    "world", "worldMatrix", "worldXfrm", "wposMatrix", "wrotMatrix", "wsclMatrix",
    #------------------------------------------------------ Triplanar
    "triplanarBlending", 
    
]

channelTypeMap = {
    lx.symbol.iCHANTYPE_EVAL:       "eval",
    lx.symbol.iCHANTYPE_FLOAT:      "float",
    lx.symbol.iCHANTYPE_INTEGER:    "integer",
    lx.symbol.iCHANTYPE_GRADIENT:   "gradient",
    lx.symbol.iCHANTYPE_STORAGE:    "string",
    lx.symbol.iCHANTYPE_NONE:       "none"
}

usdInputMap = {
    "uvTile":{
        "reset":"black",
        "repeat":"periodic",
        "edge":"clamp",
        "mirror":"mirror"
    },
    "effect":{
        "diffColor":"base_color",
        "rough":"specular_roughness",
        "normal":"in",
        "tranAmount":"transmission",
        "lumiAmount":"emission",
        "lumiColor":"emission_color",
        "specColor":"specular_color",
        "metallic":"metalness",
        "rough":"specular_roughness",
        "displace":"displacement"
    },
    "effect_gl":{
        "diffColor":"diffuseColor",
        "lumiColor":"emissiveColor",
        "specColor":"specularColor",
        "metallic":"metallic",
        "lumiAmount":"emissive",
        "rough":"roughness",
        "normal":"normal",
        "displace":"displacement"
    }
}

usdTypeMap = {
    # ----------------------------------------- mtlx standard
    "base":Sdf.ValueTypeNames.Float,
    "base_color":Sdf.ValueTypeNames.Color3f,
    "opacity":Sdf.ValueTypeNames.Float,
    "metalness":Sdf.ValueTypeNames.Float,
    "diffuse_roughness":Sdf.ValueTypeNames.Float,
    "specular":Sdf.ValueTypeNames.Float,
    "specular_color":Sdf.ValueTypeNames.Color3f,
    "specular_IOR":Sdf.ValueTypeNames.Float,
    "specular_anisotropy":Sdf.ValueTypeNames.Float,
    "specular_roughness":Sdf.ValueTypeNames.Float,
    "sheen":Sdf.ValueTypeNames.Float,
    "sheen_color":Sdf.ValueTypeNames.Color3f,
    "coat":Sdf.ValueTypeNames.Float,
    "coat_roughness":Sdf.ValueTypeNames.Float,
    "emission":Sdf.ValueTypeNames.Float,
    "emission_color":Sdf.ValueTypeNames.Color3f,
    "transmission":Sdf.ValueTypeNames.Float,
    "transmission_scatter":Sdf.ValueTypeNames.Float,
    "transmission_dispersion":Sdf.ValueTypeNames.Float,
    "transmission_extra_roughness":Sdf.ValueTypeNames.Float,
    "transmission_color":Sdf.ValueTypeNames.Color3f,
    "transmission_depth":Sdf.ValueTypeNames.Float,
    "transmission_roughness":Sdf.ValueTypeNames.Float,
    "subsurface":Sdf.ValueTypeNames.Float,
    "subsurface_color":Sdf.ValueTypeNames.Color3f,
    "subsurface_radius":Sdf.ValueTypeNames.Float,
    "subsurface_scale":Sdf.ValueTypeNames.Float,
    "subsurface_anisotropy":Sdf.ValueTypeNames.Float,
    "thin_film_thickness":Sdf.ValueTypeNames.Float,
    "thin_film_IOR":Sdf.ValueTypeNames.Float,
    "thin_walled":Sdf.ValueTypeNames.Int,
    "normal":Sdf.ValueTypeNames.Vector3f,
    "in":Sdf.ValueTypeNames.Vector3f,
    "displacement":Sdf.ValueTypeNames.Color3f,
    # ----------------------------------------- glPreview
    "diffuseColor":Sdf.ValueTypeNames.Color3f,
    "emissive":Sdf.ValueTypeNames.Float,
    "emissiveColor":Sdf.ValueTypeNames.Color3f,
    "specularColor":Sdf.ValueTypeNames.Color3f,
    "metallic":Sdf.ValueTypeNames.Float,
    "roughness":Sdf.ValueTypeNames.Float,
    "clearcoat":Sdf.ValueTypeNames.Float,
    "clearcoatRoughness":Sdf.ValueTypeNames.Float,
    "ior":Sdf.ValueTypeNames.Float,
    "occlusion":Sdf.ValueTypeNames.Float,
}

stdMatChannelMap = {}
stdMatChannelMap [lx.symbol.sITYPE_ADVANCEDMATERIAL] = {
    "glPreview": { #----------------------------------- Mapping used for Principled shading mode
        #"useRefIdx":   "useSpecularWorkflow", # boolean toggle refIndex/specAmount ?
        "specCol":      "specularColor",
        "specTint":     "metallic",
        
        "diffCol":      "diffuseColor",
        "luminousAmt":  "emissive",
        "luminousCol":  "emissiveColor",
        "specAmt":      "specular", # (if useRefIdx = 0: specAmt)
        "rough":        "roughness",
        "refIndex":     "ior", # (if useRefIdx = 1 & specRefIdx = 1):refIndex or (if useRefIdx = 1 & specRefIdx = 0):1+specAmt
        "coatAmt":      "clearcoat",
        "coatRough":    "clearcoatRoughness",
        "opacity":      "opacity",
        "stencil":      "opacityThreshold",
        
        "normal":         "normal",
        "disp":         "displacement",
        "occ":          "occlusion"
        },

    "principled": { #----------------------------------- Mapping used for Principled shading mode
        "specRefIdx":   "", # boolean toggle refIndex/specAmount ?
        
        # =============================================== BASE
        "diffAmt":      "base",
        "diffCol":      "base_color",
        "opacity":      "opacity",
        "metallic":     "metalness",
        
        # =============================================== SPECULAR REFLECTIONS
        "specAmt":      "specular", # (if useRefIdx = 0: specAmt)
        "specCol":      "specular_color",
        "refIndex":     "specular_IOR", # (if useRefIdx = 1 & specRefIdx = 1):refIndex or (if useRefIdx = 1 & specRefIdx = 0):1+specAmt
        "aniso":        "specular_anisotropy",
        "rough":        "specular_roughness",
        "specFres":     "sheen",
        #"sheenTint":    "sheen_color", # sheenTint is a float in modo, but sheen_color is a color in usd ?
        
        # =============================================== COAT
        "coatAmt":      "coat",
        "coatRough":    "coat_roughness",
        
        # =============================================== EMISSION
        "luminousAmt":  "emission",
        "luminousCol":  "emission_color",
        
        # =============================================== TRANSMISSION
        "tranAmt":      "transmission",
        "scatterAmt":   "transmission_scatter",
        "disperse":     "transmission_dispersion",
        "tranRough":    "transmission_extra_roughness",
        "tranCol":      "transmission_color",
        "tranDist":     "transmission_depth",
        "tranRough":    "transmission_roughness",
        "stencil":      "opacity",
        
        # =============================================== SSS
        "subsAmt":      "subsurface",
        "subsCol":      "subsurface_color",
        "subsDepth":    "subsurface_radius",
        "subsDist":     "subsurface_scale",
        # # =============================================== surface
        "normal":       "normal",
        "disp":         "displacement"
        },
    
    "gtr": { #----------------------------------- Mapping used for PBR shading mode
        "opacity":      "opacity",
        # =============================================== BASE
        "diffAmt":      "base",
        "diffCol":      "base_color",
        #"diffRough":    "diffuse_roughness", (diffRough is not available in modo pbr, only in modo energy conserving)
        #"metallic":     "metalness", (metallic is not supported in Modo PBR but is in mtlxStandardSurface !!)
        # =============================================== SPECULAR REFLECTIONS
        "specAmt":      "specular",
        "specCol":      "specular_color",
        "rough":        "specular_roughness",
        "refIndex":     "specular_IOR",
        "aniso":        "specular_anisotropy",
        #"aniso":        "specular_rotation", (specular rotation only exist in modo pbr through uv map ?)
        #"specFres":     "", (Fresnel does not have equivalent in mtlx standard )
        #"specTint":     "", (specTint is not available in modo pbr)
        
        # =============================================== COAT
        "coatAmt":      "coat",
        "coatRough":    "coat_roughness",
        
        # # =============================================== TRANSMISSION
        "tranAmt":      "transmission",
        "tranCol":      "transmission_color",
        "tranDist":     "transmission_depth",
        "scatterAmt":   "transmission_scatter",
        "disperse":     "transmission_dispersion",
        "tranRough":    "transmission_extra_roughness",
        "stencil":      "opacity",
        
        # # =============================================== SHEEN
        #"specFres":     "sheen", # not sure about that but it looks like same effect
        
        # # =============================================== EMISSION
        "radiance":     "emission",
        "luminousCol":  "emission_color",
        
        # # =============================================== SSS
        "subsAmt":      "subsurface",
        "subsCol":      "subsurface_color",
        "subsDepth":    "subsurface_radius",
        "subsDist":     "subsurface_scale",
        "specFres":     "sheen",
        
        # # =============================================== surface
        "normal":       "normal",
        "disp":         "displacement",
        }
    }

stdMatChannelMap[lx.symbol.sITYPE_MASK] = {
    "blend":        "",
    "effect":       "",
    "enable":       "",
    "filter":       "",
    "invert":       "",
    "opacity":      "",
    "ptag":         "",
    "ptyp":         "",
    "render":       "",
    "submask":      ""
    }
stdMatChannelMap[lx.symbol.sITYPE_CONSTANT] = {}
stdMatChannelMap[lx.symbol.sITYPE_DEFAULTSHADER] = {}
stdMatChannelMap[lx.symbol.sITYPE_RENDEROUTPUT] = {}
stdMatChannelMap[lx.symbol.sITYPE_TEXTURELOC] = {
    "uvMap":        "",
    "useUDIM":      "",
    "uvRotation":   "",
    "wrapU":        "",
    "wrapV":        "",
    "tileU":        "Wraps",
    "tileV":        "Wrapt"
}

# Command hook
def export_basic_execute(Cmd_obj, msg):
    
    scene = modo.scene.current()

    rendererId = scene.items(lx.symbol.sITYPE_POLYRENDER)[0].id
    renderer = scene.item(rendererId)
    
    jsonShaderTree = exportItem(renderer)
    
    xmlShaderTree = xmlExportItem(renderer)

    #----------- Write files
    fileName = basestring(scene.filename).removesuffix(".lxo")
    
    #----------- as Json
    writeJson(fileName, jsonShaderTree)

    #----------- as XML
    writeXml(fileName, xmlShaderTree)
    
    #----------- as usda
    writeUsda(fileName, xmlShaderTree)
    
    #----------- transform and write xml
    # to do ....

# Write the data as XML
def writeXml(fileName, xml:ET.Element):
    ET.indent(xml, space="   ")
    xmlString = ET.tostring(xml, method="xml", xml_declaration=True).decode()
    fout = open(fileName + ".xml",'w') 
    fout.write(xmlString)
    fout.close()

# Write the data as USDA
def writeUsda(filename:str, xml:ET.Element):
    
    print("saving usd ...")
    stage = Usd.Stage.CreateNew(filename + '.usda')
    context = ShadingContext()
    context.path = "/shadertree"
    context.parentPath = "/"
    usdExportShaderTree(stage, context, xml)
    stage.GetRootLayer().Save()
    print("... usd saved")

# Write the data as JSON
def writeJson(filename, dictionary):
    with open(filename + ".json", 'w') as fout:
        json.dump(dictionary, fout, indent=1)
        fout.flush()

# Recursively convert the shader tree structure to xml
def xmlExportItem(item:modo.Item):
    out_xml = ET.Element(item.type)
    out_xml.set('name',str(item.name).replace(" ", "_").replace("(", "").replace(")", ""))
    out_xml.set('id', item.id)
    out_xml.set('type', item.type)
    
    scene = modo.scene.current()
    
    #-------------------------------------------------------
    # Store extra item dependencies based on shader tree item itemType
    # some items are linked to shader tree items (like texture locators)
    # but are not directly referenced inside the shader tree item list
    # they are connected through the itemGraph like dependencies
    #-------------------------------------------------------
    match item.type:
        case lx.symbol.sITYPE_IMAGEMAP:
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
def exportItem(item:modo.Item):
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
        out_dict[itemChild.name] = exportItem(itemChild)
        
    return out_dict

# Grab all channels of an item and write it as separate Dict
def getChannels(item:modo.Item):
    d_channels = OrderedDict()

    mChan:modo.Channel
    for mChan in item.channels():
        chanName = str(mChan.name).split(".")[0] # Important ! if not using the first part of the name, channelTriple are treated as 3 channels
        d = formatChannel(item.channel(chanName), mChan.type, mChan.evalType, mChan.storageType)
        if preFilterChannels:
            if (item.type in filters.keys()) and (len(filters[item.type])>0):
                d_channels[chanName] = d
        else:
            d_channels[chanName] = d
            
    
    alphaSort = OrderedDict(sorted(d_channels.items()))
    return alphaSort

# Format a channel to the right type (lots of weird stuff here, personnal cooking !)
def formatChannel(channel:modo.Channel, ctype:int, evalType:str, storageType:str):

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

# Clean the shadertree layers names (remove white space and parenthesis)
def cleanName(name:str) -> str:
    #print(name)
    return name.replace(" ", "_").replace("(", "").replace(")", "")

# Recursive shader tree parsing
def usdExportShaderTree(stage:Usd.Stage, context:ShadingContext, xml:ET.Element) -> ShadingContext:
    #----------------------------------------------------------- Recursively explotre the shaderTree and update material usd path
    elementName = xml.tag
    
    #TODO : find a way to manege the override system using stacking priority, blending amount and blending type (mult, add, substract etc...)
    
    match elementName:
        #------------------------------------------------------- If shadertree root, explore all childs set shadertree path
        case 'polyRender':
            if (context.material == None):
                path = "/shadertree"
            else:
                path = "/"
            print("create SHADERTREE at %s" % (path))
            
            UsdGeom.Scope.Define(stage, path)
            
            for child in xml.findall('*'):
                context = usdExportShaderTree(stage, context, child)

        #------------------------------------------------------- If mask, explore all child layers
        case 'mask':
            path = "/shadertree/" +  cleanName(xml.get('name'))
            
            print("create MASK at %s" % (path))
            #---------------------------------------------------- Create material definition
            material = UsdShade.Material.Define(stage, path)
            context.material = material
            
            for child in xml.findall('*'):
                if child.tag != "channels":
                    context = usdExportShaderTree(stage, context, child)    
                else:
                    pass
                    
        #------------------------------------------------------- If imageMap, set USD graph with adjustments based on still image properties and effects
        case "imageMap":
            material:UsdShade.Material = context.material
            shader:UsdShade.Shader = context.shader
            advancedMaterialChannels:ET.Element = context.advancedMaterialChannels
            previewShader:UsdShade.Shader = context.previewShader
            
            #path:Path = material.GetPath().AppendPath(cleanName(xml.find('videoStill').get('name')))
            path:Path = material.GetPath().AppendPath(cleanName(xml.get('name')))
            
            print("create IMAGEMAP at %s" % (path))
            
            #---------------------------------------------------- Create texture definition even if modo layer is disabled
            texture:UsdShade.Shader = createUsdTexture(stage, material, path, xml)
    
            #---------------------------------------------------- Create image adjustments
            textureRange = UsdShade.Shader.Define(stage, str(path) + "_valueRange")
            textureRange.CreateIdAttr('ND_remap_color3')
            textureRange.CreateInput("in", Sdf.ValueTypeNames.Color3f).ConnectToSource(texture.GetOutput('rgb'))
            srcLow = float(xml.find('channels/min').get('value'))
            srcHigh = float(xml.find('channels/max').get('value'))
            textureRange.CreateInput('outlow', Sdf.ValueTypeNames.Color3f).Set((srcLow, srcLow, srcLow))
            textureRange.CreateInput('outhigh', Sdf.ValueTypeNames.Color3f).Set((srcHigh, srcHigh, srcHigh))
            textureRange.CreateOutput('out', Sdf.ValueTypeNames.Color3f)
            
            textureFinal:UsdShade.Shader = textureRange
            
            # def Shader "mtlxremap1"
            #     {
            #         uniform token info:id = "ND_remap_color3"
            #         color3f inputs:in.connect = </shadertree/Body_Material/DisplacementMap.outputs:rgb>
            #         color3f inputs:outhigh = (0.5, 0.5, 0.5)
            #         color3f inputs:outlow = (-1, -1, -1)
            #         color3f outputs:out
            #     }
            
            #---------------------------------------------------- Connect texture to shader and previewShader inputs if possible
            if xml.find('channels/enable').get('value') == "1":
                modoInputName = xml.find('channels/effect').get('value')
                
                match modoInputName:
                    case "stencil":
                        #---------------------------------------------------- Trick : Create invert color and connect to texture
                        path:Path = material.GetPath().AppendPath(cleanName(xml.get('name')+ "_invert_color"))
                        mathShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                        mathShader.CreateIdAttr("ND_subtract_float")
                        mathShader.CreateInput("in1", Sdf.ValueTypeNames.Color3f).Set((1.0, 1.0, 1.0))
                        mathShader.CreateInput("in2", Sdf.ValueTypeNames.Color3f).ConnectToSource(textureFinal.GetOutput('out'))
                        mathShader.CreateOutput('out', Sdf.ValueTypeNames.Color3f)
                        
                        #---------------------------------------------------- Trick : Create math round to set colors to 0 or 1 for modo stencil like
                        path:Path = material.GetPath().AppendPath(cleanName(xml.get('name')+ "_set_0_or_1"))
                        roundShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                        roundShader.CreateIdAttr("ND_round_float")
                        roundShader.CreateInput("in", Sdf.ValueTypeNames.Color3f).ConnectToSource(mathShader.GetOutput('out'))
                        roundShader.CreateOutput('out', Sdf.ValueTypeNames.Color3f)
                        
                        #---------------------------------------------------- Connect round map to shader input
                        shader.CreateInput("opacity", Sdf.ValueTypeNames.Vector3f).ConnectToSource(roundShader.GetOutput('out'))
                        
                    case "tranAmount":
                        #---------------------------------------------------- Connect imageMap alpha to transission
                        shader.CreateInput("transmission", Sdf.ValueTypeNames.Float).ConnectToSource(texture.GetOutput('a'))
                        
                    case "bump":
                        #---------------------------------------------------- Retrieve displace value in parent/channels node
                        bumpHeight = float(advancedMaterialChannels.find("bumpAmp").get("value"))
                        
                        #---------------------------------------------------- Create Normal map and connect to tecture out
                        path:Path = material.GetPath().AppendPath(cleanName(xml.get('name')+ "_bumpMap"))
                        normalShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                        normalShader.CreateIdAttr("ND_bump_vector3")
                        normalShader.CreateInput("height", Sdf.ValueTypeNames.Vector3f).ConnectToSource(textureFinal.GetOutput('out'))
                        normalShader.CreateInput("scale", Sdf.ValueTypeNames.Float).Set(bumpHeight)
                        normalShader.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
                        
                        #---------------------------------------------------- Connect normalMap to shader input
                        shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
                        
                        #---------------------------------------------------- Connect texture to previewShader input
                        if (exportGlPreviewMaterial):
                            previewShader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
                    
                    case "normal":
                        #---------------------------------------------------- Retrieve displace value in parent/channels node
                        normalHeight = 1.0 #--------------------------------- unfortynately, this value is not given by modo
                        
                        #---------------------------------------------------- Create Normal map and connect to tecture out
                        path:Path = material.GetPath().AppendPath(cleanName(xml.get('name')+ "_normalmap"))
                        normalShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                        normalShader.CreateIdAttr("ND_normalmap")
                        normalShader.CreateInput("in", Sdf.ValueTypeNames.Vector3f).ConnectToSource(textureFinal.GetOutput('out'))
                        normalShader.CreateInput("scale", Sdf.ValueTypeNames.Float).Set(normalHeight)
                        normalShader.CreateOutput('out', Sdf.ValueTypeNames.Vector3f)
                        
                        #---------------------------------------------------- Connect normalMap to shader input
                        shader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
                        
                        #---------------------------------------------------- Connect texture to previewShader input
                        if (exportGlPreviewMaterial):
                            previewShader.CreateInput("normal", Sdf.ValueTypeNames.Vector3f).ConnectToSource(normalShader.GetOutput('out'))
                    
                    case "displace":
                        #---------------------------------------------------- Retrieve displace value in parent/channels node
                        displacementHeight = float(advancedMaterialChannels.find("displace").get("value"))
                        
                        #---------------------------------------------------- Create Normal map and connect to tecture out
                        path:Path = material.GetPath().AppendPath(cleanName(xml.get('name')+ "_displacement"))
                        displacementShader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
                        displacementShader.CreateIdAttr("ND_displacement_float")
                        displacementShader.CreateInput("displacement", Sdf.ValueTypeNames.Float).ConnectToSource(textureFinal.GetOutput('out'))
                        displacementShader.CreateInput("scale", Sdf.ValueTypeNames.Float).Set(displacementHeight)
                        displacementShader.CreateOutput('out', Sdf.ValueTypeNames.Float)
                        
                        #---------------------------------------------------- Connect normalMap to shader input
                        #surfaceTerminal.ConnectToSource(displacementShader.GetOutput('out'))
                        material.CreateOutput("mtlx:displacement", Sdf.ValueTypeNames.Token).ConnectToSource(displacementShader.GetOutput('out'))
                        
                    case _:
                        #---------------------------------------------------- Connect texture to shader input
                        connectTextureToShaderInput(textureFinal, shader, modoInputName)
                        
                        #---------------------------------------------------- Connect texture to previewShader input
                        if (exportGlPreviewMaterial):
                            connectTextureToShaderInput(textureFinal, previewShader, modoInputName, usdStringMap['effect_gl'])
            
        #------------------------------------------------------- If material, create shader at defined path
        case 'advancedMaterial':
            # -------------------------------------------------- if has no context, then do nothing, as it's probably a shader that's outside a mask
            if context.material is None: return context
            
            material:UsdShade.Material = context.material
            print("create ADVANCED MATERIAL at %s" % (material.GetPath()))
            #---------------------------------------------------- Create material definition
            shader = createUsdShader(stage, material, xml, False)
            context.shader = shader
            context.advancedMaterialChannels = xml.find("channels")
            #---------------------------------------------------- Create gl preview material definition
            if (exportGlPreviewMaterial):
                previewShader = createUsdShader(stage, material, xml, True)
                context.previewShader = previewShader
            
        
    return context

# Create USD shader for advanced material layer
def createUsdShader(stage:Usd.Stage, material:UsdShade.Material, xml:ET.Element, isPreview:bool) -> UsdShade.Shader: 
    
    path:Path = material.GetPath().AppendPath(cleanName(xml.get('name')))
    
    #---------------------------------------------------- Get brdfType value for remapping
    if (isPreview):
        brdfType = 'glPreview'
        path = str(path) + "_preview"
        connectorOut = "surface"
        materialConnector = ""
        surfaceId = "UsdPreviewSurface"
        print ("create PREVIEW SHADER at : %s" % path)
    else:
        brdfType = xml.find('channels/brdfType').get('value')
        connectorOut = 'surface'
        materialConnector = "mtlx:"
        surfaceId = "ND_standard_surface_surfaceshader"
        print ("create SHADER at : %s" % path)
    
        
    shader:UsdShade.Shader = UsdShade.Shader.Define(stage, path)
    shader.CreateIdAttr(surfaceId)
    #---------------------------------------------------- Create shader properties and input values
    for channel in xml.findall('channels/*'):
        
        # Convert the channel name to its usdstandard_material equivalent input
        
        modoInputName = channel.tag
        usdValue = channel.get('value')
        
        usdInputName = getMappedChannel(modoInputName, xml.get('type'), brdfType)
        # print(usdInputName)
        if not isPreview: usdValue = applyOverrides(usdValue, brdfType, modoInputName, xml)
        if usdInputName != None:input = createUsdShaderInput(shader, usdInputName, usdValue, usdTypeMap[usdInputName])
    
    shaderOutPort = shader.CreateOutput(connectorOut, Sdf.ValueTypeNames.Token)
    surfaceTerminal = material.CreateOutput(materialConnector+connectorOut, Sdf.ValueTypeNames.Token)
    surfaceTerminal.ConnectToSource(shaderOutPort)
    
    return shader

# Apply overrides when things are specific to how the shaderTree works (multiple options due to legacy and updates)
def applyOverrides(usdValue:str, brdfType:str, modoInputName:str, xml:ET.Element) -> str|None: 
    
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
                        usdValue =  2 / (1 - math.sqrt(specAmnt)) - 1
                    pass
                        
            case "principled":
                if useRefIdx:
                    if specRefIdx:
                        if modoInputName == 'specAmt': usdValue = str(1.0)# - float(xml.find('channels/specAmt').get('value')))
                        if modoInputName == 'refIndex': usdValue = str(1.0 + float(xml.find('channels/specAmt').get('value')))
                        if modoInputName == 'specCol': usdValue = "(1.0, 1.0, 1.0)"
                    else:
                        if modoInputName == 'specAmt': usdValue = "1.0"
                        if modoInputName == 'refIndex': usdValue = xml.find('channels/refIndex').get('value')
                else:
                    if modoInputName == 'specAmt': usdValue = xml.find('channels/specAmt').get('value')
                    if modoInputName == 'specTint': usdValue = xml.find('channels/specTint').get('value')
                    if modoInputName == 'refIndex': usdValue = float(xml.find('channels/specAmt').get('value'))
                    if modoInputName == 'specCol': usdValue = "(1.0, 1.0, 1.0)"
                    #if modoInputName == 'refIndex': usdValue = 1.0 + float(xml.find('channels/refIndex').get('value'))
   
    if  usdValue != originalValue:
        print("Overrided value : %s from %s to %s " % (modoInputName, originalValue, usdValue))
        
    return usdValue

# Create USD Shader input according to modo channel scopped
def createUsdShaderInput(shaderRef:UsdShade.Shader, usdInputName, usdValue, sdfType) -> UsdShade.Shader: 
            
    if type(usdValue) is UsdShade.Output:
        print("CONNECT %s = %s as %s" % (str(usdInputName), str(usdValue), str(sdfType)))
        return shaderRef.CreateInput(usdInputName, sdfType).ConnectToSource(usdValue)
        
    elif usdInputName != None and type(usdValue) != None:
        #print("SET %s = %s as %s" % (str(usdInputName), str(usdValue), str(evaltype)))
        
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
def createUsdTexture(stage:Usd.Stage, material:UsdShade.Material, path:Path, xml:ET.Element): 

    #---------------------------------------------------- Create the texture locator
    stReader = UsdShade.Shader.Define(stage, str(path) + "_texture_reader")
    stReader.CreateIdAttr('ND_texcoord_vector2')
    stReader.CreateInput('index', Sdf.ValueTypeNames.Int).Set(0)
    stReader.CreateOutput('out', Sdf.ValueTypeNames.TexCoord2f)
    
    #---------------------------------------------------- Create the texture transform
    uvTransform = UsdShade.Shader.Define(stage, str(path) + "_texture_transform")
    uvTransform.CreateIdAttr('UsdTransform2d')
    uvTransform.CreateInput('in', Sdf.ValueTypeNames.TexCoord2f).ConnectToSource(stReader.ConnectableAPI(), 'out')
    uvTransform.CreateInput('scale', Sdf.ValueTypeNames.Float2).Set((float(xml.find('txtrLocator/channels/wrapU').get('value')),float(xml.find('txtrLocator/channels/wrapV').get('value'))))
    uvTransform.CreateInput('translation', Sdf.ValueTypeNames.Float2).Set((float(xml.find('txtrLocator/channels/m02').get('value')),float(xml.find('txtrLocator/channels/m12').get('value'))))
    uvTransform.CreateInput('rotation', Sdf.ValueTypeNames.Float).Set(360 * float(xml.find('txtrLocator/channels/uvRotation').get('value')) / (2 * math.pi))
    uvTransform.CreateOutput('result', Sdf.ValueTypeNames.TexCoord2f)
    
    #---------------------------------------------------- Create the texture
    texture:UsdShade.Shader = UsdShade.Shader.Define(stage, str(path) + "_imageFile")
    texture.CreateIdAttr('ND_UsdUVTexture_23')
    texture.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(xml.find('videoStill/channels/filename').get('value'))
    texture.CreateInput('wrapS', Sdf.ValueTypeNames.String).Set(usdInputMap['uvTile'][xml.find('txtrLocator/channels/tileU').get('value')])
    texture.CreateInput('wrapT', Sdf.ValueTypeNames.String).Set(usdInputMap['uvTile'][xml.find('txtrLocator/channels/tileV').get('value')])
    
    #---------------------------------------------------- Connect the texture locator to the texture
    texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(uvTransform.ConnectableAPI(), 'result')
    
    #texture.CreateInput('St', Sdf.ValueTypeNames.Float2).Set((0,0))
    #texture.CreateOutput('alpha', Sdf.ValueTypeNames.Double)
    # texture.CreateInput('fallback', Sdf.ValueTypeNames.Color4f).Set()
    # texture.CreateInput('scale', Sdf.ValueTypeNames.Color4f).Set()
    # texture.CreateInput('bias', Sdf.ValueTypeNames.Color4f).Set()
    
    texture.CreateOutput('r', Sdf.ValueTypeNames.Float)
    texture.CreateOutput('g', Sdf.ValueTypeNames.Float)
    texture.CreateOutput('b', Sdf.ValueTypeNames.Float)
    texture.CreateOutput('a', Sdf.ValueTypeNames.Float)
    texture.CreateOutput('rgb', Sdf.ValueTypeNames.Color3f)
    
    return texture

# Connect a texture to the relevant shader
def connectTextureToShaderInput(textureFinal:UsdShade.Shader, shader:UsdShade.Shader, modoInputName:str) -> UsdShade.Input:
    if modoInputName in usdInputMap['effect'].keys():
        inputName = usdInputMap['effect'][modoInputName]
        input = shader.GetInput(inputName)
        output = textureFinal.GetOutput("out")
        
        if input.Get() != None:
            return input.ConnectToSource(output)
        else:
            return createUsdShaderInput(shader, inputName, output, usdTypeMap[inputName])
    
    print("Effect %s not found in stringMap" % modoInputName)
    return None

# Format any channel value to given type
def formatChannelValue(channel:modo.Channel): 
    #return(value)
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

# Use a filter list to allow or  disallow a channel to be processed (is the filter option is on,
# some channels are just ignored to make files lighter. Some channels are really not relevant for
# export but unfiltered outputs are usefull for debugging and figuring what the shaderTree has to offer)
def isFiltered(chName:str, itemType:str=None):
    #---------------------------------------------- if no itemType specified, return everything
    if itemType == None:
        return True
    
    #---------------------------------------------- Ignore if filters has no itemType entry
    if (itemType not in filters.keys()): return False
    
    fMap = filters[itemType]
    
    #---------------------------------------------- Ignore if filters has no filter
    if (len(fMap) == 0):return False
    
    #---------------------------------------------- Return channel if has filter
    if (str(chName).split('.')[0] in fMap):return True
    
    #---------------------------------------------- Ignore everything else
    return False
