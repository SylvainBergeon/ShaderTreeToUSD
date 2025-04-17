# python
import sys
import os

import lx
import lxu.command
import python_modules.ShaderTree as ST

try:
    from importlib import reload
except ImportError:
    from imp import reload

def reload_modules():
    reload(ST)

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
        # Reload modules (for development stage only: remove for final release)
        reload_modules()
        
        # Call the export function with the selected options
        ST.export_basic_execute(self, msg)
        
        msg.SetCode(lx.result.OK)

lx.bless(Cmd_ExportShaderTree, "exportShaderTree")