#!/usr/bin/env python3

""" nix """
import json

import sys
from typing import Dict, List
import fire

from lark import Lark, ParseTree, Token, Tree
from lark.tree import Branch
from lark.visitors import CollapseAmbiguities
from lark.exceptions import UnexpectedEOF, UnexpectedCharacters

from rich.traceback import install
from rich.table import Table
from rich.console import Console
from rich.markdown import Markdown

console = Console()
install(extra_lines=1)

# ----- construct parser for lark -------- #

PATH_PREFIX = "./"
VORTARO_PATH = PATH_PREFIX + "vortaro.json"
GRAMMAR_PATH = PATH_PREFIX + "espWord.grammar"

PROMPT = "[bold]|[green]★ [/ green] |> [/ bold]"

with open(VORTARO_PATH) as vortaroFile:
    vortaro: Dict[str, Dict[str, (Dict[str, List[str]] | List[str])]] = json.load(vortaroFile)

vortaroFlat: Dict[str, List[str]] = {}
vortaroFlat.update(vortaro["radikoj"]["a"])
vortaroFlat.update(vortaro["radikoj"]["o"])
vortaroFlat.update(vortaro["radikoj"]["i"])
vortaroFlat.update(vortaro["radikoj"]["e"])
vortaroFlat.update(vortaro["radikoj"]["aj"])
vortaroFlat.update(vortaro["radikoj"]["oj"])
vortaroFlat.update({("-" + x + "-"): y for (x, y) in vortaro["sufiksoj"].items()})
vortaroFlat.update({(x + "-"): y for (x, y) in vortaro["prefiksoj"].items()})
vortaroFlat.update(vortaro["other"])
vortaroFlat.update(vortaro["correlatives"])

vortaroRoots: Dict[str, List[str]] = {}
vortaroRoots.update(vortaro["radikoj"]["a"])
vortaroRoots.update(vortaro["radikoj"]["o"])
vortaroRoots.update(vortaro["radikoj"]["i"])
vortaroRoots.update(vortaro["radikoj"]["e"])
vortaroRoots.update(vortaro["radikoj"]["aj"])
vortaroRoots.update(vortaro["radikoj"]["oj"])
# vortaroRoots.update(vortaro["other"])

prefixes: Dict[str, List[str]] = vortaro["prefiksoj"]
suffixes: Dict[str, List[str]] = vortaro["sufiksoj"]
memstaro: Dict[str, List[str]] = vortaro["other"]

prefixRule = "!prefix: " + ("|".join(['"' + word + '"' for word, _ in prefixes.items()])) + "\n"
suffixRule = "!suffix: " + ("|".join(['"' + word + '"' for word, _ in suffixes.items()])) + "\n"
memstaroRule = "!memstaro: " + ("|".join(['"' + word + '"' for word, _ in memstaro.items()])) + "\n"

with open(GRAMMAR_PATH) as grammarFile:
    grammar = grammarFile.read()

grammar = grammar \
          + prefixRule \
          + suffixRule \
          + memstaroRule \

parser = Lark(grammar, parser='earley', ambiguity='explicit', start="start_word")
num_parser = Lark(grammar, parser='earley', start="start_num")


# ---- quick dumb fix for issue with lark's CollapseAmbiguities ---- #
# may be replaced by a recursive function
def quick_fixed_CA(tree: ParseTree | Branch[Token]):
    firstChild = child0(tree)
    words = []
    if firstChild.data == "_ambig":
        for c in firstChild.children:
            if c.data == "_ambig":
                for cc in c.children:
                    words.append(cc)
            else:
                words.append(c)
    else:
        words.append(firstChild)
    return words


# ---- terminal ui for reading a text ---- #

def read_text(t):
    text = sys.stdin.read()
    textMd = Markdown(text, justify="full")
    console.print(textMd)
    console.input("aaa? ")


# ---- interpretation of esperanto words ---- #

def x_rule(s):
    return s.replace("ux", "ŭ") \
        .replace("cx", "ĉ") \
        .replace("sx", "ŝ") \
        .replace("jx", "ĵ") \
        .replace("hx", "ĥ") \
        .replace("gx", "ĝ")


def child0(a: ParseTree | Branch[Token]):
    return a.children[0]


