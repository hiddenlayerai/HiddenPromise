### Minified version of https://github.com/vnmabus/rdata

import gzip, bz2, lzma, sys, enum, struct, zlib
from collections.abc import Sequence

magic_dict = {
    bz2.BZ2Decompressor().decompress: b"\x42\x5a\x68",
    gzip.decompress: b"\x1f\x8b",
    lzma.decompress: b"\xFD7zXZ\x00",
    zlib.decompress: b"x\x9c\x9dW"
}

class STREAM_TYPE(enum.Enum):
    ASCII = 1
    BINARY = 2
    XDR = 3

format_dict = {
    STREAM_TYPE.XDR: b"X\n",
    STREAM_TYPE.ASCII: b"A\n",
    STREAM_TYPE.BINARY: b"B\n",
}

def get_decompression(data):
    for decompression_func, magic in magic_dict.items():
        if data[:len(magic)] == magic:
            return decompression_func
    return None

def rdata_format(data):
    for format_type, magic in format_dict.items():
        if data[:len(magic)] == magic:
            return format_type
    return None

def _str_internal(obj, indent, used_references = None):

    if used_references is None:
        used_references = set()

    small_indent = indent + 2
    big_indent = indent + 4

    indent_spaces = " " * indent
    small_indent_spaces = " " * small_indent
    big_indent_spaces = " " * big_indent

    string = ""
    
    if isinstance(obj, list):
        string += f"{indent_spaces}[\n"
        for elem in obj:
            string += _str_internal(
                elem,
                big_indent,
                used_references.copy(),
            )
        string += f"{indent_spaces}]\n"

        return string

    string += f"{indent_spaces}{obj.info.type}\n"

    if obj.tag:
        tag_string = _str_internal(
            obj.tag,
            big_indent,
            used_references.copy(),
        )
        string += f"{small_indent_spaces}tag:\n{tag_string}\n"

    if obj.info.reference:
        assert obj.referenced_object
        reference_string = (
            f"{big_indent_spaces}..."
            if obj.info.reference in used_references
            else _str_internal(
                obj.referenced_object,
                indent + 4, used_references.copy())
        )
        string += (
            f"{small_indent_spaces}reference: "
            f"{obj.info.reference}\n{reference_string}\n"
        )

    string += f"{small_indent_spaces}value:\n"

    if isinstance(obj.value, list) and len(obj.value) > 0 and type(obj.value[0]) != RObject:
        string += big_indent_spaces
        string += f"{obj.value}\n"
    elif isinstance(obj.value, RObject):
        string += _str_internal(
            obj.value,
            big_indent,
            used_references.copy(),
        )
    elif isinstance(obj.value, (tuple, list)):
        for elem in obj.value:
            string += _str_internal(
                elem,
                big_indent,
                used_references.copy(),
            )
    else:
        string += f"{big_indent_spaces}{obj.value}\n"

    if obj.attributes:
        attr_string = _str_internal(
            obj.attributes,
            big_indent,
            used_references.copy(),
        )
        string += f"{small_indent_spaces}attributes:\n{attr_string}\n"

    return string

class RObjectType(enum.Enum):
    """Type of a R object."""

    NIL = 0  # NULL
    SYM = 1  # symbols
    LIST = 2  # pairlists
    CLO = 3  # closures
    ENV = 4  # environments
    PROM = 5  # promises
    LANG = 6  # language objects
    SPECIAL = 7  # special functions
    BUILTIN = 8  # builtin functions
    CHAR = 9  # internal character strings
    LGL = 10  # logical vectors
    INT = 13  # integer vectors
    REAL = 14  # numeric vectors
    CPLX = 15  # complex vectors
    STR = 16  # character vectors
    DOT = 17  # dot-dot-dot object
    ANY = 18  # make “any” args work
    VEC = 19  # list (generic vector)
    EXPR = 20  # expression vector
    BCODE = 21  # byte code
    EXTPTR = 22  # external pointer
    WEAKREF = 23  # weak reference
    RAW = 24  # raw vector
    S4 = 25  # S4 classes not of simple type
    ALTREP = 238  # Alternative representations
    ATTRLIST = 239  # Bytecode attribute
    ATTRLANG = 240  # Bytecode attribute
    BASEENV = 241  # Base environment
    EMPTYENV = 242  # Empty environment
    BCREPREF = 243  # Bytecode repetition reference
    BCREPDEF = 244  # Bytecode repetition definition
    PERSISTSXP = 247 # call function hook
    NAMESPACESXP = 249 # Namepace Lookup
    MISSINGARG = 251  # Missinf argument
    UNBOUNDVALUE = 252 # unbound value
    GLOBALENV = 253  # Global environment
    NILVALUE = 254  # NIL value
    REF = 255  # Reference

