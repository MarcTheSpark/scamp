# create dmg #####################################################################
mkdir -p dist
FILENAME=dist/thonny-with-scamp.dmg
rm -f $FILENAME
hdiutil create -srcfolder build -volname "SCAMP" -fs HFS+ -format UDBZ $FILENAME

# sign dmg ######################
codesign -s "Marc Evanstein" --timestamp --keychain ~/Library/Keychains/login.keychain-db \
	--entitlements thonny.entitlements --options runtime \
	$FILENAME

exit
