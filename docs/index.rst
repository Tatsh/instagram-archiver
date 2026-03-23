Instagram Archiver
==================

.. include:: badges.rst

Commands
--------

.. click:: instagram_archiver.main:main
  :prog: instagram-archiver
  :nested: full

.. code-block:: shell

   instagram-archiver -o ~/instagram-backups username

The default output path is the username under the current working directory.

Videos are saved using yt-dlp and its respective configuration.

.. click:: instagram_archiver.main:save_saved_main
   :prog: instagram-save-saved
   :nested: full

.. only:: html

   Library
   -------
   .. automodule:: instagram_archiver.client
      :members:

   .. automodule:: instagram_archiver.profile_scraper
      :members:

   .. automodule:: instagram_archiver.saved_scraper
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
