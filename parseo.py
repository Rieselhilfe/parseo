""" nix """
import json
from lark import Lark
import fire
from lark.visitors import CollapseAmbiguities
from lark.exceptions import UnexpectedEOF, UnexpectedCharacters
from rich import print, inspect
from rich.traceback import install
from rich.table import Table
install(extra_lines=1)

# ----- construct parser for lark -------- #

VORTARO_PATH = "vortaro.json"
GRAMMAR_PATH = "espWord.grammar"

with open(VORTARO_PATH) as vortaroFile:
    vortaro = json.load(vortaroFile)

vortaroFlat = {}
vortaroFlat.update(vortaro["radikoj"]["a"])
vortaroFlat.update(vortaro["radikoj"]["o"])
vortaroFlat.update(vortaro["radikoj"]["i"])
vortaroFlat.update(vortaro["radikoj"]["e"])
vortaroFlat.update(vortaro["radikoj"]["aj"])
vortaroFlat.update(vortaro["radikoj"]["oj"])
vortaroFlat.update({("-"+x+"-"): y for (x, y) in vortaro["sufiksoj"].items()})
vortaroFlat.update({(x+"-"): y for (x, y) in vortaro["prefiksoj"].items()})
vortaroFlat.update(vortaro["other"])

vortaroRoots = {}
vortaroRoots.update(vortaro["radikoj"]["a"])
vortaroRoots.update(vortaro["radikoj"]["o"])
vortaroRoots.update(vortaro["radikoj"]["i"])
vortaroRoots.update(vortaro["radikoj"]["e"])
vortaroRoots.update(vortaro["radikoj"]["aj"])
vortaroRoots.update(vortaro["radikoj"]["oj"])
#vortaroRoots.update(vortaro["other"])

prefixes = vortaro["prefiksoj"]
suffixes = vortaro["sufiksoj"]
memstaro = vortaro["other"]

prefixRule = "!prefix: "+("|".join(['"'+word+'"' for word, _ in prefixes.items()]))+"\n"
suffixRule = "!suffix: "+("|".join(['"'+word+'"' for word, _ in suffixes.items()]))+"\n"
memstaroRule = "!memstaro: "+("|".join(['"'+word+'"' for word, _ in memstaro.items()]))+"\n"

with open(GRAMMAR_PATH) as grammarFile:
    grammar = grammarFile.read()

grammar = grammar\
        + prefixRule\
        + suffixRule\
        + memstaroRule\

parser = Lark(grammar, parser='earley', ambiguity='explicit', start="start_word")
num_parser = Lark(grammar, parser='earley', start="start_num")

# ---- interpretation of esperanto words ---- #

def child0(a):
    return a.children[0]

def translate_number(tree):
    num = 0
    pot = 0
    num_dict = {
            "nulo": 0,
            "unu": 1,
            "du" : 2,
            "tri" : 3,
            "kvar" : 4,
            "kvin" : 5,
            "ses" : 6,
            "sep" : 7,
            "ok" : 8,
            "naŭ": 9,
            "dek": 10,
            "cent": 100,
            "mil": 1000,
            "miliono": 1000*1000,
            "miliardo": 1000*1000*1000,
            "biliono": 1000*1000*1000*1000,
            "biliardo":1000*1000*1000*1000*1000,
        }
    for c in tree.children:
        if c.data == "digit_term":
            num += int(num_dict[child0(child0(c))])
        elif c.data == "dekpot":
            digit_num = num_dict[child0(child0(c))]
            num += 10*int(digit_num)
        elif c.data == "centpot":
            digit_num = num_dict[child0(child0(c))]
            num += 100*int(digit_num)
        elif c.data == "milpot":
            pot_num = translate_number(child0(c))
            num += 1000*pot_num
        elif c.data == "bigger_pot":
            token_num = int(num_dict[c.children[1]])
            pot_num = translate_number(child0(c))
            num += token_num*pot_num
    return num

def interpret(t, num=False):
    interpreted = {
        "prefix":[],
        "root":[],
        "suffix":[],
        "ending":[]
    }
    if num and child0(t).data == "number":
        content = translate_number(child0(t))
        interpreted["root"].append("number: "+str(content))
        return interpreted
    elif child0(t).data == "number":
        return None

    words = child0(t)
    roots = []
    for part in words.children:
        if part.data == "root":
            root = "".join([letter for letter in part.children])
            roots.append(root)
            if root in vortaroRoots:
                definition = vortaroRoots[root]
            else:
                return None
            content = root+": "+"; ".join(definition)
            interpreted["root"].append(content)
        elif part.data == "ending":
            content = child0(part).data
            interpreted["ending"].append(content)
        elif part.data == "prefix":
            prefix = child0(part)
            definition = vortaroFlat[prefix+"-"]
            content = prefix+": "+"; ".join(definition)
            interpreted["prefix"].append(content)
        elif part.data == "suffix":
            suffix = child0(part)
            definition = vortaroFlat["-"+suffix+"-"]
            content = suffix+": "+"; ".join(definition)
            interpreted["suffix"].append(content)
        elif part.data == "memstaro":
            memstaro = child0(part)
            definition = vortaroFlat[memstaro]
            content = memstaro+": "+"; ".join(definition)
            interpreted["root"].append(content)
        else:
            if part.data != "connection":
                print("invalid: ",part.data)
    if not (roots and roots[-1] in vortaro["other"] and interpreted["ending"]):
        return interpreted
    else:
        return None

def parseAndInterpret(s, num=False, both=False):
    s = s.replace("ux", "ŭ")
    s = s.replace("cx", "ĉ")
    s = s.replace("sx", "ŝ")
    s = s.replace("jx", "ĵ")
    s = s.replace("hx", "ĥ")
    def pai(s, num=False):
        try:
            if num:
                parsed = num_parser.parse(s+" ")
            else:
                parsed = parser.parse(s)
        except UnexpectedEOF:
            return None
        except UnexpectedCharacters:
            return None
        if not num:
            interps = CollapseAmbiguities().transform(parsed)
            interps = [interpret(i, num=num) for i in interps]
            return [i for i in interps if i]
        else:
            return [interpret(parsed, num=num)]

    if both: # first num because it takes a lot less time
        interpretations = pai(s, True)
        if not interpretations:
            interpretations = pai(s, False)

    if not interpretations:
        print("[italic bold red] No results found! [/italic bold red]")
        return
    table = Table(title=s, show_lines=True, title_style="yellow bold")
    table.add_column("Nr.")
    table.add_column("prefix", style="cyan")
    table.add_column("root", style="magenta")
    table.add_column("suffix", style="red")
    table.add_column("morphology", style="green")
    for n, i in enumerate(interpretations):
        table.add_row(str(n),
                      "\n\n".join(i["prefix"]),
                      "\n\n".join(i["root"]),
                      "\n\n".join(i["suffix"]),
                      "\n\n".join(i["ending"]).replace("_", ", "))
    print("\n",table, "\n")

# ----- command line interface class for fire ------- #

class Parseo(object):
    def parse(self, s):
        parseAndInterpret(s, both=True)
    def parsenum(self, n):
        parseAndInterpret(n, num=True)
    def parseword(self, s):
        parseAndInterpret(s)

if __name__ == '__main__':
  fire.Fire(Parseo)
