# add output to every datalog relation!
# assume every file is valid datalog file

from optparse import OptionParser
import os
import re

def get_rule_name(rule_decl):
    rule_name = re.findall(r"\.decl(.+)\(", rule_decl)[0]
    return rule_name

def get_comp_name(comp_decl):
    name = re.findall(r"\.comp(.+) *\{", comp_decl)[0]
    return name

class DatalogLib:
    '''
    create a datalog lib from a folder
    '''
    def __init__(self, name, include_path, override=True): 
        self.name = name
        self.include_path = include_path
        self.override = override
        self.rule_decls = []
        self.file_data = {}
        self.type_decls = []
        # map from comp name to list of rule decl
        self.comp_decls = {}
        self.inits = []
        self.inlines = []
    
    def add_dir(self, filedir, recurisve=False):
        entries = os.listdir(filedir)
        for entry in entries:
            if entry.endswith(".dl"):
                self.add_file(filedir+"/"+entry)
            elif os.path.isdir(filedir+"/"+entry):
                if recurisve:
                    self.add_dir(filedir+"/"+entry)
    
    def add_file(self, filename):
        with open(filename, "r+") as f:
            lines = list(f)
            newlines = []
            need_insert_name = None
            current_rule = ""
            comp_name = None
            comp_rules = []
            for line in lines:
                # check if a rule is complete
                if need_insert_name is not None:
                    # check if current position is still in decl body
                    if (line.find(":") != -1) and (line.find(":-") == -1) and (line.find(".decl") == -1):
                        current_rule = current_rule + line
                    # already there
                    elif line.strip().startswith(".output") or line.startswith(".input"):
                        self.rule_decls.append(current_rule)
                        need_insert_name = None
                    else:
                        newlines.append(".output "+need_insert_name+"\n")
                        # check if we are now inside a comp
                        if comp_name is None:
                            self.rule_decls.append(current_rule)
                        else:
                            comp_rules.append(current_rule)
                        need_insert_name = None
                        current_rule = None
                    # newlines.append(".output"+get_rule_name(line)+"\n")
                if line.strip().startswith(".type"):
                    self.type_decls.append(line)
                if line.strip().startswith(".init"):
                    self.inits.append(line)
                # find comp
                if line.strip().startswith(".comp"):
                    comp_name = get_comp_name(line)
                if line.strip().endswith("}"):
                    self.comp_decls[comp_name] = comp_rules
                    comp_rules = []
                    comp_name = None
                # find decl
                if line.strip().startswith(".decl"):
                    # handle inlines else where
                    if line.find("inline") == -1:
                        need_insert_name = get_rule_name(line)
                        current_rule = line
                newlines.append(line)
            self.file_data[filename] = "".join(newlines)
            # # find all inlines def
            # inline_decls = re.findall(r"\.decl .+ inline", self.file_data[filename])
            # for i_decl in inline_decls:
            #     i_name = get_rule_name(i_decl)


    def rewrite_rule(self):
        if self.override:
            for fname,data in self.file_data.items():
                with open(fname, "w+") as f:
                    f.seek(0)
                    f.write(data)
        # customize output dir not implement
    
    def generate_inlcude(self):
        with open(self.include_path, "w+") as f:
            for decl in self.type_decls:
                f.write(decl)
            for i in self.inits:
                f.write(i)
            for name, rules in self.comp_decls.items():
                f.write(".comp " + name + " {\n")
                for r in rules:
                    f.write(r)
                    f.write(".input " + get_rule_name(r) + "\n")
                f.write("}\n")
            for decl in self.rule_decls:
                f.write(decl)
                f.write(".input " + get_rule_name(decl) + "\n")


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-N", "--name", dest="libname")
    parser.add_option("-I", "--output-include", help="output path for include dl file", dest="include_dir")
    parser.add_option("-D", "--dir", action="append", dest="dirs", help="add .output to EVERY relation in a datalog file dir")
    (options, args) = parser.parse_args()
    if options.libname is not None:
        if options.include_dir is None:
            options.include_dir = options.libname + ".dl"
        lib = DatalogLib(options.libname, options.include_dir)
        if options.dirs is not None:
            for d in options.dirs:
                lib.add_dir(d)
            lib.rewrite_rule()
            lib.generate_inlcude()
    print("plz check the .init line in your generated file, something optional inside include may also be copied here!")