def translate_number(tree):
    num = 0
    pot = 0
    num_dict = {
        "nulo": 0,
        "unu": 1,
        "du": 2,
        "tri": 3,
        "kvar": 4,
        "kvin": 5,
        "ses": 6,
        "sep": 7,
        "ok": 8,
        "naŭ": 9,
        "dek": 10,
        "cent": 100,
        "mil": 1000,
        "miliono": 1000 * 1000,
        "miliardo": 1000 * 1000 * 1000,
        "biliono": 1000 * 1000 * 1000 * 1000,
        "biliardo": 1000 * 1000 * 1000 * 1000 * 1000,
    }
    for c in tree.children:
        if c.data == "digit_term":
            if child0(c) == "unu":
                num += 1
            else:
                num += int(num_dict[child0(child0(c))])
        elif c.data == "dekpot":
            if not c.children:
                digit_num = 1
            else:
                digit_num = num_dict[child0(child0(c))]
            num += 10 * int(digit_num)
        elif c.data == "centpot":
            if not c.children:
                digit_num = 1
            else:
                digit_num = num_dict[child0(child0(c))]
            num += 100 * int(digit_num)
        elif c.data == "milpot":
            if not child0(c).children:
                pot_num = 1
            else:
                pot_num = translate_number(child0(c))
            num += 1000 * pot_num
        elif c.data == "bigger_pot":
            if len(c.children) == 1:
                token_num = int(num_dict[c.children[0]])
                pot_num = 1
            else:
                token_num = int(num_dict[c.children[1]])
                pot_num = translate_number(child0(c))
            num += token_num * pot_num
    return num


def interpret(t: Branch[Token], num=False):
    def num_and_case(t):
        l = [x.data for x in t.children if x]
        if not "plural" in l:
            l.append("singular")
        if not "accusative" in l:
            l.append("nominative")
        return l

    interpreted = {
        "prefix": [],
        "root": [],
        "suffix": [],
        "ending": [],
        "structure": []
    }
    if num and child0(t).data == "number":
        content = translate_number(child0(t))
        interpreted["root"].append("number: " + str(content))
        interpreted["structure"].append(("number", content))
        return interpreted
    elif t.data == "number":
        return None

    word = t  # word = child0(t) with CollapseAmbiguities
    roots = []
    for part in word.children:
        if part.data == "root":
            root = "".join([letter for letter in part.children])
            roots.append(root)
            if root in vortaroRoots:
                definition = vortaroRoots[root]
            else:
                return None
            content = root + ": " + "; ".join(definition)
            interpreted["root"].append(content)
            interpreted["structure"].append(("root", content))
        elif part.data == "memstaro":
            memstaro = child0(part)
            roots.append(memstaro)
            definition = vortaroFlat[memstaro]
            content = memstaro + ": " + "; ".join(definition)
            interpreted["root"].append(content)
            interpreted["structure"].append(("root", content))
        elif part.data == "ending":
            if len(part.children) > 1:
                if part.children[1].data == "directional_accusative":
                    morphology = "directional accusative"
                else:
                    morphology = ", ".join(num_and_case(part.children[1]))
                content = child0(part).data + ", " + morphology
            else:
                content = child0(part).data.replace("_", ", ")

            interpreted["ending"].append(content)
            interpreted["structure"].append(("ending", content))
        elif part.data == "prefix":
            prefix = child0(part)
            definition = vortaroFlat[prefix + "-"]
            content = prefix + ": " + "; ".join(definition)
            interpreted["prefix"].append(content)
            interpreted["structure"].append(("prefix", content))
        elif part.data == "suffix":
            suffix = child0(part)
            definition = vortaroFlat["-" + suffix + "-"]
            content = suffix + ": " + "; ".join(definition)
            interpreted["suffix"].append(content)
            interpreted["structure"].append(("suffix", content))
        elif part.data == "correlative":
            morphology = None
            if len(part.children) > 2 or part.children[1].data == 'o_thing' or part.children[1].data == 'e_place':
                if part.children[1].data == 'e_place':
                    if len(part.children) > 2 and part.children[2].data == 'directional_accusative':
                        morphology = ["correlative", "directional accusative"]
                    else:
                        morphology = ["correlative"]
                elif part.children[1].data == 'o_thing':
                    if len(part.children) > 2 and part.children[2].data == 'accusative':
                        morphology = ["correlative", "accusative"]
                    else:
                        morphology = ["correlative", "nominative"]
                else:
                    morphology = ["correlative", ", ".join(num_and_case(part.children[2]))]
                interpreted["ending"] = morphology
            else:
                interpreted["ending"] = ["correlative", "inflectable"]
            root = x_rule("".join([x.data.split("_")[0] for x in part.children[:2]]))
            corr = "(" + x_rule(") + (".join([x.data.replace("_", ": ") for x in part.children[:2]])) + ")"
            content = "correlative: " + corr
            definition = "-> " + root + ": " + "; ".join(vortaroFlat[root])
            interpreted["root"].append(content)
            interpreted["root"].append(definition)
            interpreted["structure"].append(("root", content))
            if morphology:
                interpreted["structure"].append(("ending", morphology))
        elif part.data == "pronoun":
            interpreted["ending"].append("pronoun")

            if child0(part).data == "pronoun_1_sg":
                interpreted["ending"].append("1. sg.")
                interpreted["root"].append("mi")
            elif child0(part).data == "pronoun_2_sg_pl":
                interpreted["ending"].append("2. sg./pl.")
                interpreted["root"].append("vi")
            elif child0(part).data == "pronoun_m_3_sg":
                interpreted["ending"].append("3. sg. masc.")
                interpreted["root"].append("li")
            elif child0(part).data == "pronoun_f_3_sg":
                interpreted["ending"].append("3. sg. fem.")
                interpreted["root"].append("ŝi")
            elif child0(part).data == "pronoun_n_3_sg":
                interpreted["ending"].append("3. sg. neutr.")
                interpreted["root"].append("ĝi")
            elif child0(part).data == "pronoun_1_pl":
                interpreted["ending"].append("1. pl.")
                interpreted["root"].append("ni")
            elif child0(part).data == "pronoun_3_pl":
                interpreted["ending"].append("3. pl.")
                interpreted["root"].append("ili")
            elif child0(part).data == "pronoun_reflexive":
                interpreted["ending"].append("3. sg./pl. reflexive")
                interpreted["root"].append("si")

            if [x for x in part.children if x.data == "adjective"]:
                interpreted["ending"].append("possessive")
                interpreted["ending"].append(", ".join(num_and_case(part.children[-1])))
            elif len(part.children) > 1 and part.children[1].data == 'accusative':
                interpreted["ending"].append("accusative")
            else:
                interpreted["ending"].append("nominative")
            interpreted["structure"].append(("root", interpreted["root"][0]))
            interpreted["structure"].append(("ending", interpreted["ending"]))
        else:
            if not "connection" in part.data:
                console.print("invalid: ", part.data)
            else:
                interpreted["structure"].append(("connection", part.data))
    return interpreted


