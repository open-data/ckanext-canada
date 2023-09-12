from yaml import load
from six import string_types


def _get_line_number(fileobj, phrase, encoding):
    line = fileobj.readline().decode(encoding)
    num = 1
    while line:
        if phrase in line:
            return num
        line = fileobj.readline().decode(encoding)
        num += 1
    return None


def _extract_string(fileobj, key, value, encoding, comments):
    fileobj.seek(0)
    lineno = _get_line_number(fileobj, '%s: %s' % (key, value), encoding)
    while lineno:
        yield (lineno,
               '',
               value,
               comments)
        lineno = _get_line_number(fileobj, '%s: %s' % (key, value), encoding)


def extract_pd(fileobj, keywords, comment_tags, options):
    """Extract messages from XXX files.

    :param fileobj: the file-like object the messages should be extracted
                    from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: ``iterator``
    """
    encoding = options.get('encoding', 'utf-8')
    chromo = load(fileobj.read().decode(encoding))

    pd_type = chromo.get('dataset_type', 'unknown')

    # PD Type Title
    title = chromo.get('title')
    if isinstance(title, string_types):
        for lineno, funcname, message, comments in \
        _extract_string(fileobj, 'title', title, encoding, ['Title for PD Type: %s' % pd_type]):
            yield (lineno, funcname, message, comments)

    # PD Type Short Label
    label = chromo.get('shortname')
    if isinstance(label, string_types):
        for lineno, funcname, message, comments in \
        _extract_string(fileobj, 'shortname', label, encoding, ['Label for PD Type: %s' % pd_type]):
            yield (lineno, funcname, message, comments)

    # PD Type Description
    notes = chromo.get('notes')
    if isinstance(notes, string_types):
        for lineno, funcname, message, comments in \
        _extract_string(fileobj, 'notes', notes, encoding, ['Description for PD Type: %s' % pd_type]):
            yield (lineno, funcname, message, comments)

    # PD Type Resource Titles
    resources = chromo.get('resources')
    if resources:
        base_title = resources[0].get('title')  # normal resource title
        if isinstance(base_title, string_types):
            for lineno, funcname, message, comments in \
            _extract_string(fileobj, 'title', base_title, encoding, ['Resource Title for PD Type: %s' % pd_type]):
                yield (lineno, funcname, message, comments)

        base_trigger_strings = resources[0].get('trigger_strings')  # normal resource sql error messages
        if base_trigger_strings:
            for k, v in base_trigger_strings.items():
                if isinstance(v, string_types):
                    for lineno, funcname, message, comments in \
                    _extract_string(fileobj, k, v, encoding, ['SQL Trigger String for PD Type: %s' % pd_type]):
                        yield (lineno, funcname, message, comments)

        if len(resources) > 1:  # nil resource
            nil_title = resources[1].get('title')  # nil resource title
            if isinstance(nil_title, string_types):
                for lineno, funcname, message, comments in \
                _extract_string(fileobj, 'title', nil_title, encoding, ['NIL Resource Title for PD Type: %s' % pd_type]):
                    yield (lineno, funcname, message, comments)

            nil_triggers_strings = resources[1].get('trigger_strings')  # nil resource sql error messages
            if nil_triggers_strings:
                for k, v in nil_triggers_strings.items():
                    if isinstance(v, string_types):
                        for lineno, funcname, message, comments in \
                        _extract_string(fileobj, k, v, encoding, ['SQL Trigger String for PD Type: %s' % pd_type]):
                            yield (lineno, funcname, message, comments)
