"""
Channel Utilities ripped from old lxe library.

NOTE: This is taken from lxe as-is to reuse the code.
Optimally this should be rewritten to fit modox but no time for this.
"""


import traceback

import lx
import lxu.select
from .item import Item as ModoxItem


# Graph names.
sGRAPH_NAME_CHANLINKS = 'chanLinks'

# Modes for read and writing channel values when copying channels:
#   VALUE -- will read single value (or eval) at given time (set separately).
#   KEY -- time slice read mode - reads a key and all its properties if there is a key.
#   ALL -- will read entire channel, write mode doesn't matter, it'll be a perfect copy.
#
#   STATIC -- always writes static value, wipes out any existing animation.
#   AUTO -- creates key if channel is already animated, writes static value otherwise.
#   FORCEKEY -- always creates new key, adds envelope with first key to static channel.
iCHAN_READMODE_VALUE = 1
iCHAN_READMODE_KEY = 2
iCHAN_READMODE_ALL = 3
iCHAN_WRITEMODE_STATIC = 1
iCHAN_WRITEMODE_AUTO = 2
iCHAN_WRITEMODE_FORCEKEY = 3

# Modes for writing envelopes.
# Replace mode is going to wipe out all keys before any writing.
iENV_WRITEMODE_REPLACE = 1
iENV_WRITEMODE_ADD = 2

# storage types are returned from Item() ChannelStorageType method
sCHAN_STORAGE_TYPE_FLOAT = 'float'
sCHAN_STORAGE_TYPE_INTEGER = 'integer'
sCHAN_STORAGE_TYPE_BOOLEAN = 'boolean'
sCHAN_STORAGE_TYPE_DISTANCE = 'distance'
sCHAN_STORAGE_TYPE_PERCENT = 'percent'
sCHAN_STORAGE_TYPE_ANGLE = 'angle'
sCHAN_STORAGE_TYPE_MATRIX = 'matrix4'
sCHAN_STORAGE_TYPE_STRING = 'string'

# string types will be used by the ChannelAddUser method
# they're the same as storage type except for the matrix
sCHAN_STRING_TYPE_MATRIX = 'matrix'


class ChannelId:
    """ Simple class to provide ident for channels.
    Channels is identified by item they belong to and the channel index. """

    # TODO: change chan_idx to idx
    def __init__(self, item, chan_idx):
        self.item = item
        self.chan_idx = chan_idx

    def StringIdent(self):
        """ Return channel id as string ident required by various commands.
        """
        return '%s:%s' % (self.item.Ident(), self.item.ChannelName(self.chan_idx))


class ChannelUtils:
    """ Channel utilities class.
    """

    def __init__(self):
        pass

    def CopyItemChannelsByName(
            self,
            chan_read,
            chan_write,
            src_item,
            dst_item,
            src_chan_names,
            dst_chan_names=None,
            read_mode=iCHAN_READMODE_VALUE,
            write_mode=iCHAN_WRITEMODE_AUTO,
            mutual_copy=False,
            negate_values=False,
            add_non_existent=False,
            write_time=0.0,
            env_write_mode=iENV_WRITEMODE_REPLACE):
        """ Copy a set of item channels from one item to another.
        It's possible to provide different channel lists for source
        and target items although you need to make sure that channel
        types for channels of the same name match.
        Pass None to dst_chan_names to copy exact same channels between
        items.
        Args:
        - mutual_copy -- will copy dst item channels to src one.
        - write_time -- this is temporary? needs to be provided because there's no way
        - env_write_mode -- this is for writing envelopes ONLY. allows for adding keys if envelope exists
            rather then wiping out all the keys first.
        of getting write time from ChannelWrite.
        """
        # TODO: Make it call copy item channels and not be totally separate method?
        try:
            if isinstance(src_chan_names, list) == False:
                src_chan_names = [src_chan_names]

            if not dst_chan_names:
                dst_chan_names = src_chan_names
            elif isinstance(dst_chan_names, list) == False:
                dst_chan_names = [dst_chan_names]

            chan_read_utils = ChannelReadUtils()
            chan_write_utils = ChannelWriteUtils(chan_read)

            length = min(len(src_chan_names), len(dst_chan_names))
            # lx.out('copying %d channels over' % length)
            for x in range(length):
                chan_data_pack = ChannelDataPack()
                # read channel as data pack
                chan_data_pack = chan_read_utils.GetAsDataPackByName(
                    chan_read,
                    src_item,
                    src_chan_names[x],
                    read_mode,
                    negate_values)
                # this is to set change key data pack time into write time
                if read_mode == iCHAN_READMODE_KEY and chan_data_pack.keyframe_data_pack:
                    chan_data_pack.keyframe_data_pack.time = write_time
                if mutual_copy:
                    dst_chan_data_pack = chan_read_utils.GetAsDataPackByName(
                        chan_read,
                        dst_item,
                        dst_chan_names[x],
                        read_mode,
                        negate_values)
                    # change key data pack time to write time
                    if read_mode == iCHAN_READMODE_KEY and dst_chan_data_pack.keyframe_data_pack:
                        dst_chan_data_pack.keyframe_data_pack.time = write_time
                # write channel from data pack
                chan_write_utils.SetFromDataPackByName(
                    chan_write,
                    dst_item,
                    dst_chan_names[x],
                    chan_data_pack,
                    write_mode,
                    add_non_existent,
                    env_write_mode)
                if mutual_copy:
                    chan_write_utils.SetFromDataPackByName(
                        chan_write,
                        src_item,
                        src_chan_names[x],
                        dst_chan_data_pack,
                        write_mode,
                        add_non_existent,
                        env_write_mode)
        except:
            lx.out(traceback.format_exc())
            raise

    def CopyTransformChannelsByName(
            self,
            chan_read,
            chan_write,
            src_item,
            dst_item,
            src_chan_names,
            dst_chan_names=None):
        pass

    def FilterStaticKeysByName(self, item, chan_name):
        pass

    def FilterStaticKeys(
            self,
            chan_read,
            chan_write,
            item,
            chan_idx,
            delete_static_env=False,
            tolerance=0.00001):
        """ Filter a channel and delete static keys
        that do not change envelope flow.
        Return number of deleted keys or -1 if entire envelope was removed.

        Args:
        delete_static_env -- will delete envelope if there's only one key left.
        tolerance --  used for filtering float type envelopes, doesn't matter for int
        """
        try:
            # lx.out('filtering channel: %s:%s' % (item.UniqueName(), item.ChannelName(chan_idx)))
            chan_read_utils = ChannelReadUtils()
            chan_write_utils = ChannelWriteUtils(chan_read)

            if not chan_read_utils.IsAnimated(chan_read, item, chan_idx):
                return False

            # TODO: shall I test if the envelope is returned here?
            envelope = lx.object.Envelope(chan_write_utils.GetEnvelope(chan_write, item, chan_idx))
            env_utils = EnvelopeUtils(envelope)
            deleted_keys, env_static = env_utils.FilterStaticKeys(tolerance)

            # if delete_static_env is false or an envelope is not static
            # (stil has some animation) exit early
            if not delete_static_env or not env_static:
                return deleted_keys

            # if env_utils.KeyCount() > 1:
            #    return True

            # delete an envelope by writing static value to it
            # TODO: for now - return -1 if envelope was deleted
            # there will be no info about keys
            val = chan_read_utils.GetValue(chan_read, item, chan_idx)
            chan_write_utils.SetValue(chan_write, item, chan_idx, val, iCHAN_WRITEMODE_STATIC)
            return -1
        except:
            lx.out(traceback.format_exc())
            raise


