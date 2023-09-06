from yaml import load
from six import string_types


def _get_line_number(fileobj, phrase, skip=0):
    return 0


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
        yield (_get_line_number(fileobj, 'title: %s' % title),
               '',
               title,
               ['Title for PD Type: %s' % pd_type])

    # PD Type Short Label
    label = chromo.get('shortname')
    if isinstance(label, string_types):
        yield (_get_line_number(fileobj, 'shortname: %s' % label),
               '',
               label,
               ['Label for PD Type: %s' % pd_type])

    # PD Type Description
    notes = chromo.get('notes')
    if isinstance(notes, string_types):
        yield (_get_line_number(fileobj, 'notes: %s' % notes),
               '',
               notes,
               ['Description for PD Type: %s' % pd_type])

    # PD Type Resource Titles
    resources = chromo.get('resources')
    if resources:
        base_title = resources[0].get('title')  # normal resource title
        if isinstance(base_title, string_types):
            yield(_get_line_number(fileobj, 'title: %s' % base_title, skip=1),
                  '',
                  base_title,
                  ['Resource Title for PD Type: %s' % pd_type])

        base_trigger_strings = resources[0].get('trigger_strings')  # normal resource sql error messages
        if base_trigger_strings:
            for k, v in base_trigger_strings.items():
                if isinstance(v, string_types):
                    yield(_get_line_number(fileobj, '%s:' % k),
                          '',
                          v,
                          ['SQL Error Message for PD Type: %s' % pd_type])

        if len(resources) > 1:  # nil resource
            nil_title = resources[1].get('title')  # nil resource title
            if isinstance(nil_title, string_types):
                yield(_get_line_number(fileobj, 'title: %s' % nil_title),
                      '',
                      nil_title,
                      ['NIL Resource Title for PD Type: %s' % pd_type])

            nil_triggers_strings = resources[1].get('trigger_strings')  # nil resource sql error messages
            if nil_triggers_strings:
                for k, v in nil_triggers_strings.items():
                    if isinstance(v, string_types):
                        yield(_get_line_number(fileobj, '%s:' % k),
                            '',
                            v,
                            ['SQL Error Message for PD Type: %s' % pd_type])
