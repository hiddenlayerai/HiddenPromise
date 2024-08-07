from hiddenpromise.parser import Parser

data = open("../example_files/pwned.rds", "rb").read()
parsed = Parser(data).parse()
print(parsed)