class ChannelLinks:
    """ Manage links between channels.
    """

    # TODO: Needs to be general and taka a graph name too
    def __init__(self):
        scene = lx.object.Scene(lxu.select.SceneSelection().current())
        # to get channel graph simply cast the CHANLINKS scene graph
        try:
            self.chan_graph = lx.object.ChannelGraph(scene.GraphLookup(lx.symbol.sGRAPH_CHANLINKS))
        except LookupError:
            self.chan_graph = None

    def Add(self,
            out_item,
            out_channel_idx,
            in_item,
            in_channel_idx):
        """ Add a link between two channels.
        Return True if operation was successfull or
        if there already was link in place.
        """
        try:
            if not self.chan_graph or not out_item or not in_item:
                return False
            try:
                self.chan_graph.AddLink(
                    out_item,
                    out_channel_idx,
                    in_item,
                    in_channel_idx)
            except Exception:
                return False
            return True
        except:
            lx.out(traceback.format_exc())
            raise


class ChannelDataPack:
    """ Channel Data structure.
    Store all channel data, either static value or entire envelope.
    Attributes:
        type -- type of the channel, float, int, distance, percent, etc. ChannelStorageType method value
        value -- static channel value or a single value from action, setup, etc.
        NOTE: value can be of many different types! be sure to set channel type.
        keyframe_data_pack -- used for time slice copying, stores single key info.
        envelope_data_pack -- EnvelopeDataPack.
        time_offset -- shift keys (if any) in time
        value_offset -- shift values
        value_multiplier -- can be used for mirroring
    """

    def __init__(self):
        self.type = None
        self.value = None
        self.keyframe_data_pack = None
        self.envelope_data_pack = None

        self.time_offset = 0.0
        self.value_offset = 0.0
        self.value_multiplier = 1.0

    def SetTimeOffset(self, time_offset):
        self.time_offset = time_offset

    def SetValueOffset(self, value_offset):
        self.value_offset = value_offset

    def SetValueMultiplier(self, value_multiplier):
        self.value_multiplier = value_multiplier


