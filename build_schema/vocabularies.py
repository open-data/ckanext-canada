# -*- coding: UTF-8 -*-

VOCABULARY_GC_CORE_SUBJECT_THESAURUS = u'gc_core_subject_thesaurus'
VOCABULARY_ISO_TOPIC_CATEGORIES = u'iso_topic_categories'
VOCABULARY_GC_GEOGRAPHIC_REGION = u'gc_geographic_region'


def read_from_sheet(sheet):
    """
    Read xls vocabulary sheet and return a vocabulary dict like: {
        proposedName: [
            {'id': (if avail), 'eng': eng_name, 'fra': fra_name},
            ...],
        ...}
    """
    out = {}
    current_vocab = proposed_name = None
    for i in range(sheet.nrows):
        row = sheet.row(i)
        cell = [x.value.strip() if hasattr(x.value, 'strip') else int(x.value)
            for x in row]
        if not cell[0]:
            current_vocab = proposed_name = None
        elif proposed_name is None:
            proposed_name = cell[0]
        elif current_vocab is None:
            if cell[0] in (u'Controlled Vocabulary', u'Terms'):
                current_vocab = 'skip one'
        elif current_vocab == 'skip one':
            current_vocab = []
            out[proposed_name] = current_vocab
        elif cell[4]:
            key = u'org' + unicode(cell[4])
            if cell[1]:
                if cell[1] == cell[3]:
                    key = cell[1]
                else:
                    key = u'-'.join((cell[1], cell[3]))
            current_vocab.append({
                'id': cell[4],
                'key': key.lower().replace(' ', ''),
                'eng': cell[0],
                'fra': cell[2],
                })
        elif not cell[2] and not cell[3]:
            if cell[0][2] == ' ' and cell[0][:2].isupper():
                current_vocab.append({
                    'id': cell[0].split(' ', 1)[0],
                    'eng': cell[0].split(' ', 1)[1],
                    'fra': cell[1].split(' ', 1)[1],
                    })
            else:
                current_vocab.append({
                    'eng': cell[0],
                    'fra': cell[1],
                    })
        elif not cell[3] and cell[1]:
            current_vocab.append({
                'id': cell[2],
                'eng': cell[0],
                'fra': cell[1],
                })
            if proposed_name == 'topicCategory':
                current_vocab[-1]['subject_ids'] = [
                    i.strip() for i in cell[5].split(',')]
            elif proposed_name == 'formatName':
                if cell[5]:
                    current_vocab[-1]['replaces'] = [
                        i.strip() for i in cell[5].split(',')]
                current_vocab[-1]['openness_score'] = cell[6]

        else:
            current_vocab.append({
                'id': u'-'.join((cell[1], cell[3])) if cell[1] else u'',
                'eng': cell[0],
                'fra': cell[2],
                })
    return out



