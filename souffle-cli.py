# a CLI tool can run/query a datalog(souffle) rule interactively

# Yihao Sun
# Syracuse 2020

import cmd
import os
import re
import random
import string
import shutil
import subprocess
from optparse import OptionParser

from datalog_as_lib import DatalogLib

SOUFFLE_COMMAND = 'souffle'
BASE_DIR = '.souffle'
CACHE_INCLUDE_FILE = 'include.dl'
INCLUDE_DIR = 'include'
FACTS_DIR = 'facts'
OUT_DIR = 'outs'
DL_DIR = "dl"
CACHE_DIR = "cache"

def random_str():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def is_valid_dl(line):
    '''
    check if a **LINE** is a valid datalog rule, this is very inprecies, not realy
    parsing is applied here, will move so something more precise in future
    '''
    line = line.strip()
    if line.startswith('.decl') and line.endswith(')'):
        return True
    elif line.startswith('.input') or line.startswith('.output'):
        return True
    elif line.startswith('.type'):
        return True
    elif line.endswith('.') and (line.find(':-') != -1):
        return True
    else:
        return False

class DatalogShell(cmd.Cmd):
    intro = '''
                         __        _  _          _                 _ 
                        (_  _    _|__|_ |  _    | \ _ _|_ _  |  _ (_|
                        __)(_)|_| |  |  | (/_   |_/(_| |_(_| | (_)__|



    This a datalog query repl, you can use souffle style datalog query like `foo(11,_,1) :- ....`
    or you can also use `.input ...` `.output ...` to read facts and see output of a rule.
    '''
    prompt = "\U0001f95e > "

    def __init__(self, output_dir, init_entry):
        super(DatalogShell, self).__init__()
        self.output_dir = output_dir
        self.is_binary_loaded = False
        self.cachefile = random_str() + '.dl'
        # create a include file for cache
        cache_include_path = '{}/{}/{}'.format(BASE_DIR, CACHE_DIR, CACHE_INCLUDE_FILE)
        include_path = '{}/{}'.format(BASE_DIR, INCLUDE_DIR)
        with open(cache_include_path, 'w+') as f:
            for i in os.listdir(include_path):
                f.write('#include "../{}/{}"\n'.format(INCLUDE_DIR, i))
        # create cache file 
        self.create_cache()
        self.run_souffle

    # def do_ddisasm(self, arg):
    #     '''
    #     ddisasm [file]: disasmembly a binary using ddisasm
    #     '''
    #     pass
    def create_cache(self):
        cache_file_path = '{}/{}/{}'.format(BASE_DIR, CACHE_DIR, self.cachefile)
        if os.path.exists(cache_file_path):
            os.remove(cache_file_path)
        with open(cache_file_path, 'w+') as f:
            f.write('#include "./{}"\n\n'.format(CACHE_INCLUDE_FILE))

    def do_compile(self, arg):
        '''
        compile current cache file
        '''
        cache_file_path = os.path.abspath(BASE_DIR+'/'+CACHE_DIR+'/'+self.cachefile)
        self.run_souffle(cache_file_path)

    def do_emacs(self, arg):
        '''
        open emacs and edit cache rule, make sure you have a GUI version of emacs installed
        '''
        cache_file_path = '{}/{}/{}'.format(BASE_DIR, CACHE_DIR, self.cachefile)
        subprocess.run(["emacs", cache_file_path])

    def do_exportdl(self, arg):
        '''
        export datalog rule history into some file
        '''
        cache_file_path = BASE_DIR+'/'+CACHE_DIR
        # TODO: handle error here
        shutil.copyfile(cache_file_path, arg)

    def load_one_file(self, fpath):
        if os.path.exists(fpath):
            name = fpath.split('/')[-1]
            new_full_path = "{}/{}/{}".format(BASE_DIR, INCLUDE_DIR, name)
            inlcude_path = "{}/{}".format(BASE_DIR, INCLUDE_DIR)
            if name not in os.listdir(inlcude_path):
                # update include header for cache
                cache_inlcude = '{}/{}/{}'.format(BASE_DIR, CACHE_DIR, CACHE_INCLUDE_FILE)
                with open(cache_inlcude, 'a+') as f:
                    f.write('#include "../{}/{}"\n'.format(INCLUDE_DIR, name))
            shutil.copyfile(fpath, new_full_path)
        else:
            print('file {} not exist!'.format(fpath))
            return False

    def do_load(self, arg):
        '''
        load [file1, file2 ...] : load a datalog file, (you don't need re decl rule loaded before)
        be careful this will not resolve your include!
        '''
        if arg.strip() == '':
            print('please load at least one dl file')
            return
        fpaths = arg.strip().split(' ')
        for fpath in fpaths:
            if fpath != '':
                res = self.load_one_file(fpath)
                if res:
                    return
        cache_file_path = os.path.abspath(BASE_DIR+'/'+CACHE_DIR+'/'+self.cachefile)
        self.run_souffle(cache_file_path)

    def do_facts(self, arg):
        '''
        facts [dir] : load EDB facts
        '''
        # copy all these into tmp
        if os.path.exists(arg):
            for e in os.listdir(arg):
                if e.endswith('.facts'):
                    shutil.copyfile(arg+e, self.output_dir +
                                    '/' + FACTS_DIR + e)
        else:
            print("plz check whether dir exisits")

    def do_cleancache(self, arg):
        '''
        clean query cache
        '''
        self.create_cache()
        out_full_path = BASE_DIR+'/'+OUT_DIR
        if os.path.exists(out_full_path):
            shutil.rmtree(out_full_path)
            os.makedirs(out_full_path)

    def do_rules(self, arg):
        '''
        list avaliable rules to query(rule with .output/.input)
        '''
        # list facts
        facts_files = os.listdir(BASE_DIR + '/' + FACTS_DIR)
        tmpout = []
        counter = 0
        for e in facts_files:
            if counter > 3:
                counter = 0
                print("{:<40} {:<40} {:<40}".format(*tmpout))
                tmpout = []
            tmpout.append(e[:-6])
            counter = counter + 1
        outs_files = os.listdir(BASE_DIR + '/' + OUT_DIR)
        for e in outs_files:
            if counter > 3:
                counter = 0
                print("{:<30} {:<30} {:<30}".format(*tmpout))
                tmpout = []
            tmpout.append(e[:-4])
            counter = counter + 1

    def do_quit(self, arg):
        '''
        exit
        '''
        print('\nsee you (TvT)/~\n')
        return True

    def do_history(self, arg):
        '''
        show histroy input of datalog rule
        '''
        cache_file_path = BASE_DIR+'/'+CACHE_DIR+'/'+self.cachefile
        with open(cache_file_path, 'r') as f:
            print(f.read())

    def run_souffle(self, file):
        fact_full_path = os.path.abspath(BASE_DIR+'/'+FACTS_DIR)
        out_full_path = os.path.abspath(BASE_DIR+'/'+OUT_DIR)
        
        command = '{} -F {} -D {} {}'.format(SOUFFLE_COMMAND,
                                             fact_full_path, out_full_path, file)
        os.system(command)
        res = os.popen('cat /etc/services').read()
        if res.find('Error:') != -1:
            self.do_cleancache('')

    def do_save(self, arg):
        '''
        save [path] : save the output of current session
        '''
        out_full_path = '{}/{}'.format(BASE_DIR, OUT_DIR)
        shutil.copytree(out_full_path, arg)

    def default(self, arg):
        '''
        run a datalog rule, please keep single rule in one line
        '''
        # NOTE: should check if it is a valid souffle expression here
        # check if it is a output command
        arg = arg.strip()
        if not is_valid_dl(arg):
            print('invalid datalog rule, if want to input some command, type "?" to see.')
            return
        if arg.startswith('.output'):
            # there is already a output?
            rule_name = arg[7:].strip()
            outs_files = os.listdir(BASE_DIR+'/'+OUT_DIR)
            facts_files = os.listdir(BASE_DIR+'/'+FACTS_DIR)
            if (not ((rule_name+'.csv') in outs_files)) and (not ((rule_name+'.facts') in facts_files)):
                with open(BASE_DIR+'/'+CACHE_DIR+'/'+self.cachefile, 'r+') as f:
                    exist_rules = str(f.read())
                    all_names = map(lambda n: n.strip(), re.findall(r"\.decl(.+)\(", exist_rules))
                    if rule_name in all_names:
                        f.write('\n'+arg+'\n')
                    else:
                        print('rule has not been declared')
                cache_file_path = os.path.abspath(BASE_DIR+'/'+CACHE_DIR+'/'+self.cachefile)
                self.run_souffle(cache_file_path)
            if (rule_name+'.csv') in outs_files:
                with open('{}/{}/{}.csv'.format(BASE_DIR, OUT_DIR, rule_name), 'r') as f:
                    print(f.read())
            if (rule_name+'.facts') in facts_files:
                with open('{}/{}/{}.facts'.format(BASE_DIR, FACTS_DIR, rule_name), 'r') as f:
                    print(f.read()) 
        else:
            with open(BASE_DIR+'/'+CACHE_DIR+'/'+self.cachefile, 'a+') as f:
                f.write(arg+'\n')


