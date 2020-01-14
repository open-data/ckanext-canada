from ckanapi import LocalCKAN
from dateutil import parser
import logging
import nltk
import pysolr
import simplejson as json
from pylons import config
from ckanext.scheming.helpers import scheming_get_preset

SEARCH_INTEGRATION_ENABLED_OPTION = "ckanext.canada.adv_search_enabled"
SEARCH_INTEGRATION_URL_OPTION = "ckanext.canada.adv_search_solr_core"
SEARCH_INTEGRATION_OD_URL_EN_OPTION = "ckanext.canada.adv_search_od_base_url_en"
SEARCH_INTEGRATION_OD_URL_FR_OPTION = "ckanext.canada.adv_search_od_base_url_fr"
SEARCH_INTEGRATION_ENABLED = False
SEARCH_INTEGRATION_LOADING_PAGESIZE = 100


def get_summary(original_text, lang, max_sentences=4):
    if lang == 'fr':
        sent_tokenizer_fr = nltk.data.load('tokenizers/punkt/french.pickle')
        sentences = sent_tokenizer_fr.tokenize(original_text)
    else:
        sent_tokenizer_en = nltk.data.load('tokenizers/punkt/english.pickle')
        sentences = sent_tokenizer_en.tokenize(original_text)
    sentence_total = max_sentences if len(sentences) >= max_sentences else len(sentences)
    if len(sentences) > sentence_total:
        summary_text = " ".join(sentences[0:sentence_total])
    else:
        summary_text = original_text
    return summary_text


def scheming_choices_label_by_value(choices):
    choices_en = {}
    choices_fr = {}

    for choice in choices:
        choices_en[choice['value']] = choice['label']['en']
        choices_fr[choice['value']] = choice['label']['fr']
    return {'en': choices_en, 'fr': choices_fr}


