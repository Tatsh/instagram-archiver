Instagram Archiver
==================

Commands
--------

.. click:: instagram_archiver.main:main
  :prog: instagram-archiver
  :nested: full

Typical use
^^^^^^^^^^^

.. code-block:: shell

   instagram-archiver -o ~/instagram-backups username

Videos are saved using yt-dlp and its respective configuration.

.. only:: html

   Library
   -------
   .. automodule:: instagram_archiver.client
      :members:

   Constants
   ---------
   .. automodule:: instagram_archiver.constants
      :members:

   Typing
   ------
   .. automodule:: instagram_archiver.typing
      :members:

   Utilities
   ---------
   .. automodule:: instagram_archiver.utils
      :members:
      :exclude-members: setup_logging

   .. toctree::
      :maxdepth: 2
      :caption: Contents:

Indices and tables
------------------
* :ref:`genindex`
* :ref:`modindex`
