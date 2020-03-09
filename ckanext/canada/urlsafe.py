# -*- coding: utf-8 -*-

import codecs
import re

def url_part_escape(orig):
    """
    simple encoding for url-parts where all non-alphanumerics are
    wrapped in e.g. _xxyyzz_ blocks w/hex UTF-8 xx, yy, zz values

    used for safely including arbitrary unicode as part of a url path
    all returned characters will be in [a-zA-Z0-9_-]
    """
    return '_'.join(
        codecs.encode(s.encode('utf-8'), 'hex').decode('ascii') if i % 2 else s
        for i, s in enumerate(
            re.split(u'([^-a-zA-Z0-9]+)', orig)
        )
    )

def url_part_unescape(urlpart):
    """
    reverse url_part_escape
    """
    return ''.join(
        codecs.decode(s, 'hex').decode('utf-8') if i % 2 else s
        for i, s in enumerate(urlpart.split('_'))
    )
