from buildingmotif.database.utils import (
    _custom_json_deserializer,
    _custom_json_serializer,
)


def test_custom_json_serde():
    def roundtrip(inp):
        return _custom_json_deserializer(_custom_json_serializer(inp))

    x = []
    assert x == roundtrip(x)
    x = [1]
    assert x == roundtrip(x)
    x = [1, 2]
    assert x == roundtrip(x)
    x = {"a": "b"}
    assert x == roundtrip(x)
    x = {"a": "b", "c": "d"}
    assert x == roundtrip(x)
    x = ["a", "b", "c", "d"]
    assert x == roundtrip(x)
    x = ["ab", "cd"]
    assert x == roundtrip(x)
    x = ["abc", "def"]
    assert x == roundtrip(x)