def all_word_interpretations(s: str, num=False):
    try:
        if num:
            parsed = num_parser.parse(s + " ")
            #print("(" + s + " " + ")")
        else:
            parsed = parser.parse(s)
    except UnexpectedEOF:
        return None
    except UnexpectedCharacters:
        return None
    if not num:
        parsed = quick_fixed_CA(parsed)  # because CA does no longer work for me (None in optionals like num_and_case)
        # parsed = CollapseAmbiguities().transform(parsed)
        interps = [interpret(i, num=num) for i in parsed]
        return [i for i in interps if i]
    else:
        return [interpret(parsed, num=num)]


def parse_and_interpret(s: str, num=False, both=False, to_json=False, min=False):
    old_s = s
    s = s.strip().lower().replace(".","").replace(",","").replace(";","").replace("?","").replace("!","").replace("\"","").replace("(","").replace(")","").replace(":","")
    s = x_rule(s)

    if both:  # first num because it takes a lot less time
        interpretations = all_word_interpretations(s, True)
        if not interpretations:
            interpretations = all_word_interpretations(s, False)
    else:
        interpretations = all_word_interpretations(s, num)
    if not interpretations:
        if not min:
            console.print("[italic bold red] No results found! [/italic bold red]")
            return
        else:
            console.print("[italic bold red]"+old_s+"[/italic bold red]", end=" ")
            return
    else:
        interpretations = assignWeight(interpretations)

    if to_json:
        print(json.dumps(interpretations))
        return

    if min:
        print_parsed_structure(interpretations[0]["structure"], True)
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
                      "\n\n".join(i["ending"]))
    console.print(table)

