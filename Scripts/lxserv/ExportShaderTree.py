# python
import sys
import os

import lx
import lxu.command

# looks like we need this to keep referencing ST at module root
ST = None
SF = None

try:
    from importlib import reload, import_module
except ImportError:
    from imp import reload
    from importlib import import_module

# ShaderTree imports from these (`from .normalize import normalize as normalize_shadertree`), but
# reload(ST) only re-executes ShaderTree.py itself, not the modules it imports - so without reloading
# these explicitly first, edits under normalize/ would need a Modo restart to take effect, unlike
# ShaderTree.py/ShaderFilters.py. Submodules first, package __init__.py last, so the package's
# `from .specular_ior import ...`-style lines rebind to the freshly reloaded submodules.
NORMALIZE_MODULES = [
    "python_modules.normalize.specular_ior",
    "python_modules.normalize.blend_operators",
    "python_modules.normalize.projection_defaults",
    "python_modules.normalize.effect_channel_names",
    "python_modules.normalize.node_registry",
    "python_modules.normalize",
]

def reload_modules():
    global ST, SF
    for module_name in NORMALIZE_MODULES:
        if module_name in sys.modules:
            reload(sys.modules[module_name])
        else:
            import_module(module_name)

    if SF is not None:
        reload(SF)
    else:
        import python_modules.ShaderFilters as SF

    if ST is not None:
        reload(ST)
    else:
        import python_modules.ShaderTree as ST

class Cmd_ExportShaderTree(lxu.command.BasicCommand):

    def __init__(self):
        lxu.command.BasicCommand.__init__(self)
        self.dyna_Add('item', '&item')
        self.basic_SetFlags(0, lx.symbol.fCMDARG_OPTIONAL)
        
        # Define each preference with its default value and group
        preferences = {
            #---------------------------------------------------- Export options
            'USDExport_export_json': False,
            'USDExport_export_xml': False,
            'USDExport_export_usd': True,
            'USDExport_export_usda': False,
            'USDExport_export_usdz': False,
            'USDExport_consolidateScene': False,
            'USDExport_saveDiagnostic': True,
            #---------------------------------------------------- Event log message
            'USDExport_verbose': False,
            'USDExport_verboseSetValue': True,
            'USDExport_verboseCreateShader': True,
            'USDExport_verboseOverrideValue': True,
            'USDExport_verboseModifyTree': True,
            'USDExport_verboseConsolidate': True,
            'USDExport_verboseUnsupported': True,
            #---------------------------------------------------- USD options
            'USDExport_exportGlPreviewMaterial': False
        }

        for pref_name, default_value in preferences.items():
            # Check if the user value is already defined
            if not lx.eval(f'query scriptsysservice userValue.isDefined ? {pref_name}'):
                print(f"Set default user value {pref_name} = {str(default_value).lower()}")
                
                # Define the user value with a label
                lx.eval(f'user.defNew {pref_name} boolean')
                
                # Set the default value
                lx.eval(f'user.value {pref_name} {str(default_value).lower()}')
                                 
    def cmd_Flags(self) -> int:
      return lx.symbol.fCMD_UNDO | lx.symbol.fCMD_MODEL

    def cmd_Enable(self, msg):
        return True

    def basic_Execute(self, msg, flags):
        global ST, SF    
        # reloads external modules - offloading to external module(s)makes development & debugging quicker since 
        # code edited in those modules does not require a re-start of modo to run. Only changes to this module 
        # require a restart.
        
        # try:
        #     reload_modules()
        # except NameError:
        #     # deferred import of python_modules - fixes an issue with Modo crashing
        #     # in Windows on startup as the kit is being parsed by lxserv. Now it's imported
        #     #the first time the commend is run.
        #     import python_modules.ShaderTree as ST
        
        reload_modules()
        
        # Call the export function with the selected options
        ST.export_basic_execute(self, msg)
        
        msg.SetCode(lx.result.OK)

lx.bless(Cmd_ExportShaderTree, "exportShaderTree")