class ChannelReadUtils:
    """ Utilities for reading channel values.
    TODO: Read evaluated setup channels.
    """

    def __init__(self):
        self.selection_service = lx.service.Selection()
        scene_selection = lxu.select.SceneSelection()
        self.scene = lx.object.Scene(scene_selection.current())
        self.read_mode = iCHAN_READMODE_VALUE

    def IsAnimated(
            self,
            chan_read,
            item,
            chan_idx):
        """ Return bool value indicating whether a channel
        is animated (has an envelope) or not.
        """
        try:
            try:
                envelope = lx.object.Envelope(chan_read.Envelope(item, chan_idx))
            except LookupError:
                return False
            return True
        except:
            lx.out(traceback.format_exc())
            raise

    def IsKeyframed(
            self,
            chan_read,
            item,
            chan_idx):
        """ Check if a channel has a keyframe at a time set in channel read.
        """
        try:
            try:
                envelope = lx.object.Envelope(chan_read.Envelope(item, chan_idx))
            except LookupError:
                return False
            # chan_read = lx.object.ChannelRead(chan_read)
            time = chan_read.Time()
            env_utils = EnvelopeUtils(envelope)
            return env_utils.KeyExists(time)

        except:
            lx.out(traceback.format_exc())
            raise

    def TimeRange(
            self,
            chan_read,
            item,
            chan_idx):
        """ Get first and last keys time for a channel.
        Raise ValueError if channel is not animated.
        """
        try:
            try:
                envelope = lx.object.Envelope(chan_read.Envelope(item, chan_idx))
            except LookupError:
                raise ValueError

            keyframe_extra = KeyframeExtended(envelope.Enumerator())
            try:
                return keyframe_extra.KeyTimeRange()
            except ValueError:
                raise ValueError
        except:
            lx.out(traceback.format_exc())
            raise

    def GetValueByName(
            self,
            chan_read,
            item,
            chan_name,
            negative=False):
        """ Same as GetValue but channel is passed by name, not index.
        """
        try:
            try:
                chan_idx = item.ChannelLookup(chan_name)
            except LookupError:
                chan_idx = None
            if chan_idx is None:
                # TODO: This is wrong, I should rise an exception!
                return None

            return self.GetValue(chan_read, item, chan_idx, negative)
        except:
            lx.out(traceback.format_exc())
            raise

    def GetValue(
            self,
            chan_read,
            item,
            chan_idx,
            negative=False):
        """ Get channel value by index.
        Works on integers, floats and strings.
        Args:
        item --  item object to which channel belongs.
        chan_read -- ChannelRead object to use for reading.
        negative -- allows for reading negated value, useful for mirroring.
        """
        try:
            item = lx.object.Item(item)
            # chan_read = lx.object.ChannelRead()
            chan_type = item.ChannelType(chan_idx)
            value = None

            if chan_type == lx.symbol.iCHANTYPE_INTEGER:
                if not negative:
                    value = chan_read.Integer(item, chan_idx)
                else:
                    value = (chan_read.Integer(item, chan_idx) * -1)
            elif chan_type == lx.symbol.iCHANTYPE_FLOAT:
                if not negative:
                    value = chan_read.Double(item, chan_idx)
                else:
                    value = (chan_read.Double(item, chan_idx) * -1.0)
            elif chan_type == lx.symbol.iCHANTYPE_STORAGE:
                chan_storage_type = item.ChannelStorageType(chan_idx)
                if chan_storage_type == sCHAN_STORAGE_TYPE_STRING:
                    value = chan_read.String(item, chan_idx)
            return value
        except:
            lx.out(traceback.format_exc())
            raise

    def GetAsDataPackByName(
            self,
            chan_read,
            item,
            chan_name,
            read_mode=iCHAN_READMODE_ALL,
            negative=False):
        """ Same as GetDataPack but channel is passed by name, not index.
        """
        try:
            try:
                chan_idx = item.ChannelLookup(chan_name)
            except LookupError:
                chan_idx = None

            if chan_idx is None:
                return None

            return self.GetAsDataPack(chan_read, item, chan_idx, read_mode, negative)
        except:
            lx.out(traceback.format_exc())
            raise

    def GetAsDataPack(
            self,
            chan_read,
            item,
            chan_idx,
            read_mode=iCHAN_READMODE_ALL,
            negative=False):
        """ Get entire channel contents as channel data pack.
        This can be either single, user set value or
        an envelope if the channel is animated.
        Args:
        - read_mode -- read value, a single key or entire channel contents
        - negative -- allows for reading negated values
        Data pack is always returned. If something goes wrong with reading channel value
        the data pack will only contain channel type at least. All other attributes
        will be None.
        """
        # TODO: change negative to multplier?
        # then negation would simply be -1.0 multiplier
        # TODO: optimize processing read modes
        try:
            chan_data_pack = ChannelDataPack()

            item = lx.object.Item(item)
            chan_data_pack.type = item.ChannelStorageType(chan_idx)

            # Asked for channel value as data pack only
            if read_mode == iCHAN_READMODE_VALUE:
                chan_data_pack.value = self.GetValue(chan_read, item, chan_idx, negative)
                # lx.out('%s:%s - %s' % (item.UniqueName(), item.ChannelName(chan_idx), str(chan_data_pack.value)))
                return chan_data_pack
            elif read_mode == iCHAN_READMODE_ALL:
                # Test if channel is animated.
                try:
                    envelope = lx.object.Envelope(chan_read.Envelope(item, chan_idx))
                except LookupError:
                    envelope = None
                except RuntimeError:
                    # channel can't have an envelope - like matrix channel
                    # don't read this channel and quit immediately
                    return chan_data_pack

                # Simply get value if channel is not animated.
                # So same as above.
                if not envelope:
                    chan_data_pack.value = self.GetValue(chan_read, item, chan_idx, negative)
                    return chan_data_pack

                # Getting an envelope.
                envelope_utils = EnvelopeUtils(envelope)
                envelope_data_pack = EnvelopeDataPack()
                envelope_data_pack = envelope_utils.GetAsDataPack(negative)

                if not envelope_data_pack:
                    return chan_data_pack

                chan_data_pack.envelope_data_pack = envelope_data_pack
                return chan_data_pack
            elif read_mode == iCHAN_READMODE_KEY:
                # see if there's an envelope and a key at current frame
                try:
                    envelope = lx.object.Envelope(chan_read.Envelope(item, chan_idx))
                except LookupError:
                    envelope = None
                if not envelope:
                    chan_data_pack.value = self.GetValue(chan_read, item, chan_idx, negative)
                    return chan_data_pack
                # see if there's a key?
                envelope_utils = EnvelopeUtils(envelope)
                key_data_pack = envelope_utils.GetKeyAsDataPack(chan_read.Time(), negative)
                if key_data_pack:
                    chan_data_pack.keyframe_data_pack = key_data_pack
                else:
                    chan_data_pack.value = self.GetValue(chan_read, item, chan_idx, negative)
                return chan_data_pack
            return chan_data_pack
        except:
            lx.out(traceback.format_exc())
            raise


