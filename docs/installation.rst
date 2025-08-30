Installation and Update
=======================

This add-on is a collection of Geometry Nodes for Blender. This add-on is free for Commercial Use based on GPL-3. So you can install as addon or .blend file as Asset Libraries.

You can see our source code on `Github here (stable version) <https://github.com/Breathfang/BreathfangGeoNodes/>`_ or `Github here (preview version) <https://github.com/Breathfang/BreathfangGeoNodes/tree/preview>`_

Requirements
------------

Before you install |packnamebold|, here is the requirements

* For base |packnamebold|, the minimum version of Blender is |blenderminver|. The node prefix is ``BFang_``
* For |packnameextbold|, the minimum version of Blender is |blenderextminver|. The node prefix is ``BFangExt_``

.. warning::
   If you installed in older version, be prepare of compatibility issues. Such as ``BFangExt_`` node will not work or weird behavior in |blenderminver|.
   
   Some nodes may disappear automatically by Blender if you attempt to using |packnameextbold| in |blenderminver|.

Step to install
---------------

After you download |packnamebold|, here is the steps to install |packnamebold|

.. warning::
    If you've downloaded in unknown or pirated sources, it may cause the add-on or the .blend file to not work properly or being outdated. If you've encountered any issues, there is no support will be provided.
    
    **Please note:** This add-on is free for Commercial Use based on GPL-3 and it priced $0 (Free).

.. _addon-method:

Method 1: Using Addon Method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you like to install |packnamebold| as add-on, here is the steps

1. Open ``File -> Preferences -> Add-ons -> Dropdown menu -> Install from disk...``
2. Find |packnameblendver|
3. Click ``Install from disk``


.. _blend-method:

Method 2: Using .blend file method as Asset Libraries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to install |packnamebold| as Asset Libraries, here is the steps

1. Locate the downloaded |packnamezipver|
2. Extract the |packnameblendver| in any location
3. Open ``File -> Preferences -> File Paths -> Asset Libraries``
4. Click ``(+) Add Asset Library``
5. Locate the |packnamebold| folder and select |packnameblendver|.
6. Click ``Add Asset Library``

.. warning::
   To prevent breaking changes when updating |packnameblend|, you must set ``Import Method`` as ``Append (Reuse Data)``.

    .. image:: /_static/img/steptoinstall/correct_import_method.jpg
        :target: /_static/img/steptoinstall/correct_import_method.jpg
        :width: 100%
        :alt: Append

.. caution::
    NEVER set ``Import Method`` as ``Link``, otherwise it will break your project file if you update to newer version.

How to update
-------------

If you want to update |packnamebold|, here is the steps

Method 1: If you using addon method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here is the steps to update |packnamebold|:

1. Open ``File -> Preferences -> Get Extensions``
2. Search |packnamecode|
3. Click ``Update``
4. Wait until the update is done

Method 2: If you using .blend file method as Asset Libraries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    Since you've installed |packnamebold| as Asset Libraries, you are not necessary to open preferences.
    You just only need to replace the |packnameblendold|.

Here is the steps to update |packnamebold|:

1. Extract the |packnamezipnew|
2. Locate |packnameblendnew| in extracted folder, then press ``CTRL + C`` or ``right click -> Copy``
3. Open your directory that contains |packnameblendold|
4. Rename the |packnameblendold| to |packnameblendoldold|, then press ``CTRL + V`` or ``right click -> Paste``.
5. (Optional) You can delete |packnameblendoldold|.
6. Restart Blender

.. _reinstall-the-addon:

How to reinstall
----------------

If you want to reinstall |packnamebold|, this is same as how to update |packnamebold|. Refers to `How to update <installation.html#how-to-update>`_

Just download the same version as you've downloaded before, and then extract it.

How to uninstall
----------------

If you want to uninstall |packnamebold|, here is the steps

.. warning::
    If you set ``Import Method`` as ``Link``, you need to set ``Import Method`` as ``Append (Reuse Data)`` first. Otherwise it will break your project file.

Method 1: If you using addon method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open ``File -> Preferences -> Get Extensions``
2. Search |packnamecode|
3. Click ``Uninstall``
4. In the pop up, click ``Confirm``
5. Or alternatively you can disable the add-on in ``Add-ons`` and search for |packnamebold| then untick the checkbox to disable the add-on instead of uninstalling the addon.

Method 2: If you using .blend file method as Asset Libraries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open ``File -> Preferences -> File Paths -> Asset Libraries``
2. Select |packnameblendver| and click ``Remove``

.. note::
    You can delete your package folder to free up space of your disk.
