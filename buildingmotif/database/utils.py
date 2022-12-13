import json

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


class JSONType(sa.types.TypeDecorator):
    """Custom JSON type that uses JSONB on Postgres and JSON on other dialects.
    This allows us to use our custom JSON serialization below *and* have the
    database enforce uniqueness on JSON-encoded dictionaries
    """

    impl = sa.JSON
    hashable = False
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            # Use the native JSON type.
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(sa.JSON())


# the custom ser/de handlers are to allow the database to ensure
# uniqueness of dependency bindings (see https://github.com/NREL/BuildingMOTIF/pull/113)
def _custom_json_serializer(obj):
    """
    Serializes dictionaries as a sorted list of key-value tuples. All
    other items are serialized as normal
    """
    if isinstance(obj, dict):
        # ensure dictionary has at least 1 pair
        if len(obj) == 0:
            obj[None] = None
        return json.dumps(sorted([(k, v) for k, v in obj.items()]))
    return json.dumps(obj)


def _custom_json_deserializer(inp):
    """
    Handles deserializing the objects serialied by _custom_json_serializer
    """
    obj = json.loads(inp)
    # return normal object if it is not a list
    if not isinstance(obj, list):
        return obj
    # if *all* of the items in the list are pairs,
    # then we deserialize as a dictionary
    if len(obj) > 0 and all(map(lambda x: isinstance(x, list) and len(x) == 2, obj)):
        return dict(obj)
    # ...otherwise return. It's just a normal list!
    return obj