class ChannelWriteUtils:
    """ Utilities for writing channel values.
    NOTE: This is not final solution but channel write
    needs to have channel read available as well for some methods.
    It's recommended to pass chan_read to write utils.
    """

    def __init__(self, chan_read=None):
        # action_layer=lx.symbol.s_ACTIONLAYER_EDIT,
        # chan_time=None):
        self.selection_service = lx.service.Selection()
        scene_selection = lxu.select.SceneSelection()
        self.scene = lx.object.Scene(scene_selection.current())

        # Init write interface
        # self.chan_write = lx.object.ChannelWrite()
        # self.SetWriteAccess(action_layer, chan_time)
        self.write_mode = iCHAN_WRITEMODE_AUTO
        if chan_read:
            self.chan_read = chan_read
        else:
            self.chan_read = None

    def NewEnvelope(
            self,
            chan_write,
            item,
            chan_idx,
            initial_key=False):
        """ Add new envelope to a channel if it doesn't exist yet.
        Return the envelope object.
        Args:
            initial_key:    set this to false (default) if you want
                            new envelope to be cleared. Otherwise the envelope
                            will not be changed if it already was on channel
                            or have one default key.
        """
        try:
            envelope = lx.object.Envelope(chan_write.Envelope(item, chan_idx))
            if not initial_key:
                envelope.Clear()
            return envelope
        except:
            lx.out(traceback.format_exc())
            raise

    def GetEnvelope(
            self,
            chan_write,
            item,
            chan_idx):
        """ Get Channel envelope for writing.
        NOTE: If you passed channel read object it will return existing envelope if any.
        If you didn't pass channel read object to utils first or there is no envelope -
        one will be created.
        """
        try:
            # self.chan_read = lx.object.ChannelRead()
            # see if there's already an envelope on the channel
            # envelope method on channel read HAS to be used.
            # if there is just pull it from channel write interface
            # so it's got access to write.
            envelope = lx.object.Envelope()
            if not self.chan_read is None:
                try:
                    envelope = self.chan_read.Envelope(item, chan_idx)
                except LookupError:
                    pass
                else:
                    # Should be safe to grab writable envelope now
                    envelope = chan_write.Envelope(item, chan_idx)
            # return lx.object.Envelope(chan_write.Envelope(item, chan_idx))
            # or get new envelope without any key
            if not envelope.test():
                envelope = self.NewEnvelope(chan_write, item, chan_idx, False)
            return envelope
        except:
            lx.out(traceback.format_exc())
            raise

    def SetValueByName(
            self,
            chan_write,
            item,
            chan_name,
            value,
            write_mode=iCHAN_WRITEMODE_AUTO):
        try:
            try:
                chan_idx = item.ChannelLookup(chan_name)
            except LookupError:
                chan_idx = None

            if chan_idx is None:
                return False

            return self.SetValue(chan_write, item, chan_idx, value, write_mode)
        except:
            lx.out(traceback.format_exc())
            raise

    def SetValue(
            self,
            chan_write,
            item,
            chan_idx,
            value,
            write_mode=iCHAN_WRITEMODE_AUTO,
            value_offset=0.0,
            value_multiplier=1.0):
        """ Set single channel value.
        Use this method only to set single values or
        to force channel to static (no envelope).
        Works with integers, floats and string. With string the write mode doesn't matter.
        TODO: Make sure it works with percents, distances, etc.
        """
        try:
            item = lx.object.Item(item)
            chan_type = item.ChannelType(chan_idx)

            if chan_type == lx.symbol.iCHANTYPE_INTEGER:
                value = int(float(value + value_offset) * value_multiplier)
                if write_mode == iCHAN_WRITEMODE_STATIC:
                    chan_write.Integer(item, chan_idx, value)
                elif write_mode == iCHAN_WRITEMODE_AUTO:
                    chan_write.IntegerKey(item, chan_idx, value, 0)
                elif write_mode == iCHAN_WRITEMODE_FORCEKEY:
                    chan_write.IntegerKey(item, chan_idx, value,
                                          1)  # last argument forces creating a key and an envelope

            elif chan_type == lx.symbol.iCHANTYPE_FLOAT:
                value = float((value + value_offset) * value_multiplier)
                if write_mode == iCHAN_WRITEMODE_STATIC:
                    chan_write.Double(item, chan_idx, value)
                elif write_mode == iCHAN_WRITEMODE_AUTO:
                    chan_write.DoubleKey(item, chan_idx, value, 0)
                elif write_mode == iCHAN_WRITEMODE_FORCEKEY:
                    chan_write.DoubleKey(item, chan_idx, value, 1)  # last argument forces creating a key

            elif chan_type == lx.symbol.iCHANTYPE_STORAGE:
                chan_storage_type = item.ChannelStorageType(chan_idx)
                if chan_storage_type == lxe.symbol.sCHAN_STORAGE_TYPE_STRING:
                    value = str(value)
                    chan_write.String(item, chan_idx, value)
        except:
            lx.out(traceback.format_exc())
            raise

    def SetFromDataPackByName(
            self,
            chan_write,
            item,
            chan_name,
            chan_data_pack,
            write_mode=iCHAN_WRITEMODE_AUTO,
            add_non_existent=False,
            env_write_mode=iENV_WRITEMODE_REPLACE):
        """
        Args:
            add_non_existent:   will add not found channel to the item if true.
        """
        try:
            if not chan_data_pack or not item:
                return False

            try:
                chan_idx = item.ChannelLookup(chan_name)
            except LookupError:
                chan_idx = None
                # Add Non existent channel if flag is on
                if add_non_existent:
                    item_extra = ModoxItem(item)
                    item_extra.addUserChannel(chan_name, chan_data_pack.type)
                    try:
                        chan_idx = item.ChannelLookup(chan_name)
                    except LookupError:
                        chan_idx = None

            if chan_idx is None:
                return False

            return self.SetFromDataPack(chan_write, item, chan_idx, chan_data_pack, write_mode, env_write_mode)
        except:
            lx.out(traceback.format_exc())
            raise

    def SetFromDataPack(
            self,
            chan_write,
            item,
            chan_idx,
            chan_data_pack,
            write_mode=iCHAN_WRITEMODE_AUTO,
            env_write_mode=iENV_WRITEMODE_REPLACE):
        """ Set channel from data pack.

        Can be used to set single values but more importantly
        to set entire channel with envelope and keys.
        Args:
        = write_mode --- is only really used for single value write
        """
        # TODO: Passing time offset, value offset and multiplier is SHIT
        # There should be data pack methods to apply these to data pack directly.
        try:
            if not chan_data_pack or not item:
                return False

            item = lx.object.Item(item)

            if chan_data_pack.envelope_data_pack:
                # Set entire envelope. By default it's using existing envelope
                # and creating new one ONLY if there was no envelope already.
                # TODO: Should there be a flag or something to always create fresh envlope?
                envelope = self.GetEnvelope(chan_write, item, chan_idx)
                # envelope = self.NewEnvelope(chan_write, item, chan_idx)
                envelope_utils = EnvelopeUtils(envelope)
                # TODO: This is temporary until it will be possible to set envelope interpolation
                # via SDK. Right now it needs to be done by firing command.
                envelope_utils.chan_ident_string = '%s:%s' % (item.Ident(), item.ChannelName(chan_idx))
                envelope_utils.SetFromDataPack(chan_data_pack.envelope_data_pack,
                                               env_write_mode,
                                               chan_data_pack.time_offset,
                                               chan_data_pack.value_offset,
                                               chan_data_pack.value_multiplier)
            elif chan_data_pack.keyframe_data_pack:
                # this needs to set a key from data pack
                # TODO: I may need to add chan_read as argument here anyways
                # as in this case i need to test if there is an envelope first
                # the issue is that GetEnvelope will create an envelope with initial key
                # at the current chan write time which may not be what i want
                envelope = lx.object.Envelope(self.GetEnvelope(chan_write, item, chan_idx))
                envelope_utils = EnvelopeUtils(envelope)
                # alter the time of data pack key so it's current chan write time
                # TODO: think about key time here, it's hard coded that key time is ignored
                # when setting channel from data pack that has one keyframe in it
                # TODO: NEED A WAY TO PASS WRITE TIME!!!
                chan_data_pack.keyframe_data_pack.time = 0.0  # chan_write.Time()
                envelope_utils.SetKeyFromDataPack(chan_data_pack.keyframe_data_pack,
                                                  chan_data_pack.time_offset,
                                                  chan_data_pack.value_offset,
                                                  chan_data_pack.value_multiplier)
            elif chan_data_pack.value is not None:
                # No envelope, set single value in static mode. """
                # lx.out(chan_data_pack.value)
                self.SetValue(chan_write,
                              item,
                              chan_idx,
                              chan_data_pack.value,
                              write_mode,
                              chan_data_pack.value_offset,
                              chan_data_pack.value_multiplier)
                # lx.out('%s:%s - %s' % (item.UniqueName(), item.ChannelName(chan_idx), str(chan_data_pack.value)))
            else:
                return True
            return True
        except:
            lx.out(traceback.format_exc())
            raise


