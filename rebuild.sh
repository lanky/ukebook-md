#!/bin/bash
export TSTAMP=$(date +%Y-%m-%d)
export OUTPUTDIR=~/Documents/generated_books
WEBONLY=0

SUPPORTED_TYPES="singers band"

show_help() {
    echo "Usage: $(basename ${0}) [-hl] [-o OUTPUTDIR] BOOKTYPE..."
    echo "where BOOKTYPE is one or more of ${SUPPORTED_TYPES}"
    echo "Commandline options"
    echo "  -h                Show this help and exit"
    echo "  -l                Generate landscape output"
    echo "  -w                Only generate HTML output, not pdf"
    echo "  -i INPUTDIR       where to find input documents"
    echo "  -o OUTPUTDIR      where to put generated books/html"
    echo "  -n PROJECTNAME    Name of book project, basename of INPUTDIR if not provided"
}


while getopts ":hlwi:o:n:" opt
do
    case $opt in
        h)
            show_help
            exit 0
            ;;
        o)
            OUTPUTDIR=${OPTARG}
            shift 2
            ;;
        i)
            INPUTDIR=${OPTARG}
            shift 2
            ;;
        l)
            LANDSCAPE=1
            ;;
        w)
            WEBONLY=1
            ;;
        n)
            PROJECTNAME=${OPTARG}
            shift 2
            ;;
    esac
done

[[ -z ${OUTPUTDIR} ]] && OUTPUTDIR=~/Documents/generated_books
[[ -z ${INPUTDIR} ]] && INPUTDIR=~/Documents/dev/karauke_udn/current

[[ -z ${PROJECTNAME} ]] && PROJECTNAME=$(basename ${INPUTDIR})



if [ ${#} -gt 0 ]; then
    BOOKTYPES=${*}
else
    BOOKTYPES=${SUPPORTED_TYPES}
fi

echo "Output wil be placed in ${OUTPUTDIR}"
echo "Generating booktypes ${BOOKTYPES}"


for BOOKTYPE in ${BOOKTYPES}; do

    case ${BOOKTYPE} in
        band)
            STYLE=pdfprint
            FORMAT=karauke
            ;;
        singers)
            STYLE=pdfprint
            FORMAT=singers
            ;;
        landscape_singers)
            STYLE=landscapepdf
            FORMAT=singers
            ;;
        landscape_band)
            STYLE=landscapepdf
            FORMAT=karauke
            ;;
    esac
    ./genbook.py --${FORMAT} -s ${STYLE} ${INPUTDIR} -o ${OUTPUTDIR}/karauke-${BOOKTYPE}-${TSTAMP} &&
    if [ ${WEBONLY} -ne 1 ]; then
        ./makepdf.py ${OUTPUTDIR}/karauke-${BOOKTYPE}-${TSTAMP} -o ${OUTPUTDIR}/karauke-${BOOKTYPE}-${TSTAMP}.pdf
    else
        echo "skipping PDF generation as requested"
    fi
done
