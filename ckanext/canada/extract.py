from yaml import load
from yaml.loader import SafeLoader
from six import string_types


class SafeLineLoader(SafeLoader):
    def __init__(self, stream):
        super(SafeLineLoader, self).__init__(stream)
        self.line_numbers = {}

    def construct_scalar(self, node):
        if node.value in self.line_numbers:
            self.line_numbers[node.value].append(node.start_mark.line + 1)
        else:
            self.line_numbers[node.value] = [node.start_mark.line + 1]
        return super(SafeLineLoader, self).construct_scalar(node)

    def get_single_data(self):
        data = super(SafeLineLoader, self).get_single_data()
        return self.line_numbers, data


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
    line_numbers, chromo = load(fileobj.read().decode(encoding), Loader=SafeLineLoader)

    pd_type = chromo.get('dataset_type', 'unknown')

    # PD Type Title
    title = chromo.get('title')
    if isinstance(title, string_types):
        for line_number in line_numbers.get(title, [0]):
            yield (line_number, '', title, ['Title for PD Type: %s' % pd_type])

    # PD Type Short Label
    label = chromo.get('shortname')
    if isinstance(label, string_types):
        for line_number in line_numbers.get(label, [0]):
            yield (line_number, '', label, ['Label for PD Type: %s' % pd_type])

    # PD Type Description
    notes = chromo.get('notes')
    if isinstance(notes, string_types):
        for line_number in line_numbers.get(notes, [0]):
            yield (line_number, '', notes, ['Description for PD Type: %s' % pd_type])

    # PD Type Resource Titles
    resources = chromo.get('resources')
    if resources:
        base_title = resources[0].get('title')  # normal resource title
        if isinstance(base_title, string_types):
            for line_number in line_numbers.get(base_title, [0]):
                yield (line_number, '', base_title, ['Resource Title for PD Type: %s' % pd_type])

        base_trigger_strings = resources[0].get('trigger_strings')  # normal resource sql error messages
        if base_trigger_strings:
            for k, v in base_trigger_strings.items():
                if isinstance(v, string_types):
                    for line_number in line_numbers.get(v, [0]):
                        yield (line_number, '', v, ['SQL Trigger String for PD Type: %s' % pd_type])

        if len(resources) > 1:  # nil resource
            nil_title = resources[1].get('title')  # nil resource title
            if isinstance(nil_title, string_types):
                for line_number in line_numbers.get(nil_title, [0]):
                    yield (line_number, '', nil_title, ['NIL Resource Title for PD Type: %s' % pd_type])

            nil_triggers_strings = resources[1].get('trigger_strings')  # nil resource sql error messages
            if nil_triggers_strings:
                for k, v in nil_triggers_strings.items():
                    if isinstance(v, string_types):
                        for line_number in line_numbers.get(v, [0]):
                            yield (line_number, '', v, ['SQL Trigger String for PD Type: %s' % pd_type])
