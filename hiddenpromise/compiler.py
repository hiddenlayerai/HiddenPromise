from enum import Enum
import struct
import gzip

class TYPES(Enum):
    REFSXP            = 255
    NILVALUE_SXP      = 254
    GLOBALENV_SXP     = 253
    UNBOUNDVALUE_SXP  = 252
    MISSINGARG_SXP    = 251
    BASENAMESPACE_SXP = 250
    NAMESPACESXP      = 249
    PACKAGESXP        = 248
    PERSISTSXP        = 247
    CLASSREFSXP       = 246
    GENERICREFSXP     = 245
    BCREPDEF          = 244
    BCREPREF          = 243
    EMPTYENV_SXP	  = 242
    BASEENV_SXP	  	  = 241
    ATTRLANGSXP       = 240
    ATTRLISTSXP       = 239
    ALTREP_SXP	      = 238
    NILSXP	          = 0	#  /* nil = NULL */
    SYMSXP	          = 1	#  /* symbols */
    LISTSXP	          = 2	#  /* lists of dotted pairs */
    CLOSXP	          = 3	#  /* closures */
    ENVSXP	          = 4	#  /* environments */
    PROMSXP	          = 5	#  /* promises: [un]evaluated closure arguments */
    LANGSXP	          = 6	#  /* language constructs (special lists) */
    SPECIALSXP        = 7	#  /* special forms */
    BUILTINSXP        = 8	#  /* builtin non-special forms */
    CHARSXP	          = 9	#  /* "scalar" string type (internal only)*/
    LGLSXP	          = 10	#  /* logical vectors */
    INTSXP	          = 13	#  /* integer vectors */
    REALSXP	          = 14	#  /* real variables */
    CPLXSXP	          = 15	#  /* complex variables */
    STRSXP	          = 16	#  /* string vectors */
    DOTSXP	          = 17	#  /* dot-dot-dot object */
    ANYSXP	          = 18	#  /* make "any" args work. */
    VECSXP	          = 19	#  /* generic vectors */
    EXPRSXP	          = 20	#  /* expressions vectors */
    BCODESXP          = 21 #   /* byte code */
    EXTPTRSXP         = 22 #   /* external pointer */
    WEAKREFSXP        = 23 #   /* weak reference */
    RAWSXP            = 24 #   /* raw bytes */
    OBJSXP            = 25 #   /* object, non-vector  */
    S4SXP             = 25 #   /* same as OBJSXP, retained for back compatability */
    NEWSXP            = 30 #   /* fresh node created in new page */
    FREESXP           = 31 #   /* node released by GC */
    FUNSXP            = 99 #   /* Closure or Builtin or Special */


class Opcode:
    def __init__(self, ftype, levels, isobj, hasattr, hastag, value, falsey):
        self.ftype = ftype
        self.levels = levels
        self.isobj = isobj
        self.hasattr = hasattr
        self.hastag = hastag
        self.value = value
        self.falsey = falsey

    def get_flag(self):
        flag = self.ftype.value & 255
        flag |= (self.levels << 12)
        if self.isobj:
            flag |= (1 << 8)
        if self.hasattr:
            flag |= (1 << 9)
        if self.hastag:
            flag |= (1 << 10)
        return flag

class Compiler:
    def __init__(self):
        self.data = b''
        self.last = None

    def as_integer(self, value):
        return value.to_bytes(4, byteorder='big')

    def as_real(self, value):
        return struct.pack('>d', value)

    def build_header(self):
        self.data += b'X\n'
        self.data += self.as_integer(0x3)
        self.data += self.as_integer(0x40303)
        self.data += self.as_integer(0x30500)
        self.data += self.as_integer(0x5)
        self.data += b'UTF-8'
        
    def add_instruction(self, instruction):

        if instruction.falsey:
            self.last = instruction
            return
        
        ftype = instruction.ftype
        # print(ftype)

        if ftype == None:
            self.data += self.as_integer(instruction.value)
            return

        flags = instruction.get_flag()

        if ftype == TYPES.REFSXP:
            flags |= (((instruction.value + 1) << 8) | TYPES.REFSXP.value)
        
        self.data += self.as_integer(flags)

        if self.last != None:
            self.data += self.as_integer(self.last.value)
            self.last = None

        if ftype == TYPES.STRSXP or ftype == TYPES.BCREPREF or ftype == TYPES.VECSXP or ftype == TYPES.RAWSXP or ftype == TYPES.ENVSXP:
            self.data += self.as_integer(instruction.value)
        elif ftype == TYPES.BCODESXP:
            if instruction.value != None:
                self.data += self.as_integer(instruction.value)
        elif ftype == TYPES.INTSXP or ftype == TYPES.LGLSXP:
            if type(instruction.value) == int:
                self.data += self.as_integer(instruction.value)
                return
            self.data += self.as_integer(len(instruction.value))
            for i in instruction.value:
                self.data += self.as_integer(i)
        elif ftype == TYPES.NAMESPACESXP or ftype == TYPES.PACKAGESXP or ftype == TYPES.PERSISTSXP:
            self.data += self.as_integer(0)
            self.data += self.as_integer(instruction.value)
        elif ftype == TYPES.REALSXP:
            self.data += self.as_integer(len(instruction.value))
            for i in instruction.value:
                self.data += self.as_real(i)
        elif ftype == TYPES.CHARSXP:
            self.data += self.as_integer(len(instruction.value))
            self.data += instruction.value.encode('UTF-8')
        elif ftype == TYPES.BCREPDEF:
            self.data += self.as_integer(instruction.value[0])
            self.data += self.as_integer(instruction.value[1].value)
        elif ftype == TYPES.BUILTINSXP or ftype == TYPES.SPECIALSXP:
            self.data += self.as_integer(len(instruction.value))
            self.data += instruction.value.encode('UTF-8')
        elif ftype in [TYPES.CLOSXP, TYPES.BASENAMESPACE_SXP, TYPES.LISTSXP, TYPES.SYMSXP, TYPES.MISSINGARG_SXP, TYPES.NILVALUE_SXP, TYPES.LANGSXP, TYPES.NILSXP, TYPES.REFSXP, TYPES.GLOBALENV_SXP, TYPES.OBJSXP, TYPES.EXTPTRSXP, TYPES.DOTSXP, TYPES.PROMSXP, TYPES.ALTREP_SXP, TYPES.EMPTYENV_SXP, TYPES.BASEENV_SXP, TYPES.UNBOUNDVALUE_SXP]:
            pass
        else:
            raise Exception(ftype)


    def craft_file(instructions):
        c = Compiler()

        c.build_header()

        for instruction in instructions:
            c.add_instruction(instruction)

        return c.data