def add_to_search_index(data_dict_id, in_bulk=False):

    log = logging.getLogger('ckan')
    od_search_solr_url = config.get(SEARCH_INTEGRATION_URL_OPTION, "")
    od_search_enabled = config.get(SEARCH_INTEGRATION_ENABLED_OPTION, False)
    od_search_od_url_en = config.get(SEARCH_INTEGRATION_OD_URL_EN_OPTION, "https://open.canada.ca/data/en/dataset/")
    od_search_od_url_fr = config.get(SEARCH_INTEGRATION_OD_URL_FR_OPTION, "https://ouvert.canada.ca/data/fr/dataset/")

    # Retrieve the full record - it has additional information including organization title and metadata modified date
    # that are not available in the regular data dict

    portal = LocalCKAN()
    data_dict = portal.action.package_show(id=data_dict_id)

    if not od_search_enabled:
        return
    try:
        subject_codes = scheming_choices_label_by_value(scheming_get_preset('canada_subject')['choices'])
        type_codes = scheming_choices_label_by_value(scheming_get_preset('canada_resource_related_type')['choices'])
        collection_codes = scheming_choices_label_by_value(scheming_get_preset('canada_collection')['choices'])
        juristiction_codes = scheming_choices_label_by_value(scheming_get_preset('canada_jurisdiction')['choices'])
        resource_type_codes = scheming_choices_label_by_value(scheming_get_preset('canada_resource_type')['choices'])
        frequency_codes = scheming_choices_label_by_value(scheming_get_preset('canada_frequency')['choices'])

        org_title = data_dict['organization']['title'].split('|')
        owner_org_title_en = org_title[0].strip()
        owner_org_title_fr = org_title[1].strip()

        subjects_en = []
        subjects_fr = []
        subjects = json.loads(data_dict['subject']) if \
            isinstance(data_dict['subject'], str) else data_dict['subject']
        for s in subjects:
            subjects_en.append(subject_codes['en'][s].replace(",", ""))
            subjects_fr.append(subject_codes['fr'][s].replace(",", ""))

        resource_type_en = []
        resource_type_fr = []
        resource_fmt = []
        resource_title_en = []
        resource_title_fr = []
        for r in data_dict['resources']:
            resource_type_en.append(
                resource_type_codes['en'][r['resource_type']]
                if r['resource_type'] in resource_type_codes['en'] else '')
            resource_type_fr.append(
                resource_type_codes['fr'][r['resource_type']]
                if r['resource_type'] in resource_type_codes['fr'] else '')
            resource_fmt.append(r['format'])

            resource_name = json.loads(r['name_translated']) if \
                isinstance(r['name_translated'], str) else r['name_translated']
            if 'en' in resource_name:
                resource_title_en.append(resource_name['en'])
            elif 'en-t-fr' in resource_name:
                resource_title_en.append(resource_name['en-t-fr'])
            if 'fr' in resource_name:
                resource_title_fr.append(resource_name['fr'].strip())
            elif 'fr-t-en' in resource_name:
                resource_title_fr.append(resource_name['fr-t-en'].strip())
        display_options = []
        if 'display_flags' in data_dict:
            for d in data_dict['display_flags']:
                display_options.append(d)
        notes_translated = json.loads(data_dict['notes_translated']) if \
            isinstance(data_dict['notes_translated'], str) else data_dict['notes_translated']
        title_translated = json.loads(data_dict['title_translated']) if \
            isinstance(data_dict['title_translated'], str) else data_dict['title_translated']
        od_obj = {
            'portal_type_en_s': type_codes['en'][data_dict['type']],
            'portal_type_fr_s': type_codes['fr'][data_dict['type']],
            'collection_type_en_s': collection_codes['en'][data_dict['collection']],
            'collection_type_fr_s': collection_codes['fr'][data_dict['collection']],
            'jurisdiction_en_s': juristiction_codes['en'][data_dict['jurisdiction']],
            'jurisdiction_fr_s': juristiction_codes['fr'][data_dict['jurisdiction']],
            'owner_org_title_en_s': owner_org_title_en,
            'owner_org_title_fr_s': owner_org_title_fr,
            'subject_en_s': subjects_en,
            'subject_fr_s': subjects_fr,
            'resource_type_en_s': list(set(resource_type_en)),
            'resource_type_fr_s': list(set(resource_type_fr)),
            'update_cycle_en_s': frequency_codes['en'][data_dict['frequency']],
            'update_cycle_fr_s': frequency_codes['fr'][data_dict['frequency']],
            'id_name_s': data_dict['name'],
            'id': data_dict['name'],
            'owner_org_s': data_dict['owner_org'],
            'author_txt': data_dict['author'] if 'author' in data_dict else '',
            'description_txt_en': notes_translated['en'] if 'en' in data_dict['notes_translated'] else '',
            'description_txt_fr': notes_translated['fr'] if 'fr' in data_dict['notes_translated'] else '',
            'description_xlt_txt_fr': notes_translated['fr-t-en'] if 'fr-t-en' in notes_translated else '',
            'description_xlt_txt_en': notes_translated['en-t-fr'] if 'en-t-fr' in notes_translated else '',
            'title_en_s': title_translated['en'] if 'en' in title_translated else '',
            'title_fr_s': title_translated['fr'] if 'fr' in title_translated else '',
            'title_xlt_fr_s': title_translated['fr-t-en'] if 'fr-t-en' in title_translated else '',
            'title_xlt_en_s': title_translated['en-t-fr'] if 'en-t-fr' in title_translated else '',
            'resource_format_s': list(set(resource_fmt)),
            'resource_title_en_s': resource_title_en,
            'resource_title_fr_s': resource_title_fr,
            'last_modified_tdt': parser.parse(data_dict['metadata_modified']).replace(microsecond=0).isoformat() + 'Z',
            'ogp_link_en_s': '{0}{1}'.format(od_search_od_url_en, data_dict['name']),
            'ogp_link_fr_s': '{0}{1}'.format(od_search_od_url_fr, data_dict['name']),
            'display_options_s': display_options
        }

        if 'en' in notes_translated:
            od_obj['desc_summary_txt_en'] = get_summary(notes_translated['en'].strip(), 'en')
        elif 'en-t-fr' in notes_translated:
            od_obj['desc_summary_txt_en'] = get_summary(notes_translated['en-t-fr'].strip(), 'en')
        if 'fr' in notes_translated:
            od_obj['desc_summary_txt_fr'] = get_summary(notes_translated['fr'].strip(), 'fr')
        elif 'en-t-fr' in notes_translated:
            od_obj['desc_summary_txt_fr'] = get_summary(notes_translated['fr-t-en'].strip(), 'fr')

        keywords = json.loads(data_dict['keywords']) if \
            isinstance(data_dict['keywords'], str) else data_dict['keywords']
        if 'en' in keywords:
            od_obj['keywords_en_s'] = keywords['en']
        elif 'en-t-fr' in keywords:
            od_obj['keywords_xlt_en_s'] = keywords['en-t-fr']
        if 'fr' in keywords:
            od_obj['keywords_fr_s'] = keywords['fr']
        elif 'fr-t-en' in keywords:
            od_obj['keywords_xlt_fr_s'] = keywords['fr-t-en']

        solr = pysolr.Solr(od_search_solr_url)
        if in_bulk:
            solr.add([od_obj])
        else:
            solr.delete(id=od_obj['id'])
            solr.add([od_obj])
            solr.commit()
    except Exception as x:
        log.error("Exception: {} {}".format(x.message, x.args))


def delete_from_search_index(id):

    log = logging.getLogger('ckan.logic')
    od_search_solr_url = config.get(SEARCH_INTEGRATION_URL_OPTION, "")
    od_search_enabled = config.get(SEARCH_INTEGRATION_ENABLED_OPTION, False)

    if not od_search_enabled:
        return
    try:
        solr = pysolr.Solr(od_search_solr_url)
        q = 'id:"{0}"'.format(id)
        solr.delete(q=q)
        solr.commit()
    except Exception as x:
        log.error(x.message)


def rebuild_search_index(portal, unindexed_only=False, refresh_index=False):

    log = logging.getLogger('ckan.logic')
    data_sets = portal.action.package_list()
    od_search_solr_url = config.get(SEARCH_INTEGRATION_URL_OPTION, "")

    try:
        search_solr = pysolr.Solr(od_search_solr_url)
        if not unindexed_only and not refresh_index:
            search_solr.delete(q='*:*')
        row_counter = 0
        for dsid in data_sets:
            if unindexed_only:
                sr = search_solr.search(q='id:{0}'.format(dsid))
                if len(sr.docs) > 0:
                    continue
            add_to_search_index(dsid, in_bulk=True)
            row_counter += 1
            if row_counter % SEARCH_INTEGRATION_LOADING_PAGESIZE == 0:
                print("{0} Records Indexed".format(row_counter))
        search_solr.commit()
        print("Total {0} Records Indexed".format(row_counter))
    except Exception as x:
        log.error("Exception: {} {}".format(x.message, x.args))


