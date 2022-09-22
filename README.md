# parseo
A smart esperanto word parser that shows all possible word compositions from roots, affixes and word endings. 
Based on the wordlists of Baza Radikaro Oficiala.

Web version: [http://parseo.online](http://parseo.online)

Usage from command line: 
    
    python parseo.py parse [esperanto-word]
    
For Example:
  
    python parseo.py parse memorindajn

outputs (as a rich library table):

| Nr. | Prefix | Root | Suffix | Morphology |
| --- | ------ | ---- | ------ | ---------- |
| 0 | mem : self | or: gold |  ind: (denotes worthiness, merit) | adjective, accusative, plural |
| 1 | | memor: to recall; recollect; remember | ind: (denotes worthiness, merit) | adjective, accusative, plural |

Parseo also can parse and translate numbers and understands the x-system, so:

    python parseo.py parse "kvin milionoj kvarcent tridek kvin mil sescent okdek naux"

outputs:

| Nr. | Prefix | Root | Suffix | Morphology |
| --- | ------ | ---- | ------ | ---------- |
| 0 | | number: 5435689 | | |