BYTECODE_SPECIAL_SET = [
    RObjectType.BCODE,
    RObjectType.BCREPREF,
    RObjectType.BCREPDEF,
    RObjectType.LANG,
    RObjectType.LIST,
    RObjectType.ATTRLANG,
    RObjectType.ATTRLIST,
]

class RVersions:
    def __init__(self, format, serialized, minimum):
        self.format = format
        self.serialized = serialized
        self.minimum = minimum

class RExtraInfo:
    def __init__(self, encoding):
        self.encoding = encoding

class RObjectInfo:
    def __init__(self, type, object, attributes, tag, gp, reference):
        self.type = type
        self.object = object
        self.attributes = attributes
        self.tag = tag
        self.gp = gp
        self.reference = reference

class EnvironmentValue:
    def __init__(self, locked, enclosure, frame, hash_table):
        self.locked = locked
        self.enclosure = enclosure
        self.frame = frame
        self.hash_table = hash_table

class RObject:
    def __init__(self, info, value, attributes, tag, referenced_object):
        self.info = info
        self.value = value
        self.attributes = attributes
        self.tag = tag
        self.referenced_object = referenced_object

class RData:
    def __init__(self, versions, extra, object):
        self.versions = versions
        self.extra = extra
        self.object = object

    def __str__(self):
        return (
            "RData(\n"
            f"  versions: {self.versions}\n"
            f"  extra: {self.extra}\n"
            f"  object: \n{_str_internal(self.object, indent=4)}\n"
            ")\n"
        )
    
def bits(data: int, start: int, stop: int) -> int:
    """Read bits [start, stop) of an integer."""
    count = stop - start
    mask = ((1 << count) - 1) << start

    bitvalue = data & mask
    return bitvalue >> start

def parse_r_object_info(info_int: int) -> RObjectInfo:
    """Parse the internal information of an object."""
    type_exp = RObjectType(bits(info_int, 0, 8))

    reference = 0

    if is_special_r_object_type(type_exp):
        object_flag = False
        attributes = False
        tag = False
        gp = 0
    else:
        object_flag = bool(bits(info_int, 8, 9))
        attributes = bool(bits(info_int, 9, 10))
        tag = bool(bits(info_int, 10, 11))
        gp = bits(info_int, 12, 28)

    if type_exp == RObjectType.REF:
        reference = bits(info_int, 8, 32)

    return RObjectInfo(
        type=type_exp,
        object=object_flag,
        attributes=attributes,
        tag=tag,
        gp=gp,
        reference=reference,
    )

def is_special_r_object_type(r_object_type: RObjectType) -> bool:
    """Check if a R type has a different serialization than the usual one."""
    return (
        r_object_type is RObjectType.NILVALUE
        or r_object_type is RObjectType.REF
    )

