# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys

sys.path.append(os.curdir)
from pelicanconf import *

# If your site is available via HTTPS, make sure SITEURL begins with https://
SITEURL = "https://emmatyping.dev"
RELATIVE_URLS = False

HTML_MIN = True
INLINE_CSS_MIN = True
INLINE_JS_MIN = True
CSS_MIN = True
JS_MIN = True

DELETE_OUTPUT_DIRECTORY = True

RELATIVE_URLS = False