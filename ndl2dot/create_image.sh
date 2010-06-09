#!/bin/sh
f=$*
if [[ -f images/${f/.rdf/.dot} ]]; then
     rm images/${f/.rdf/.dot}
fi
$PWD/ndl2dot.py $f images/${f/.rdf/.dot}
fdp -Tpng -o images/${f/.rdf/.png} images/${f/.rdf/.dot} 2> /dev/null
