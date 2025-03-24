# python
import sys
import os

# Register pixar's USD lib (pxr)
project_dir = os.path.dirname(__file__)
pxr_path = os.path.join(project_dir, 'libs')
sys.path.insert(0, pxr_path)

import lx
import lxu.command
import python_modules.ShaderTree

try:
    from importlib import reload
except ImportError:
    from imp import reload

def reload_modules():
    reload(python_modules.ShaderTree)

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
            'USDExport_export_usda': True,
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
     
        # reloads external modules - offloading to external module(s)makes development & debugging quicker since 
        # code edited in those modules does not require a re-start of modo to run. Only changes to this module 
        # require a restart.
        reload_modules()
        
        # Call the export function with the selected options
        python_modules.ShaderTree.export_basic_execute(self, msg)
        
        msg.SetCode(lx.result.OK)

lx.bless(Cmd_ExportShaderTree, "exportShaderTree")