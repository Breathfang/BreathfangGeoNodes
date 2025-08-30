import datetime

master_doc = 'index'

# Project Setup
html_title = 'Breathfang\'s Geometry Nodes Toolset Pack'  # Optional: title shown in browser tab
project = 'Breathfang\'s Geometry Nodes Toolset Pack'  # This shows up in the header and browser title
html_static_path = ['_static']
html_logo = '_static/img/logo/logo.png'

# Project Information
version = 'v1.1.0-preview'
release = 'v1.1.0-preview'
author = 'Breathfang'

# Update copyright
copyright = f'2025, Breathfang (Formerly Drageon DB)'

if datetime.datetime.now().year > 2025:
    copyright = f'2025-{datetime.datetime.now().year}, Breathfang (Formerly Drageon DB)'

# Project Extensions
extensions = [
    'sphinx_rtd_theme',
]

# Theme Setup
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    'analytics_id': 'G-XXXXXXXXXX',  #  Provided by Google in your dashboard
    'analytics_anonymize_ip': False,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#8a080d',
    'flyout_display': 'hidden',
    'version_selector': True,
    'language_selector': True,
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False,
    'version_selector': True,
    'logo_only': True,
    'display_version': False,
    'includehidden': True
}

# Epilog Constants for rst
rst_epilog = """
.. |packname| replace:: {0}
.. |packnamebold| replace:: **{0}**
.. |packnamecode| replace:: ``{0}``
.. |packnameblend| replace:: ``{0}.blend``
.. |packnameext| replace:: {1}
.. |packnameextbold| replace:: **{1}**
.. |packnameblendver| replace:: ``{0} <version>.blend``
.. |packnameblendold| replace:: ``{0} <old version>.blend``
.. |packnameblendnew| replace:: ``{0} <new version>.blend``
.. |packnameblendoldold| replace:: ``{0} <old version>.blend.old``
.. |packnamezip| replace:: ``{0}.zip``
.. |packnamezipver| replace:: ``{0} <version>.zip``
.. |packnamezipold| replace:: ``{0} <old version>.zip``
.. |packnamezipnew| replace:: ``{0} <new version>.zip``
.. |blenderminver| replace:: **Blender 4.2 LTS**
.. |blenderextminver| replace:: **Blender 4.5 LTS**
"""
rst_epilog = rst_epilog.format("Breathfang's Geometry Nodes Toolset Pack", "Breathfang's Geometry Nodes Toolset Extension Pack")