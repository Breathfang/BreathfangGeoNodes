import datetime

master_doc = 'index'

# Project Setup
html_title = 'Breathfang\'s Geometry Nodes Toolset Pack'  # Optional: title shown in browser tab
project = 'Breathfang\'s Geometry Nodes Toolset Pack'  # This shows up in the header and browser title

html_static_path = ['_static']
html_logo = '_static/img/logo/logo.png'

version = 'v1.1.0-preview'
release = 'v1.1.0-preview'
author = 'Breathfang'

copyright = f'2025, Breathfang (Formerly Drageon DB)'

if datetime.datetime.now().year > 2025:
    copyright = f'2025-{datetime.datetime.now().year}, Breathfang (Formerly Drageon DB)'

# Project Extensions
extensions = [
    'sphinx_rtd_theme',
]

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

rst_epilog = """
.. |packname| replace:: Breathfang's Geometry Nodes Toolset Pack
.. |packnamebold| replace:: **Breathfang's Geometry Nodes Toolset Pack**
"""