import lx

# Modo channel storage type (lx.symbol.iCHANTYPE_*) -> plain string, used by _UTIL_format_channel (stage 1,
# XML/JSON extraction) to record what kind of value a channel holds alongside its value.
channelTypeMap = {
    lx.symbol.iCHANTYPE_EVAL:     "eval",
    lx.symbol.iCHANTYPE_FLOAT:    "float",
    lx.symbol.iCHANTYPE_INTEGER:  "integer",
    lx.symbol.iCHANTYPE_GRADIENT: "gradient",
    lx.symbol.iCHANTYPE_STORAGE:  "string",
    lx.symbol.iCHANTYPE_NONE:     "none",
}
