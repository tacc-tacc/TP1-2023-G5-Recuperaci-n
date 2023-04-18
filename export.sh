for f in "designer"/*
    do
    name=${f##*/}
    python -m PyQt5.uic.pyuic "$f" -o "src/ui/${name%.*}.py"
    done

for f in "resources"/*
    do
    name=${f##*/}
    extension=${f##*.}
    if [ $extension = "qrc" ]; then
        python -m PyQt5.pyrcc_main "$f" -o "${name%.*}_rc.py" #error de Python que hace necesario agregar '_rc' al nombre y ponerlo en el root
    fi
    done
echo "DONE"
