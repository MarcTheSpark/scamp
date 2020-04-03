To install, drag the SCAMP folder to your Desktop or Applications folder, then run the Setup.command script. The script will download the most recent folder of examples, and create two scripts called UpdateExamples.command and UpdateSCAMP.command that can be used in future. It will also remove a restriction that some versions of MacOS place on applications by unofficial developers
that have been downloaded from the internet.


NOTE: At first run of the application or any of the .command files below, Apple may refuse to let you open it, since I haven't paid them $100/year to be an official developer. The way to get around this is to Ctrl-click (or right-click) and select "Open", and then click "Open" again at the confirmation dialog that appears.


After running Setup.command, the SCAMP folder should contain:

- Thonny, an application (technically an IDE, or "Integrated Development Environment") for running Python code. It comes with SCAMP and its associated libraries pre-installed, so you can get straight to making music. If you have not yet installed LilyPond, you will need to do that in order to generate PDFs of music notation.
 
- A folder of examples, pulled from the SCAMP online repository.

- UpdateExamples.command, which will open up a terminal and re-download the most up-to-date examples folder when you double-click it. NB: THIS WILL DELETE THE CURRENT EXAMPLES FOLDER, so best not to store your python scripts in there.

- UpdateSCAMP.command, which will open up a terminal and run the appropriate commands to update SCAMP to the most recent release.


To uninstall, simply move the SCAMP folder to the Trash!
