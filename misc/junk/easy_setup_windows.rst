Easy Setup on Windows
=====================

If you're new to Python, the easiest way to get up and running with SCAMP on Windows is to:

1. Install Thonny, a simple Python editor for beginners

2. Install the SCAMP package and its dependencies from inside Thonny

3. Install LilyPond

Installing Thonny
-----------------

To install Thonny, simply go to `the Thonny website <https://thonny.org/>`_ and download and run the Windows installer. You may run into an issue with Windows Defender not trusting the installer; just click "More info" and
"Run anyway":

+-------+-------+
||pic1| | |pic2||
+-------+-------+


.. |pic1| image:: WindowsInstallingThonny.png
   :width: 100%

.. |pic2| image:: WindowsInstallingThonny2.png
   :width: 100%

Run the installer as you would any other installer, and then open up Thonny.


Installing SCAMP
----------------

From inside scamp, go to the `Tools` menu and select `Manage Packages...`

.. image:: WindowsManagePackages.png
   :width: 70%
   :align: center

In the dialog that opens, type "scamp" into the textbox and click "Find package from PyPI". PyPI is an online repository of Python libraries from which SCAMP can be downloaded and installed. Click the "Install" button:

.. image:: WindowsInstallSCAMP.png
   :width: 70%
   :align: center

After having installed SCAMP, search for and install the following packages, upon which scamp depends:

- `python-rtmidi`

- `abjad`

- `pynput`


Installing LilyPond
-------------------

One of the tools that SCAMP uses to produce music notation is a marvelous piece of free and open source music notation software called LilyPond. Download and install LilyPond from `the LilyPond website <http://lilypond.org/windows.html>`_. You may see an unnerving dialog about allowing and "unknown publisher to make changes". Just click yes and proceed with the installation:

.. image:: WindowsLilypondUnnerving.png
   :width: 70%
   :align: center


Testing it Out
--------------

To test if everything is working correctly, open up Thonny, and save and run the following script:

.. code-block:: python

    from scamp import test_run
    test_run.play(show_lilypond=True)

You should hear a piano gesture sweeping inward towards middle C, and then see the notation pop up!