def rename_out_to_facts(path):
    entries = os.listdir(path)
    facts = filter(lambda e: e.endswith('.facts'), entries)
    facts = map(lambda e: e[:-6], facts)
    outs = filter(lambda e: e.endswith('.csv'), entries)
    outs = map(lambda e: e[:-4], outs)
    for e in outs:
        # remove input if it is also output
        if e in facts:
            os.remove(path+"/"+e+'facts')
        os.rename(path+"/"+e+'.csv', path+"/"+e+".facts")

def prepare_tmp():
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)
    os.makedirs(BASE_DIR)
    os.makedirs(BASE_DIR + '/' + INCLUDE_DIR)
    os.makedirs(BASE_DIR + '/' + OUT_DIR)
    os.makedirs(BASE_DIR + '/' + DL_DIR)
    os.makedirs(BASE_DIR + '/' + CACHE_DIR)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('-N', '--name', dest='dlname', help='your datalog program name')
    parser.add_option('-D', '--datalog-dir', dest='dl_dir', help="fold contain all your datalog rule")
    parser.add_option('-E', '--entry-dl', dest='entry_dl', help="main entry path of your datalog rule")
    parser.add_option('-F', '--facts-dir', dest='facts_dir', help="EDB facts preloaded")
    (options, args) = parser.parse_args()
    prepare_tmp()
    if options.dl_dir is None:
        print('plz enter your datalog dir')
        exit()
    if options.entry_dl is None:
        print('plz enter your top level datalog file')
        exit()
    dl_new_path = '{}/{}/{}'.format(BASE_DIR, DL_DIR, options.dlname)
    shutil.copytree(options.dl_dir, dl_new_path)
    include_file_path = '{}/{}/{}_include.dl'.format(BASE_DIR, INCLUDE_DIR, options.dlname)

    # copy facts into facts
    if options.facts_dir is not None:
        print('plz specify your fact dir')
        exit()
    if not os.path.exists(options.facts_dir):
        print('plz have a valid facts dir')
    facts_new_path = '{}/{}'.format(BASE_DIR, FACTS_DIR)
    shutil.copytree(options.facts_dir, facts_new_path)
    lib = DatalogLib(options.dlname, include_file_path)
    lib.add_dir(dl_new_path)
    lib.rewrite_rule()
    lib.generate_inlcude()
    print("plz check the .init line in your generated file, something optional inside include may also be copied here!")