class Parser:
    def __init__(self, data):
        decompression_func = get_decompression(data)
        if decompression_func != None:
            data = decompression_func(data)

        if rdata_format(data) != STREAM_TYPE.XDR:
            raise Exception("Only XDR Supported")
        
        self.data = data
        self.cur = 0

    def parse(self):
        versions = self.parse_versions()
        extra_info = self.parse_extra_info(versions)
        obj = self.parse_R_object()

        return RData(versions, extra_info, obj)
    
    def read_bytes(self, to_read):
        if self.cur >= len(self.data):
            print("EOF")
            raise Exception("end of file")
        data = self.data[self.cur:self.cur+to_read]
        self.cur += to_read
        return data
    
    def parse_int(self, size=4):
        return int.from_bytes(self.read_bytes(size), byteorder='big')
    
    def parse_real(self, size=8):
        return struct.unpack('>d', self.read_bytes(size))[0]
    
    def parse_string(self, length):
        return self.read_bytes(length)
    
    def parse_bool(self):
        return bool(self.parse_int())

    def parse_nullable_int_array(self):
        length = self.parse_int()
        return [self.parse_int() for i in range(length)]
    
    def parse_nullable_bool_array(self):
        return [bool(i) for i in self.parse_nullable_int_array()]
    
    def parse_double_array(self):
        length = self.parse_int()
        return [self.parse_real() for i in range(length)]
    
    def parse_complex_array(self):
        return self.parse_double_array()
    
    def parse_versions(self):
        self.read_bytes(2)
        format_version = self.parse_int()
        r_version = self.parse_int()
        minimum_r_version = self.parse_int()

        return RVersions(format_version, r_version, minimum_r_version)
    
    def parse_extra_info(self, versions):
        
        encoding = None

        minimum_version_with_encoding = 3
        if versions.format >= minimum_version_with_encoding:
            encoding_len = self.parse_int()
            encoding = self.parse_string(encoding_len)

        return RExtraInfo(encoding)
    
    def _parse_bytecode_constant(self, reference_list, bytecode_rep_list=None):

        obj_type = self.parse_int()

        return self.parse_R_object(
            reference_list,
            bytecode_rep_list,
            info_int=obj_type,
        )
    
    def _parse_bytecode(self, reference_list, bytecode_rep_list=None):

        if bytecode_rep_list is None:
            n_repeated = self.parse_int()

        code = self.parse_R_object(reference_list, bytecode_rep_list)

        if bytecode_rep_list is None:
            bytecode_rep_list = [None] * n_repeated

        n_constants = self.parse_int()
        constants = [
            self._parse_bytecode_constant(
                reference_list,
                bytecode_rep_list,
            )
            for _ in range(n_constants)
        ]

        return (code, constants)
    
    def parse_R_object(self, reference_list=None, bytecode_rep_list=None, info_int=None):

        if reference_list is None:
            reference_list = []

        original_info_int = info_int
        if (
            info_int is not None
            and RObjectType(info_int) in BYTECODE_SPECIAL_SET
        ):
            info = parse_r_object_info(info_int)
            info.tag = info.type not in {
                RObjectType.BCREPREF,
                RObjectType.BCODE,
            }
        else:
            info_int = self.parse_int()
            info = parse_r_object_info(info_int)

        tag = None
        attributes = None
        referenced_object = None

        bytecode_rep_position = -1
        tag_read = False
        attributes_read = False
        add_reference = False

        result = None

        if info.type == RObjectType.BCREPDEF:
            assert bytecode_rep_list
            bytecode_rep_position = self.parse_int()
            info.type = RObjectType(self.parse_int())

        if info.type == RObjectType.NIL:
            value = None

        elif info.type == RObjectType.SYM:
            # Read Char
            value = self.parse_R_object(reference_list, bytecode_rep_list)
            # Symbols can be referenced
            add_reference = True

        elif info.type in {
            RObjectType.LIST,
            RObjectType.LANG,
            RObjectType.CLO,
            RObjectType.PROM,
            RObjectType.DOT,
            RObjectType.ATTRLANG,
        }:
            if info.type is RObjectType.ATTRLANG:
                info.type = RObjectType.LANG
                info.attributes = True

            tag = None
            if info.attributes:
                attributes = self.parse_R_object(
                    reference_list,
                    bytecode_rep_list,
                )
                attributes_read = True

            if info.tag:
                tag = self.parse_R_object(reference_list, bytecode_rep_list)
                tag_read = True

            # Read CAR and CDR
            car = self.parse_R_object(
                reference_list,
                bytecode_rep_list,
                info_int=(
                    None if original_info_int is None
                    else self.parse_int()
                ),
            )
            cdr = self.parse_R_object(
                reference_list,
                bytecode_rep_list,
                info_int=(
                    None if original_info_int is None
                    else self.parse_int()
                ),
            )
            value = (car, cdr)

        elif info.type == RObjectType.ENV:
            info.object = True

            result = RObject(
                info=info,
                tag=tag,
                attributes=attributes,
                value=None,
                referenced_object=referenced_object,
            )

            reference_list.append(result)

            locked = self.parse_bool()
            enclosure = self.parse_R_object(reference_list, bytecode_rep_list)
            frame = self.parse_R_object(reference_list, bytecode_rep_list)
            hash_table = self.parse_R_object(reference_list, bytecode_rep_list)
            attributes = self.parse_R_object(reference_list, bytecode_rep_list)

            value = EnvironmentValue(
                locked=locked,
                enclosure=enclosure,
                frame=frame,
                hash_table=hash_table,
            )

        elif info.type in {RObjectType.SPECIAL, RObjectType.BUILTIN}:
            length = self.parse_int()
            if length > 0:
                value = self.parse_string(length=length)

        elif info.type == RObjectType.CHAR:
            length = self.parse_int()
            if length > 0:
                value = self.parse_string(length=length)
            elif length == 0:
                value = b""
            elif length == -1:
                value = None
            else:
                msg = f"Length of CHAR cannot be {length}"
                raise NotImplementedError(msg)

        elif info.type == RObjectType.LGL:
            value = self.parse_nullable_bool_array()

        elif info.type == RObjectType.INT:
            value = self.parse_nullable_int_array()

        elif info.type == RObjectType.REAL:
            value = self.parse_double_array()

        elif info.type == RObjectType.CPLX:
            value = self.parse_complex_array()

        elif info.type in {
            RObjectType.STR,
            RObjectType.VEC,
            RObjectType.EXPR
        }:
            length = self.parse_int()

            value = [None] * length

            for i in range(length):
                value[i] = self.parse_R_object(
                    reference_list, bytecode_rep_list)

        elif info.type == RObjectType.BCODE:
            value = self._parse_bytecode(reference_list, bytecode_rep_list)
            tag_read = True

        elif info.type == RObjectType.EXTPTR:

            result = RObject(
                info=info,
                tag=tag,
                attributes=attributes,
                value=None,
                referenced_object=referenced_object,
            )

            reference_list.append(result)
            protected = self.parse_R_object(
                reference_list,
                bytecode_rep_list,
            )
            extptr_tag = self.parse_R_object(
                reference_list,
                bytecode_rep_list,
            )

            value = (protected, extptr_tag)

        elif info.type == RObjectType.S4:
            value = None

        elif info.type == RObjectType.ALTREP:
            altrep_info = self.parse_R_object(
                reference_list,
                bytecode_rep_list,
            )
            altrep_state = self.parse_R_object(
                reference_list,
                bytecode_rep_list,
            )
            altrep_attr = self.parse_R_object(
                reference_list,
                bytecode_rep_list,
            )

            value = (altrep_info, altrep_state, altrep_attr)

        elif info.type == RObjectType.BASEENV:
            value = None

        elif info.type == RObjectType.EMPTYENV:
            value = None

        elif info.type == RObjectType.BCREPREF:
            assert bytecode_rep_list
            position = self.parse_int()
            result = bytecode_rep_list[position]
            assert result
            return result

        elif info.type == RObjectType.MISSINGARG:
            value = None

        elif info.type == RObjectType.GLOBALENV:
            value = None

        elif info.type == RObjectType.UNBOUNDVALUE:
            value = None

        elif info.type == RObjectType.NILVALUE:
            value = None

        elif info.type == RObjectType.REF:
            value = None
            # Index is 1-based
            referenced_object = reference_list[info.reference - 1]

        elif info.type == RObjectType.NAMESPACESXP or info.type == RObjectType.PERSISTSXP:
            add_reference = True

            if self.parse_int() != 0:
                raise Exception("names in persistent strings are not supported yet")

            length = self.parse_int()

            value = [None] * length

            for i in range(length):
                value[i] = self.parse_R_object(
                    reference_list, bytecode_rep_list)


        else:
            msg = f"Type {info.type} not implemented"
            raise NotImplementedError(msg)

        if info.attributes and not attributes_read:
            attributes = self.parse_R_object(reference_list, bytecode_rep_list)

        if result is None:
            result = RObject(
                info=info,
                tag=tag,
                attributes=attributes,
                value=value,
                referenced_object=referenced_object,
            )
        else:
            result.info = info
            result.attributes = attributes
            result.value = value
            result.referenced_object = referenced_object

        if add_reference:
            reference_list.append(result)

        if bytecode_rep_position >= 0:
            assert bytecode_rep_list
            bytecode_rep_list[bytecode_rep_position] = result

        return result

if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    parsed = Parser(data).parse()
    print(parsed)