import os
AUTHOR = 'Emma Smith'
SITENAME = "Emma's Blog"
SITEURL = ""

PATH = "content"

TIMEZONE = 'America/Los_Angeles'
DEFAULT_LANG = 'en'
COPYRIGHT_YEAR = '2025'

THEME = 'terminimal'

FEED_DOMAIN = "https://emmatyping.dev"
FEED_ALL_ATOM = "feeds/all.atom.xml"
CATEGORY_FEED_ATOM = "feeds/{slug}.atom.xml"
TAG_FEED_ATOM = "feeds/{slug}/atom.xml"
FEED_ALL_RSS = "feeds/all.rss.xml"
CATEGORY_FEED_RSS = "feeds/{slug}.rss.xml"
TAG_FEED_RSS = "feeds/{slug}/rss.xml"
RSS_FEED_SUMMARY_ONLY = False

STATIC_PATHS = ["static"]

MENUITEMS = (
    ("Home", "$BASE_URL/index.html"),
    ("About", "$BASE_URL/pages/about.html"),
    ("Contact", "$BASE_URL/pages/contact.html"),
    ("GitHub", "https://github.com/emmatyping"),
    ("Mastodon", "https://hachyderm.io/@emmatyping"),
    ("BlueSky", "https://bsky.app/profile/emmatyping.dev"),
)

DEFAULT_PAGINATION = 2

JINJA_ENVIRONMENT = {
    'extensions': ['jinja2.ext.loopcontrols']
}

ACCENT_COLOR = 'blue'
BACKGROUND_COLOR = 'dark'

PLUGINS = [
    "pelican.plugins.neighbors",
    "pelican.plugins.minify",
]

CSS_MIN = True
JS_MIN = True

RELATIVE_URLS = True

MASTODON_URL = "https://hachyderm.io/@emmatyping"
