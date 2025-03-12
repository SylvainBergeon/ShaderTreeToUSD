# python
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
            'USDExport_export_json': (False, "USD_Export: Export JSON"),
            'USDExport_export_xml': (False, "USD_Export: Export XML"),
            'USDExport_export_usda': (True, "USD_Export: Export USDA"),
            'USDExport_consolidateScene': (False, "USD_Export: Consolidate Scene"),
            'USDExport_saveDiagnostic': (True, "USD_Export: Save Diagnostic"),
            #---------------------------------------------------- Event log message
            'USDExport_verbose': (False, "USD_Export: Verbose Output"),
            'USDExport_verboseSetValue': (True, "USD_Export: Verbose Set Value"),
            'USDExport_verboseCreateShader': (True, "USD_Export: Verbose Create Shader"),
            'USDExport_verboseOverrideValue': (True, "USD_Export: Verbose Override Value"),
            'USDExport_verboseModifyTree': (True, "USD_Export: Verbose Modify Tree"),
            'USDExport_verboseConsolidate': (True, "USD_Export: Verbose Consolidate"),
            'USDExport_verboseUnsupported': (True, "USD_Export: Verbose Unsupported"),
            #---------------------------------------------------- Filter options
            'USDExport_preFilterChannels': (False, "USD_Export: Pre-filter Channels"),
            #---------------------------------------------------- USD options
            'USDExport_exportGlPreviewMaterial': (False, "USD_Export: Export GL Preview Material")
        }

        for pref_name, (default_value, label) in preferences.items():
            
            # Check if the user value is already defined
            if not lx.eval(f'query scriptsysservice userValue.isDefined ? {pref_name}'):
                print(f"Set user value {pref_name} = {str(default_value).lower()}")
                
                # Define the user value with a label
                lx.eval(f'user.defNew {pref_name} boolean')
            
                # Define the user value label
                lx.eval(f'user.def {pref_name} label "{label}"')
                
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