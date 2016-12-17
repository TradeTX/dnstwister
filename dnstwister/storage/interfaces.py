"""Storage implementations are expected to implement this interface."""
import zope.interface.verify


# pylint: disable=inherit-non-class
class IKeyValueDB(zope.interface.Interface):
    """Interface for a key-value storage."""
    def set(self, kind, key, value):
        """Set the value for kind:key.
        """

    # pylint: disable=arguments-differ
    def get(self, kind, key):
        """Get a value for kind + key or None."""

    def ikeys(self, kind):
        """Return an iterator of all keys, optionally filtered on kind."""

    def delete(self, kind, key):
        """Delete a key."""


def instance_valid(instance):
    """Check an instance correctly implements storage."""
    return zope.interface.verify.verifyObject(IKeyValueDB, instance)