class KeyframeDataPack:
    """ Contains all properties of single keyframe.

    Properties:
        value_side      - ENVSIDE value to tell which side of the value controls keyframe at its time
                          when setting keyframe make sure to set value to for the controlling side as a last value

    TODO: Maybe change slope and weight props names to indicate they are values? Add 'Value' to them.
    """

    def __init__(self):
        self._empty = True
        self._is_int = False

        self.time = 0.0
        self.break_flags = 0
        self.value_side = lx.symbol.iENVSIDE_IN

        self.broken_value = 0
        self.broken_slope = 0
        self.broken_weight = 0

        self.i_value_in = 0
        self.i_value_out = 0
        self.f_value_in = 0.0
        self.f_value_out = 0.0

        self.slope_type_in = lx.symbol.iSLOPE_AUTO
        self.manual_weight_in = False
        self.slope_type_out = lx.symbol.iSLOPE_AUTO
        self.manual_weight_out = False
        self.slope_in = 0.0
        self.slope_out = 0.0

        self.weight_in = 0.0
        self.weight_out = 0.0


class KeyframeExtended(lx.object.Keyframe):
    """ Extended Keyframe object.
    """

    def __init__(self, keyframe_object=None):
        """ Init needs to initialize the parent lx.object.Keyframe object.
        It needs to account for two situations:
        when you pass keyframe object upon initialization and when you don't.

        Properties:
            is_int:     should be set to process proper type of values. typically
                        this flag can be obtained from Envelope object and passed here.
        """

        if keyframe_object is not None:
            lx.object.Keyframe.__init__(keyframe_object)
        else:
            lx.object.Keyframe.__init__(lx.object.Item())

        self.is_int = False

    def SetIsInt(self, is_int=False):
        """ Set this to true if you're processing integer keys.
        is_int comes from envelope and you have to set it here to process
        reading/writing key values properly.
        Keyframe doesn't know its own type, using float or int methods is on user.
        """
        self.is_int = is_int

    def Count(self):
        """ Return number of keys in enumerator.
        """
        try:
            count = 0
            try:
                self.First()
            except LookupError:
                return count

            enum_keys = True
            while enum_keys:
                count += 1
                try:
                    self.Next()
                except LookupError:
                    enum_keys = False
                    break
            return count
        except:
            lx.out(traceback.format_exc())
            raise

    def KeyTimeRange(self):
        """ Return time range by returning times for first and list key.
        If only one key is present then both start and end of range is the same time.
        If no keys are preset - raise ValueError.
        """
        try:
            self.First()
        except LookupError:
            raise ValueError

        time_range_start = self.GetTime()

        try:
            self.Last()
        except LookupError:
            time_range_end = time_range_start
        else:
            time_range_end = self.GetTime()
        return time_range_start, time_range_end

    def KeyExists(self, time):
        """ Check if there's a key exactly at a given time.
        """
        try:
            # Find selects a key for further operation.
            # using iENVSIDE_BOTH selects only a key precisely at a given time.
            self.Find(time, lx.symbol.iENVSIDE_BOTH)
        except LookupError:
            return False
        return True

    def GetValueAuto(self, negative=False):
        """ Gets key value. Value Type and Value Broken sensitive.

        It will return a 1 or 2 element list, depending whether value on key is broken.
        Will return int or float list elmenents depending on key type.
        SetIsInt needs to called prior to use this method to get proper value.
        """
        # TODO: Think about making separate code for handling
        # negative multiplication - in case it slows things down
        try:
            break_flags, value_side = self.GetBroken()
            broken_value = break_flags & lx.symbol.fKEYBREAK_VALUE

            if self.is_int:
                if negative:
                    multiplier = -1
                else:
                    multiplier = 1

                if broken_value:
                    try:
                        value_in = self.GetValueI(lx.symbol.iENVSIDE_IN) * multiplier
                        value_out = self.GetValueI(lx.symbol.iENVSIDE_OUT) * multiplier
                    # TODO: Exception type needed here
                    except:
                        return None
                    return [value_in, value_out]
                else:
                    """ If value is not broken it doesn't matter which side argument
                    will be passed to GetValueI. """
                    try:
                        value = self.GetValueI(lx.symbol.iENVSIDE_IN) * multiplier
                    # TODO: Exception type needed here
                    except:
                        return None
                    return [value]
            else:
                if negative:
                    multiplier = -1.0
                else:
                    multiplier = 1.0

                if broken_value:
                    try:
                        value_in = self.GetValueF(lx.symbol.iENVSIDE_IN) * multiplier
                        value_out = self.GetValueF(lx.symbol.iENVSIDE_OUT) * multiplier
                    # TODO: Exception type needed here
                    except:
                        return None
                    return [value_in, value_out]
                else:
                    """ If value is not broken it doesn't matter which side argument
                    will be passed to GetValueF. """
                    try:
                        value = self.GetValueF(lx.symbol.iENVSIDE_IN) * multiplier
                    # TODO: Exception type needed here
                    except:
                        return None
                    return [value]
        except:
            lx.out(traceback.format_exc())
            raise

    def GetDataPack(self, negative=False):
        """ Gets all single keyframe properties and stores them as DataPack.
        """
        try:
            # TODO: Decide what the method should do if any of queries fail - should it return with fail?
            # TODO: Could use GetValueAuto method for getting values???
            data_pack = KeyframeDataPack()

            # Make sure to set is_int flat to indicate the type of keyframe value
            data_pack._is_int = self.is_int

            data_pack.time = self.GetTime()
            # Flags are bits so i need to do bit AND with a symbol which is essentialy a bit filter.
            # Sides flag should only be useful when value is broken - and it describes which side of the key (in/out)
            # has an effect on the key at its time.
            # For me, it always shows "IN" side as active - value of int 1
            # lx.symbol.iENVSIDE_IN
            #
            # NOTE: break_flags doesn't need to be stored in data pack
            #
            # TODO: I should not need empty flag - simply if anything bad happens get data pack should return false
            break_flags, data_pack.value_side = self.GetBroken()

            data_pack.broken_value = break_flags & lx.symbol.fKEYBREAK_VALUE
            data_pack.broken_slope = break_flags & lx.symbol.fKEYBREAK_SLOPE
            data_pack.broken_weight = break_flags & lx.symbol.fKEYBREAK_WEIGHT

            # Pull keyframe value based on the is_int flag
            # If value is not broken it does not matter which side will be passed
            # to GetValue as argument. I'm getting IN value by default
            # and getting OUT value if the value is broken.
            if not self.is_int:
                if negative:
                    multiplier = -1.0
                else:
                    multiplier = 1.0
                try:
                    data_pack.f_value_in = self.GetValueF(lx.symbol.iENVSIDE_IN) * multiplier
                except RuntimeError:
                    return False  # TODO: Check return code here, perhaps should be None or RS_ERR? Maybe it should continue?

                if data_pack.broken_value:
                    data_pack.f_value_out = self.GetValueF(lx.symbol.iENVSIDE_OUT) * multiplier
                else:
                    data_pack.f_value_out = 0.0
            else:
                if negative:
                    multiplier = -1
                else:
                    multiplier = 1
                try:
                    data_pack.i_value_in = self.GetValueI(lx.symbol.iENVSIDE_IN) * multiplier
                except RuntimeError:
                    return False  # TODO: Same as above^^^

                if data_pack.broken_value:
                    data_pack.i_value_out = self.GetValueI(lx.symbol.iENVSIDE_OUT) * multiplier
                else:
                    data_pack.i_value_out = 0

            # It's possible for these to fail!
            try:
                data_pack.slope_type_in, data_pack.manual_weight_in = self.GetSlopeType(lx.symbol.iENVSIDE_IN)
            except RuntimeError:
                pass
            try:
                data_pack.slope_type_out, data_pack.manual_weight_out = self.GetSlopeType(lx.symbol.iENVSIDE_OUT)
            except RuntimeError:
                pass
            try:
                data_pack.slope_in = self.GetSlope(lx.symbol.iENVSIDE_IN)
            except RuntimeError:
                pass
            try:
                data_pack.slope_out = self.GetSlope(lx.symbol.iENVSIDE_OUT)
            except RuntimeError:
                pass
            if negative:
                data_pack.slope_in *= -1.0
                data_pack.slope_out *= -1.0

            # If you read weight on auto weighted key then you get the auto weight value
            # This value seems to be consistent if the slope doesn't change.
            # So if the key has the slope set - the weight value set automatically should always be the same.
            # So when pasting a key - paste a slope and setting weight to auto should give the same result
            # as on source key with the same slope, time and value.

            # TODO: Optimization, maybe i should not read weight values at all
            # if auto weighting is applied to a key.
            try:
                data_pack.weight_in = self.GetWeight(lx.symbol.iENVSIDE_IN)
            except RuntimeError:
                pass
            try:
                data_pack.weight_out = self.GetWeight(lx.symbol.iENVSIDE_OUT)
            except RuntimeError:
                pass

            # When all properties are read the empty flag needs to set to false
            data_pack._empty = False

            return data_pack
        except:
            lx.out(traceback.format_exc())
            raise

    def SetFromDataPack(self, key_data_pack, time_offset=0.0, value_offset=0.0, value_multiplier=1.0):
        """ Sets a key on envelope reading its properties from data pack.
        """
        try:
            self.pack = KeyframeDataPack()
            self.pack = key_data_pack

            if self.pack._empty:
                return False

            key_time = self.pack.time + time_offset

            # Create either int or float key.
            # When setting broken value key the side controlling the key at its time
            # needs to be set last.
            if self.pack._is_int:
                i_value_in = int((float(self.pack.i_value_in) + value_offset) * value_multiplier)
                i_value_out = int((float(self.pack.i_value_out) + value_offset) * value_multiplier)

                self.AddI(key_time, i_value_in)

                if self.pack.broken_value:
                    if self.pack.value_side == lx.symbol.iENVSIDE_IN:
                        self.SetValueI(i_value_out, lx.symbol.iENVSIDE_OUT)
                        self.SetValueI(i_value_in, lx.symbol.iENVSIDE_IN)
                    elif self.pack.value_side == lx.symbol.iENVSIDE_OUT:
                        self.SetValueI(i_value_in, lx.symbol.iENVSIDE_IN)
                        self.SetValueI(i_value_out, lx.symbol.iENVSIDE_OUT)

            else:
                f_value_in = (self.pack.f_value_in + value_offset) * value_multiplier
                f_value_out = (self.pack.f_value_out + value_offset) * value_multiplier

                self.AddF(key_time, f_value_in)

                if self.pack.broken_value:
                    if self.pack.value_side == lx.symbol.iENVSIDE_IN:
                        self.SetValueF(f_value_out, lx.symbol.iENVSIDE_OUT)
                        self.SetValueF(f_value_in, lx.symbol.iENVSIDE_IN)
                    elif self.pack.value_side == lx.symbol.iENVSIDE_OUT:
                        self.SetValueF(f_value_in, lx.symbol.iENVSIDE_IN)
                        self.SetValueF(f_value_out, lx.symbol.iENVSIDE_OUT)

            # Slope has to be multiplied too to adjust handles to value change
            # ESPECIALLY when mirroring values (multiplier is -1.0)
            if self.pack.broken_slope:
                self.SetSlopeType(self.pack.slope_type_in, lx.symbol.iENVSIDE_IN)
                self.SetSlopeType(self.pack.slope_type_out, lx.symbol.iENVSIDE_OUT)
                self.SetSlope(self.pack.slope_in * value_multiplier, lx.symbol.iENVSIDE_IN)
                self.SetSlope(self.pack.slope_out * value_multiplier, lx.symbol.iENVSIDE_OUT)
            else:
                try:
                    self.SetSlopeType(self.pack.slope_type_in, lx.symbol.iENVSIDE_BOTH)
                    self.SetSlope(self.pack.slope_in * value_multiplier, lx.symbol.iENVSIDE_BOTH)
                except RuntimeError:
                    pass

            # For setting weights - ALWAYS set all possible weights, regardless
            # of broken weights flag. Apparently, modo allows for editing in and out weights
            # even when weights are not broken. So broken weights flag should not
            # be taken into account.
            # 0 argument is reset, when set to true the weight will be reset to automatic
            # which should be default when creating a key.
            # So I'm only setting weight when it's manual.
            # TODO: Setting weights back to auto is not really needed.
            # can be skipped. So Else statements below"""
            if self.pack.manual_weight_in:
                self.SetWeight(self.pack.weight_in, 0, lx.symbol.iENVSIDE_IN)
                auto_in = 0
            else:
                try:
                    self.SetWeight(self.pack.weight_in, 1, lx.symbol.iENVSIDE_IN)
                except RuntimeError:
                    pass
                finally:
                    auto_in = 1

            if self.pack.manual_weight_out:
                self.SetWeight(self.pack.weight_out, 0, lx.symbol.iENVSIDE_OUT)
            else:
                try:
                    self.SetWeight(self.pack.weight_out, 1, lx.symbol.iENVSIDE_OUT)
                except RuntimeError:
                    pass

            # TODO: THIS NEEDS TO BE RECHECKED
            # NOTE 24.03.2014 - irrelevant in 801
            ## Unify weights if they were not broken
            ## NOTE: That doesn't mean they have same weight values!
            # this needs to be done with a key.unify command
            # if not self.pack.broken_weight:
            #    self.SetWeight(self.pack.weight_in, auto_in, lx.symbol.iENVSIDE_BOTH)

            return True
        except:
            lx.out(traceback.format_exc())
            raise


