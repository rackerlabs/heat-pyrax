# Copyright 2010 Jacob Kaplan-Moss

# Copyright 2011 OpenStack LLC.
# Copyright 2012 Rackspace

# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Base utilities to build API operation managers and objects on top of.
"""

import pyrax.utils as utils


class BaseResource(object):
    """
    A resource represents a particular instance of an object (server, flavor,
    etc). This is pretty much just a bag for attributes.

    :param manager: Manager object
    :param info: dictionary representing resource attributes
    :param loaded: prevent lazy-loading if set to True
    """
    HUMAN_ID = False
    NAME_ATTR = "name"

    def __init__(self, manager, info, loaded=False):
        self.manager = manager
        self._info = info
        self._add_details(info)
        self._loaded = loaded

        # NOTE(sirp): ensure `id` is already present because if it isn't we'll
        # enter an infinite loop of __getattr__ -> get -> __init__ ->
        # __getattr__ -> ...
        if "id" in self.__dict__ and len(str(self.id)) == 36:
            self.manager.write_to_completion_cache("uuid", self.id)

        human_id = self.human_id
        if human_id:
            self.manager.write_to_completion_cache("human_id", human_id)


    @property
    def human_id(self):
        """Subclasses may override this provide a pretty ID which can be used
        for bash completion.
        """
        if self.NAME_ATTR in self.__dict__ and self.HUMAN_ID:
            return utils.slugify(getattr(self, self.NAME_ATTR))
        return None


    def _add_details(self, info):
        for (key, val) in info.iteritems():
            try:
                setattr(self, key, val)
            except AttributeError:
                # In this case we already defined the attribute on the class
                pass


    def __getattr__(self, key):
        if key not in self.__dict__:
            #NOTE(bcwaldon): disallow lazy-loading if already loaded once
            if not self.loaded:
                self.get()
                return self.__getattr__(key)
            raise AttributeError(key)
        else:
            return self.__dict__[key]


    def __repr__(self):
        reprkeys = sorted(key for key in self.__dict__.keys()
               if (key[0] != "_") and (key != "manager"))
        info = ", ".join("%s=%s" % (key, getattr(self, key)) for key in reprkeys)
        return "<%s %s>" % (self.__class__.__name__, info)


    def get(self):
        # set 'loaded' first ... so if we have to bail, we know we tried.
        self.loaded = True
        if not hasattr(self.manager, "get"):
            return
        new = self.manager.get(self.id)
        if new:
            self._add_details(new._info)


    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if hasattr(self, "id") and hasattr(other, "id"):
            return self.id == other.id
        return self._info == other._info

 
    def reload(self):
        """
        Since resource objects are essentially snapshots of the entity they
        represent at the time they are created, they do not update as the
        entity updates. For example, the 'status' attribute can change, but
        the instance's value for 'status' will not. This method will refresh
        the instance with the current state of the underlying entity.
        """
        new_obj = self.manager.api.get(self.id)
        self._add_details(new_obj._info)


    def _get_loaded(self):
        return self._loaded

    def _set_loaded(self, val):
        self._loaded = val

    loaded = property(_get_loaded, _set_loaded)