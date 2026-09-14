# SCAMP AI Policy

All code that is included in this library must be thoroughly reviewed and edited by a human being before being 
committed. Such code generally goes through many rounds of revision and redirection: we have found that AI coding 
tools can be very valuable, but the quality of the codebase inevitably reflects the quality of human effort and 
attention paid.

The person committing the code accepts responsibility for understanding every single line. Comments in the code are a 
central way of ensuring understanding: both of the person committing the code, and as a communication to future 
contributors. AI coding agents will inevitably offer a first draft of comments, but these drafts must be carefully 
edited to reflect the human reviewer's understanding. It has been our repeated experience that the process of rewording
comments often leads to changes in understanding that necessitate changes in the code itself. Bottom line: if you
can't explain it line-by-line, it does not belong in the core libraries.

The one exception to the rules above is in scripts for packaging and documentation. These may be written mostly
or entirely with AI assistance, and may receive considerably less scrutiny than the core library code. Since they do 
not ship with the packaged library, and are not run on users' computers, the threshold for responsibility is lower.
That said, *such scripts should be labeled as AI-written* to clearly delineate what has and has not received human 
effort and attention.

Similarly, changelogs, commit messages, and planning documents may be written with AI assistance. These should be 
reviewed briefly for correctness and clarity.

The goal of these policies is to ensure the long-term health of this codebase, and in particular to ensure that if all AI
coding tools abruptly disappeared, the codebase would remain maintainable. In some cases — such as with the writing of 
commit messages and changelogs — AI tools _increase_ the human maintainability of the code. Such tasks are tedious and
human developers tend to cut corners with them despite their usefulness. However, where the core library code is 
concerned, slow deliberate human effort is essential to the quality of codebase.
