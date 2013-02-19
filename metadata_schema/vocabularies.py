# -*- coding: UTF-8 -*-

VOCABULARY_GC_CORE_SUBJECT_THESAURUS = u'gc_core_subject_thesaurus'
VOCABULARY_ISO_TOPIC_CATEGORIES = u'iso_topic_categories'

GC_CORE_SUBJECT_THESAURUS = {
    'eng': {
        'AA': u'Arts, Music, Literature',
        'AG': u'Agriculture',
        'EC': u'Economics and Industry',
        'ET': u'Education and Training',
        'FM': u'Form descriptors',
        'GV': u'Government and Politics',
        'HE': u'Health and Safety',
        'HI': u'History and Archaeology',
        'IN': u'Information and Communications',
        'LB': u'Labour',
        'LN': u'Language and Linguistics',
        'LW': u'Law',
        'MI': u'Military',
        'NE': u'Nature and Environment',
        'PE': u'Persons',
        'PR': u'Processes',
        'SO': u'Society and Culture',
        'ST': u'Science and Technology',
        'TR': u'Transport',
        },
    'fra': {
        'AA': u'Arts, musique, littérature',
        'AG': u'Agriculture',
        'EC': u'Économie et industrie',
        'ET': u'Éducation et formation',
        'GV': u'Gouvernement et vie politique',
        'HE': u'Santé et sécurité',
        'HI': u'Histoire et archéologie',
        'IN': u'Information et communication',
        'LB': u'Travail et emploi',
        'LN': u'Langue et linguistique',
        'LW': u'Droit',
        'MI': u'Histoire et science militaire',
        'NE': u'Nature et environnement',
        'PE': u'Personnes',
        'PR': u'Liens et fonctions',
        'SO': u'Société et culture',
        'ST': u'Sciences et technologie',
        'TR': u'Transport',
        },
    }


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
        else:
            current_vocab.append({
                'id': u'-'.join((cell[1], cell[3])) if cell[1] else u'',
                'eng': cell[0],
                'fra': cell[2],
                })
    return out



