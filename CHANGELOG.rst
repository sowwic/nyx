nyx
=========================

v 1.0.2
-------
* (#154) Load the environment of the login shell on launch (Linux, macOS), so Nyx has the user's ``PATH`` and variables when started from the Finder or a desktop entry
* (#154) Add the ``environment`` config section with ``source_file`` (environment file to load) and ``vars_overrides`` (variables set last), applied on launch and whenever the config is saved
* (#154) Add ``--envfile`` argument to ``nyx`` and ``nyx stage run`` to load an environment file before starting
* (#154) Add Fetch Environment node, storing the environment variables in a dictionary when the flow reaches it
* (#154) Add system function nodes ``append_env``, ``prepend_env``, ``pop_env``, ``unset_env``, ``update_env``, ``split_env``, ``has_env_entry``, ``expand_env``, ``load_env_file``, ``filter_env``, ``get_env_bool`` and ``get_env_int``
* (#154) Show dictionary, list, tuple and set values as a scrollable list in the Inspector
* (#154) Add ``editor_utils`` to api (editor helpers for plugins, ``create_mono_icon`` and ``create_mono_image`` for icons matching the editor's)
* (#154) Fix the fallback QML item of components without an editor pointing at a file that doesn't exist

v 1.0.1
-------
* (#150) Expose stlib nodes and components in api

v 1.0.0
-------
* Initial release
