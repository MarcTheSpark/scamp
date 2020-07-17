
# xxl ####################################################################################

# before making the xxl bundle, move the Thonny app back to where it was
mv build/SCAMP/Thonny.app build/Thonny.app

$PYTHON_CURRENT/bin/python3.7 -s -m pip install --no-cache-dir -r ../requirements-xxl-bundle.txt

find $PYTHON_CURRENT/lib -name '*.pyc' -delete
find $PYTHON_CURRENT/lib -name '*.exe' -delete

# sign frameworks and app ##############################
codesign --force -s "Marc Evanstein" --timestamp --keychain ~/Library/Keychains/login.keychain-db \
	--entitlements thonny.entitlements --options runtime \
	build/Thonny.app/Contents/Frameworks/Python.framework
codesign --force -s "Marc Evanstein" --timestamp --keychain ~/Library/Keychains/login.keychain-db \
	--entitlements thonny.entitlements --options runtime \
	build/Thonny.app


# create dmg #####################################################################
# before making the dmg, move the Thonny app back to the scamp folder
mv build/Thonny.app build/SCAMP/Thonny.app

PLUS_FILENAME=dist/thonny-xxl-${VERSION}.dmg
rm -f $PLUS_FILENAME
hdiutil create -srcfolder build -volname "Thonny XXL $VERSION" -fs HFS+ -format UDBZ $PLUS_FILENAME

# sign dmg #######################################################################
codesign -s "Marc Evanstein" --timestamp --keychain ~/Library/Keychains/login.keychain-db \
	--entitlements thonny.entitlements --options runtime \
	$PLUS_FILENAME


# Notarizing #####################################################################
# https://successfulsoftware.net/2018/11/16/how-to-notarize-your-software-on-macos/
# xcrun altool -t osx --primary-bundle-id org.thonny --notarize-app --username <apple id email> --password <generated app specific pw> --file <dmg>
# xcrun altool --notarization-info $1 --username aivar.annamaa@gmail.com --password <notarize ID>
# xcrun stapler staple <dmg>


# clean up #######################################################################
#rm -rf build
