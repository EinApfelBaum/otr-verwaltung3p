#!/usr/bin/sh

usage () {
    echo "otr-avi2hq.sh <inputfile> [<outputfile>]"
    echo "If <outputfile> is not given it will be named: <basename>.HQ.<extension>"
}

if [ -z "$1" ]; then
    usage
    exit 1
elif [ -z "$2" ]; then
    infile="$1"
    fname=${1%.*}
    extension=${1##*.}
    outfile=${fname}.HQ.${extension}
else
    infile="$1"
    outfile="$2"
fi

#echo $fname
#echo $extension
#echo $outfile

# deblock=-1/-1:
ffmpeg -i "${infile}" -profile:v high -level 3.2 -vcodec libx264 -preset medium -tune film \
-x264opts crf=23:direct=auto:force-cfr=1:b-adapt=2:rc-lookahead=60:weightp=0:aq-mode=2:videoformat=pal:colorprim=bt709:transfer=bt709:colormatrix=bt709:force_cfr \
-vf setsar=1:1 -vf scale=720:480 \
-acodec libmp3lame -b:a 192k -ar 48000 -ac 2 "${outfile}"
