#! /bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
$DIR/.RemoveQuarantine.sh
$DIR/.UpdateExamples.sh
$DIR/.UpdateSCAMP.sh
mv $DIR/.UpdateExamples.sh $DIR/UpdateExamples.command
mv $DIR/.UpdateSCAMP.sh $DIR/UpdateSCAMP.command
rm $DIR/.RemoveQuarantine.sh
rm $DIR/Setup.command
