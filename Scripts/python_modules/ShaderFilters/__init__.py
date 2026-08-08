# Modo <-> USD correspondence tables, one file per table (mirrors Scripts/python_modules/normalize/'s
# layout). Re-exported here so `from .ShaderFilters import usdTypeMap` etc. keeps working unchanged from
# ShaderTree.py - this package boundary is an implementation detail, not something callers need to know.
#
# Live (actually imported by ShaderTree.py):
from .channel_types import channelTypeMap
from .usd_types import usdTypeMap
from .std_mat_channel_map import stdMatChannelMap

# Not currently used anywhere - see each file's header for why they're kept around regardless:
from .filters import filters
from .input_map import usdInputMap
