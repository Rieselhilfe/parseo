""" nix """
import json
from lark import Lark
import fire
from lark.visitors import CollapseAmbiguities
from lark.exceptions import UnexpectedEOF
from rich import print, inspect
from rich.traceback import install
from rich.table import Table
install()

# TODO: ZAHLWÖRTER
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

parser = Lark(grammar, parser='earley', ambiguity='explicit', start="start")

# ---- interpretation of esperanto words ---- #

def interpret(t):
    interpreted = {
        "prefix":[],
        "root":[],
        "suffix":[],
        "ending":[]
    }
    words = t.children[0]
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
            content = part.children[0].data
            interpreted["ending"].append(content)
        elif part.data == "prefix":
            prefix = part.children[0]
            definition = vortaroFlat[prefix+"-"]
            content = prefix+": "+"; ".join(definition)
            interpreted["prefix"].append(content)
        elif part.data == "suffix":
            suffix = part.children[0]
            definition = vortaroFlat["-"+suffix+"-"]
            content = suffix+": "+"; ".join(definition)
            interpreted["suffix"].append(content)
        elif part.data == "memstaro":
            memstaro = part.children[0]
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

def parseAndInterpret(s):
    try:
        parsed = parser.parse(s)
    except UnexpectedEOF:
        print("[italic bold red] No results found! [/italic bold red]")
        return
    interpretations = CollapseAmbiguities().transform(parsed)
    interpretations = [interpret(i) for i in interpretations if interpret(i)]
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
    print(table)

# ----- command line interface class for fire ------- #

class Parseo(object):
    def parse(self, s):
        return parseAndInterpret(s)

if __name__ == '__main__':
  fire.Fire(Parseo)
