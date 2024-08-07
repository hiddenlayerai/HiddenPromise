from hiddenpromise.parser import Parser, RObjectType
from hiddenpromise.injector import get_addresses
import zlib, os, sys

def find_files(directory, extensions=('.rdx', '.rds')):
    found_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(extensions):
                found_files.append(os.path.join(root, file))
    return found_files

def check_rdb_rdx(path):
    rdx_data = open(path, "rb").read()
    rdx_parsed = Parser(rdx_data).parse()
    if rdx_parsed.object.info.type == RObjectType.VEC:
        print(path, "Type:", str(RObjectType.VEC))
        rdb_data = open(path.replace(".rdx", ".rdb"), "rb").read()

        addresses = get_addresses(rdx_parsed)

        for address in addresses:
            try:

                start = addresses[address]["offsets"][0]
                length = addresses[address]["offsets"][1]

                decompressed_rdb_data = zlib.decompress(rdb_data[start:start + length][4::])
                rdb_parsed = Parser(decompressed_rdb_data).parse()
                print("\t", address.decode(), addresses[address]["offsets"], "First Instruction:", rdb_parsed.object.info.type)

            except Exception as e:
                pass
    else:
        print(path, "Type:", str(rdx_parsed.object.info.type))

def check_first_opcode(path):
    if ".rdx" in path and os.path.exists(path.replace(".rdx", ".rdb")):
        check_rdb_rdx(path)
    else:
        rdx_data = open(path, "rb").read()
        rdx_parsed = Parser(rdx_data).parse()
        print(path, "Type:", str(rdx_parsed.object.info.type))

if __name__ == "__main__":
    found_files = find_files(sys.argv[1])
    for file in found_files:
        check_first_opcode(file)