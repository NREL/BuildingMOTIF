```markdown
# Parsing Function Signatures and Usage

This document provides the function signatures and example usage of all subclasses of `Parser`.

## `string`
```
def __init__(self, s: str, type_name: TokenOrConstructor)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser = string("hello", Identifier)
result = parser("hello world")
print(result)  # Expected output: [TokenResult('hello', Identifier('hello'), 5)]
```

## `rest`
```
def __init__(self, type_name: TokenOrConstructor)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser = rest(Identifier)
result = parser("hello world")
print(result)  # Expected output: [TokenResult('hello world', Identifier('hello world'), 11)]
```

## `substring_n`
```
def __init__(self, length: int, type_name: TokenOrConstructor)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser = substring_n(5, Identifier)
result = parser("hello world")
print(result)  # Expected output: [TokenResult('hello', Identifier('hello'), 5)]
```

## `regex`
```
def __init__(self, r: str, type_name: TokenOrConstructor)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser = regex(r"\w+", Identifier)
result = parser("hello world")
print(result)  # Expected output: [TokenResult('hello', Identifier('hello'), 5)]
```

## `choice`
```
def __init__(self, *parsers: Parser)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser1 = string("hello", Identifier)
parser2 = string("hi", Identifier)
parser = choice(parser1, parser2)
result = parser("hi there")
print(result)  # Expected output: [TokenResult('hi', Identifier('hi'), 2)]
```

## `constant`
```
def __init__(self, type_name: Token)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser = constant(Identifier("constant"))
result = parser("anything")
print(result)  # Expected output: [TokenResult(None, Identifier('constant'), 0)]
```

## `abbreviations`
```
def __init__(self, patterns: dict)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
patterns = {"AHU": BRICK.Air_Handling_Unit, "FCU": BRICK.Fan_Coil_Unit}
parser = abbreviations(patterns)
result = parser("AHU sensor data")
print(result)  # Expected output: [TokenResult('AHU', Constant(BRICK.Air_Handling_Unit), 3)]
```

## `sequence`
```
def __init__(self, *parsers: Parser)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser1 = string("hello", Identifier)
parser2 = string(" ", Delimiter)
parser3 = string("world", Identifier)
parser = sequence(parser1, parser2, parser3)
result = parser("hello world")
print(result)  # Expected output: [TokenResult('hello', Identifier('hello'), 5), TokenResult(' ', Delimiter(' '), 1), TokenResult('world', Identifier('world'), 5)]
```

## `many`
```
def __init__(self, seq_parser: Parser)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
item_parser = string("a", Identifier)
parser = many(item_parser)
result = parser("aaaab")
print(result)  # Expected output: [TokenResult('a', Identifier('a'), 1), TokenResult('a', Identifier('a'), 1), TokenResult('a', Identifier('a'), 1), TokenResult('a', Identifier('a'), 1)]
```

## `maybe`
```
def __init__(self, parser: Parser)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser = maybe(string("hello", Identifier))
result = parser("world")
print(result)  # Expected output: [TokenResult(None, Null(), 0)]
```

## `until`
```
def __init__(self, parser: Parser, type_name: TokenOrConstructor)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
parser = until(string("stop", Identifier), Identifier)
result = parser("hello world stop")
print(result)  # Expected output: [TokenResult('hello world ', Identifier('hello world '), 12)]
```

## `extend_if_match`
```
def __init__(self, parser: Parser, type_name: Token)
def __call__(self, target: str) -> List[TokenResult]
```

### Example Usage
```python
base_parser = string("hello", Identifier)
parser = extend_if_match(base_parser, Constant("extra_type"))
result = parser("hello world")
print(result)  # Expected output: [TokenResult('hello', Identifier('hello'), 5), TokenResult(None, Constant('extra_type'), 0)]
```