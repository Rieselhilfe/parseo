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
    print(tree)
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
        "ending": []
    }
    if num and t.data == "number":
        content = translate_number(child0(t))
        interpreted["root"].append("number: " + str(content))
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
        elif part.data == "memstaro":
            memstaro = child0(part)
            roots.append(memstaro)
            definition = vortaroFlat[memstaro]
            content = memstaro + ": " + "; ".join(definition)
            interpreted["root"].append(content)
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
        elif part.data == "prefix":
            prefix = child0(part)
            definition = vortaroFlat[prefix + "-"]
            content = prefix + ": " + "; ".join(definition)
            interpreted["prefix"].append(content)
        elif part.data == "suffix":
            suffix = child0(part)
            definition = vortaroFlat["-" + suffix + "-"]
            content = suffix + ": " + "; ".join(definition)
            interpreted["suffix"].append(content)
        elif part.data == "correlative":
            if len(part.children) > 2 or part.children[1].data == 'o_thing' or part.children[1].data == 'e_place':
                if part.children[1].data == 'e_place':
                    if len(part.children) > 2 and part.children[2].data == 'directional_accusative':
                        morphology = ", ".join(["correlative", "directional accusative"])
                    else:
                        morphology = ", ".join(["correlative"])
                elif part.children[1].data == 'o_thing':
                    if len(part.children) > 2 and part.children[2].data == 'accusative':
                        morphology = ", ".join(["correlative", "accusative"])
                    else:
                        morphology = ", ".join(["correlative", "nominative"])
                else:
                    morphology = ", ".join(["correlative"] + num_and_case(part.children[2]))
                interpreted["ending"].append(morphology)
            else:
                interpreted["ending"].append("correlative, inflectable")
            root = x_rule("".join([x.data.split("_")[0] for x in part.children[:2]]))
            corr = "(" + x_rule(") + (".join([x.data.replace("_", ": ") for x in part.children[:2]])) + ")"
            content = "correlative: " + corr
            definition = "-> " + root + ": " + "; ".join(vortaroFlat[root])
            interpreted["root"].append(content)
            interpreted["root"].append(definition)
        else:
            if part.data != "connection":
                console.print("invalid: ", part.data)
    return interpreted


def all_word_interpretations(s: str, num=False):
    try:
        if num:
            parsed = num_parser.parse(s + " ")
            print("(" + s + " " + ")")
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


def parseAndInterpret(s: str, num=False, both=False):
    s = x_rule(s)

    if both:  # first num because it takes a lot less time
        interpretations = all_word_interpretations(s, True)
        if not interpretations:
            interpretations = all_word_interpretations(s, False)
    else:
        interpretations = all_word_interpretations(s, num)
    if not interpretations:
        console.print("[italic bold red] No results found! [/italic bold red]")
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
        parseAndInterpret(s, both=True)
        try:
            s = console.input(PROMPT)
        except EOFError:
            break
        except KeyboardInterrupt:
            break


# ----- command line interface class for fire ------- #

class Parseo(object):
    def parse(self, s):
        parseAndInterpret(s, both=True)

    def parsenum(self, n):
        parseAndInterpret(n, num=True)

    def parseword(self, s):
        parseAndInterpret(s)

    def read(self, *t):
        read_text(t)

    def repl(self):
        repl()


if __name__ == '__main__':
    fire.Fire(Parseo)
