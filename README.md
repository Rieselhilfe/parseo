# parseo
A smart esperanto word parser that shows all possible word compositions from roots, affixes and word endings. 
Based on Baza Radikaro Oficiala.


Usage from command line: 
    
    python parseo.py parse [esperanto-word]
    
For Example:
  
    python parseo.py parse memorindajn

outputs (as a rich library table):

| Nr. | Prefix | Root | Suffix | Morphology |
| --- | ------ | ---- | ------ | ---------- |
| 0 | mem : self | or: gold |  ind: (denotes worthiness, merit) | adjective, accusative, plural |
| 1 | | memor: to recall; recollect; remember | ind: (denotes worthiness, merit) | adjective, accusative, plural |