class EnvelopeDataPack:
    """ Envelope data pack stores all envelope properties and keyframes.

    Properties:
    keyframes --- a list of keyframe data packs
    time_offset --- to shift keyframes in time
    value_offset --- to shift values in time
    value_multiplier --- to negate or scale values
    """

    # TODO: This class should include methods on getting/setting datapack.
    # Right now it's very bad design
    def __init__(self):
        self._empty = True
        self._is_int = False

        self.end_behavior_in = 0
        self.end_behavior_out = 0
        self.interpolation = 0
        self.keyframes = []


class EnvelopeUtils:
    """ Envelope object extension.
    """

    def __init__(self, envelope_object=None):
        """ Pass luxology envelope object.
        If you don't pass it you HAVE to either set envelope using set method
        or use New method to have a nice, new envelope to work with.

        chan_ident_string - this is temporary thing, it's required for setting channel interpolation to work.
                            that is because there's no method for doing this via SDK
        """
        if envelope_object:
            self.envelope = lx.object.Envelope(envelope_object)
        else:
            self.envelope = lx.object.Envelope()

        self.data_pack = EnvelopeDataPack()
        self.chan_ident_string = None

    def set(self, envelope_object):
        self.envelope = lx.object.Envelope(envelope_object)

    def SetChanIdentString(self, chan_ident):
        self.chan_ident_string = chan_ident

    def SetInterpolation(self, interpolation_type):
        """ Set envelope interpolation.
        Use interpolation integer lx.symbol as argument.
        Requires settings ChanIdentString FIRST!
        Also, doesn't change interpolation for integer (boolean) channels.
        """
        if self.chan_ident_string and not self.envelope.IsInt():
            lx.eval('!channel.interpolation type:%d channel:{%s}' % (interpolation_type, self.chan_ident_string))

    def KeyCount(self):
        """ Returns number of keys on an envelope.
        """
        key = KeyframeExtended(self.envelope.Enumerator())
        return key.Count()

    def TimeRange(self):
        """ Return envelope time range.
        Raise ValueError if there are no keys on envelope.
        """
        key = KeyframeExtended(self.envelope.Enumerator())
        return key.KeyTimeRange()

    def KeyExists(self, time):
        """ Check whether an envelope has a key at a given time.
        """
        # TODO: perhaps keyframe enumerator should be a class attribute
        # instead of local variable?
        key = KeyframeExtended(self.envelope.Enumerator())
        return key.KeyExists(time)

    def GetKeyAsDataPack(self, time, negative=False):
        """ Get only one key from the envelope.
        Key has to be exactly on a given time.
        """
        try:
            if not self.envelope.test():
                return False

            key = KeyframeExtended(self.envelope.Enumerator())
            try:
                key.Find(time, lx.symbol.iENVSIDE_BOTH)
            except LookupError:
                return None
            key_data_pack = KeyframeDataPack()
            key_data_pack = key.GetDataPack(negative)
            if not key_data_pack:
                return None
            return key_data_pack
        except:
            lx.out(traceback.format_exc())
            raise

    def SetKeyFromDataPack(self, key_data_pack, time_offset=0.0, value_offset=0.0, value_multiplier=1.0):
        try:
            if not self.envelope.test():
                return False

            key = KeyframeExtended(self.envelope.Enumerator())
            key.SetFromDataPack(key_data_pack, time_offset, value_offset, value_multiplier)
        except:
            lx.out(traceback.format_exc())
            raise

    def GetAsDataPack(self, negative=False):
        """ Get all envelope properties and keyframes
        and store them as EnvelopeDataPack.

        Args:
            negative -- allows for reading mirrored keyframe values.
            is_int -- set this to true if the envelope is of integer type.

        NOTE: Uses extended keyframe object (KeyframeExtended) to get/store
        keyframes via extra methods.
        """
        try:
            if not self.envelope.test():
                return False

            data_pack = EnvelopeDataPack()

            # Crucial to determine envelope type
            data_pack._is_int = self.envelope.IsInt()

            data_pack.interpolation = self.envelope.Interpolation()
            data_pack.end_behavior_in = self.envelope.EndBehavior(lx.symbol.iENVSIDE_IN)
            data_pack.end_behavior_out = self.envelope.EndBehavior(lx.symbol.iENVSIDE_OUT)

            key = KeyframeExtended(self.envelope.Enumerator())
            key.SetIsInt(
                self.envelope.IsInt())  # CRUCIAL, Keyframe needs to know its type of value for Get/Set Data Pack methods

            if not key.test():
                return data_pack

            process_keys = True
            key_data_pack = KeyframeDataPack()
            # Key processing section. Keys need to be enumerated.
            # If next key is not found LookupError exception is raised.
            try:
                key.First()
            except LookupError:
                process_keys = False

            while process_keys:
                key_data_pack = key.GetDataPack(negative)

                if key_data_pack:
                    data_pack.keyframes.append(key_data_pack)

                try:
                    key.Next()
                except LookupError:
                    process_keys = False
                    break

            data_pack._empty = False
            return data_pack
        except:
            lx.out(traceback.format_exc())
            raise

    def SetFromDataPack(self,
                        data_pack,
                        env_write_mode=iENV_WRITEMODE_REPLACE,
                        time_offset=0.0,
                        value_offset=0.0,
                        value_mutliplier=1.0):
        """ Sets envelope from data pack object.

        IMPORTANT: Using this method requires selecting an appropriate channel in scene first!
        That is because channel interpolation can currently be only set via command.
        For command to work the channel has to be selected in scene!
        """
        try:
            # target_envelope = lx.object.Envelope()
            self.data_pack = data_pack

            if not self.envelope.test():
                return False

            if self.data_pack._empty:
                return False

            # Set general envelope properties
            self.envelope.SetEndBehavior(self.data_pack.end_behavior_in, lx.symbol.iENVSIDE_IN)
            self.envelope.SetEndBehavior(self.data_pack.end_behavior_out, lx.symbol.iENVSIDE_OUT)
            self.SetInterpolation(self.data_pack.interpolation)
            # if self.chan_ident_string:
            #    lx.eval('channel.interpolation type:%d channel:{%s}' % (self.data_pack.interpolation, self.chan_ident_string))

            if env_write_mode == iENV_WRITEMODE_REPLACE:
                self.envelope.Clear()

            # Start key processing
            if self.data_pack.keyframes:
                key = KeyframeExtended(self.envelope.Enumerator())
                for key_data_pack in self.data_pack.keyframes:
                    key.SetFromDataPack(key_data_pack, time_offset, value_offset, value_mutliplier)

            return True
        except:
            lx.out(traceback.format_exc())
            raise

    def FilterStaticKeys(self, tolerance=0.00001):
        """ Delete keys that do not change envelope flow.
        Return number of deleted keys and a bool flag stating
        whether the result envelope is static or not.
        Can be used to optimize static envelopes that have many keys.
        """
        # TODO: Error code for exit?
        try:
            if not self.envelope.test():
                # throw an exception here!
                return None, False

            # Store that because if channel is int
            # we are not going to compare slopes.
            isInt = self.envelope.IsInt()

            key = KeyframeExtended(self.envelope.Enumerator())
            key.SetIsInt(
                self.envelope.IsInt())  # CRUCIAL, Keyframe needs to know its type of value for Get/Set Data Pack methods

            keys_deleted = 0
            is_static = False

            try:
                key.First()
            except LookupError:
                # No keys, nothing to do so it's all ok.
                # TODO: Is returning is_static=False correct here?
                return keys_deleted, is_static

            first_key_time = key.GetTime()
            process_keys = True

            while process_keys:
                # 1ST KEY.
                # key1_time will be used to reset filtering to a specific key
                # with Find method.
                key1_values = key.GetValueAuto()
                key1_time = key.GetTime()
                if not isInt:
                    key1_out_slope = key.GetSlope(lx.symbol.iENVSIDE_OUT)

                # Grab Out key value.
                key1_val = key1_values[len(key1_values) - 1]

                # Test values of 2 next keys.
                # They have to be the same as first key for filtering to proceed.

                # 2ND KEY.
                try:
                    key.Next()
                except LookupError:
                    process_keys = False
                    # if this is the first env key then the envelope is static
                    if key1_time == first_key_time:
                        is_static = True
                    break
                key2_values = key.GetValueAuto()
                key2_time = key.GetTime()
                if not isInt:
                    key2_in_slope = key.GetSlope(lx.symbol.iENVSIDE_IN)
                    key2_out_slope = key.GetSlope(lx.symbol.iENVSIDE_OUT)

                # If key2 has broken value - don't proceed.
                # Set it as new first key and start loop again.
                if len(key2_values) > 1:
                    continue

                # Grab key2 value.
                key2_val = key2_values[0]

                # Different comparison for floats and integers.
                if key.is_int:
                    # For integer channels compare key values.
                    # If key2 has different value then key1 don't even bother.
                    # Set it as new first key by continuing the loop from the start.
                    if key1_val != key2_val:
                        continue
                else:
                    # For floats compare both values and slopes.
                    if abs(key1_val - key2_val) > tolerance:
                        continue
                    # Check the slope between 1st and 2nd key
                    # It has to be flat between keys of a float channel.
                    # Apparently, when first key OUT slope is parallel to 2nd key's
                    # IN slope their values are the same.
                    # If slope is not flat even if keys have the same value they are not static
                    # since curve between them is not a straight line.
                    if abs(key1_out_slope - key2_in_slope) > tolerance:
                        continue

                # 3RD KEY
                try:
                    key.Next()
                except LookupError:
                    # Two first keys are equal and third one doesn't exist.
                    # If first key is the first key on envelope then
                    # that means that there are only 2 keys left on envelope.
                    # That means that envelope is static now.

                    # LEGACY: Delete the last one so there's only 1 key left.
                    if key1_time == first_key_time:
                        is_static = True
                        # lx.out('envelope is static')
                        # key.Last()
                        # key.Delete()
                        # keys_deleted += 1
                    process_keys = False
                    break

                key3_values = key.GetValueAuto()
                key3_time = key.GetTime()
                # Key3 can be broken but we're going to get in value only.
                key3_val = key3_values[0]
                if not isInt:
                    key3_in_slope = key.GetSlope(lx.symbol.iENVSIDE_IN)

                if key.is_int:
                    # Int channel.
                    # If Key3 value is different then Key1 dont' bother again.
                    # Start loop again, this time key3 will become new key1.
                    if key1_val != key2_val:
                        continue
                else:
                    # Check values and slopes between 2nd and 3rd key on float channels.
                    if abs(key2_val - key3_val) > tolerance:
                        continue
                    if abs(key2_out_slope - key3_in_slope) > tolerance:
                        continue

                # Now I have 3 keys of either the same value (int channels)
                # or flat slope between keys (float channels).
                # Delete the middle key and go back to the first key to start
                # filtering again.

                try:
                    key.Previous()
                except LookupError:
                    process_keys = False
                    break
                key.Delete()
                keys_deleted += 1

                # Setting a key to start loop from again is done with Find method.
                # Find will find a key at a given time if it exists.
                # Passing iENVSIDE_BOTH makes Find work only if it can find a key
                # at the exact given time.
                try:
                    key.Find(key1_time, lx.symbol.iENVSIDE_BOTH)
                except LookupError:
                    key.First()

            return keys_deleted, is_static
        except:
            lx.out(traceback.format_exc())
            raise
