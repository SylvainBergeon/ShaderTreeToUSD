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

    def cmd_Flags(self) -> int:
      return lx.symbol.fCMD_UNDO | lx.symbol.fCMD_MODEL

    def cmd_Enable(self, msg):
        return True

    def basic_Execute(self, msg, flags):
        # reloads external modules - offloading to external module(s)makes development & debugging quicker since 
        # code edited in those modules does not require a re-start of modo to run. Only changes to this module 
        # require a restart.
        reload_modules()

        python_modules.ShaderTree.export_basic_execute(self, msg)
        
        msg.SetCode(lx.result.OK)

lx.bless(Cmd_ExportShaderTree, "exportShaderTree")