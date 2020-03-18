#! /bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
$DIR/.RemoveQuarantine.sh
$DIR/.UpdateExamples.sh
mv $DIR/.UpdateExamples.sh $DIR/UpdateExamples.command
rm $DIR/.RemoveQuarantine.sh
rm $DIR/Setup.command