def assignWeight(interpretations):
    def weight(i):
        w = 0
        if "on: (denotes a fraction)" in i["suffix"]:
            w+=5
        if [n for n, e in enumerate(i["structure"]) if e[0]=="root"] and [n for n, e in enumerate(i["structure"]) if e[0]=="suffix"]:
            if [n for n, e in enumerate(i["structure"]) if e[0]=="root"][0] > [n for n, e in enumerate(i["structure"]) if e[0]=="suffix"][0]:
                w+=5
        if len(i["root"])==0:
            w+=5
        if "in adjectives" in "".join(i["suffix"]) and not "adjective" in "".join(i["ending"]):
            w+=5
        return w+(len(i["suffix"])/1.1+len(i["prefix"])+len(i["root"])/2)
    for i in interpretations:
        i["weight"] = weight(i)
    if len(interpretations) >= 1:
        return sorted(interpretations, key=lambda i: i["weight"])
    return interpretations

def print_parsed_structure(structure, color=False):
    out = []
    for s in structure:
        if s[0] == "number":
            out.append("[bold white]"+str(s[1])+"[/bold white]")
        if s[0] == "root":
            if s[1].split(":")[0] == "correlative":
                a = s[1].split("(")[1].split(":")[0]
                b = s[1].split("(")[2].split(":")[0]
                out.append("[bold magenta]"+a+"[/bold magenta]")
                out.append("[bold magenta]"+b+"[/bold magenta]")
            else:
                out.append("[bold]"+s[1].split(":")[0]+"[/bold]")
        if s[0] == "suffix":
            out.append("[yellow]"+s[1].split(":")[0]+"[/yellow]")
        if s[0] == "prefix":
            out.append("[cyan]"+s[1].split(":")[0]+"[/cyan]")
        if s[0] == "connection":
            if not "dash" in s[1]:
                out.append(s[1][-1])
            else:
                out.append("-")
        if s[0] == "ending":
            if ("correlative" in s[1] or "pronoun" in s[1]) and not ("plural" in s[1] or "accusative" in s[1]):
                continue
            out.append("[green]")
            if "noun" in s[1]:
                out[-1]+="o"
            elif "adjective" in s[1]:
                out[-1]+="a"
            elif "adverb" in s[1]:
                out[-1]+="e"
            elif "infinitive" in s[1]:
                out[-1]+="i"
            elif "future" in s[1]:
                out[-1]+="os"
            elif "perfect" in s[1]:
                out[-1]+="is"
            elif "presence" in s[1]:
                out[-1]+="as"
            elif "subjunctive" in s[1]:
                out[-1]+="us"
            elif "imperative" in s[1]:
                out[-1]+="u"
            if "plural" in s[1]:
                out[-1]+="j"
            if "accusative" in s[1]:
                out[-1]+="n"
            out[-1]+="[/green]"
        #TODO numbers
    if not color:
        print("".join(out)) #TODO
    else:
        console.print(".".join(out), end=" ")


def parse_token(s):
    s = x_rule(s)
    try:
            parsed = parser.parse(s)
    except UnexpectedEOF:
        return None
    except UnexpectedCharacters:
        return None
    return quick_fixed_CA(parsed)

def repl():
    s = console.input(PROMPT)
    while s and s != ":quit" and s != ":q":
        parse_and_interpret(s, both=True)
        try:
            s = console.input(PROMPT)
        except EOFError:
            break
        except KeyboardInterrupt:
            break


# ----- command line interface class for fire ------- #

class Parseo(object):
    def parse(self, s):
        parse_and_interpret(s, both=True)

    def parse_to_json(self, s):
        parse_and_interpret(s, both=True, to_json=True)

    def parse_all(self, s):
        s = s.split()
        for w in s:
            parse_and_interpret(w, both=True)

    def parse_all_min(self, s):
        s = s.split()
        for w in s:
            console.print(w)
            parse_and_interpret(w, both=True, min=True)
            console.line(1)

    def parse_all_min_from_file(self, filename):
        with open(filename) as f:
            content = f.read()
        for w in content.split():
            w = w.strip().lower().replace(".","").replace(",","").replace(";","").replace("?","").replace("!","").replace("\"","").replace("(","").replace(")","")
            parse_and_interpret(w, both=True, min=True)

    def parsenum(self, n):
        parse_and_interpret(n, num=True)

    def parseword(self, s):
        parse_and_interpret(s)

    def read(self, *t):
        read_text(t)

    def repl(self):
        repl()

if __name__ == '__main__':
    fire.Fire(Parseo)
