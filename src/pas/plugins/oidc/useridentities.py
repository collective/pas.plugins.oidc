from persistent import Persistent
from persistent.dict import PersistentDict
from Products.PluggableAuthService.UserPropertySheet import UserPropertySheet

import uuid


class UserIdentity(PersistentDict):
    def __init__(self, result):
        super().__init__()
        self["provider_name"] = result.provider.name
        self.update(result.user.to_dict())

    # @property
    # def credentials(self):
    #     cfg = authomatic_cfg()
    #     return Credentials.deserialize(cfg, self.user["credentials"])

    # @credentials.setter
    # def credentials(self, credentials):
    #     self.data["credentials"] = credentials.serialize()


class UserIdentities(Persistent):
    def __init__(self, userid):
        self.userid = userid
        self._identities = PersistentDict()
        self._sheet = None

    # def update_userdata(self, result):
    #     self._sheet = None  # invalidate property sheet
    #     identity = self._identities[result.provider.name]
    #     identity.update(result.user.to_dict())

    @property
    def propertysheet(self):
        if self._sheet is not None:
            return self._sheet
        # build sheet from identities
        pdata = dict(id=self.userid)
        self._sheet = UserPropertySheet(**pdata)
        return self._sheet
