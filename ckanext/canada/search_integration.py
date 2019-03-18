import datetime
import logging
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

def scheming_choices_label_by_value(choices):
    choices_en = {}
    choices_fr = {}

    for choice in choices:
        choices_en[choice['value']] = choice['label']['en']
        choices_fr[choice['value']] = choice['label']['fr']
    return {'en': choices_en, 'fr': choices_fr}


def add_to_search_index(data_dict, in_bulk=False):

    log = logging.getLogger('ckan.logic')
    od_search_solr_url = config.get(SEARCH_INTEGRATION_URL_OPTION, "")
    od_search_enabled = config.get(SEARCH_INTEGRATION_ENABLED_OPTION, False)
    od_search_od_url_en = config.get(SEARCH_INTEGRATION_OD_URL_EN_OPTION, "https://open.canada.ca/data/en/dataset/")
    od_search_od_url_fr = config.get(SEARCH_INTEGRATION_OD_URL_FR_OPTION, "https://ouvert.canada.ca/data/fr/dataset/")

    if not od_search_enabled:
        return
    try:
        subject_codes = scheming_choices_label_by_value(scheming_get_preset('canada_subject')['choices'])
        type_codes = scheming_choices_label_by_value(scheming_get_preset('canada_resource_related_type')['choices'])
        collection_codes = scheming_choices_label_by_value(scheming_get_preset('canada_collection')['choices'])
        juristiction_codes = scheming_choices_label_by_value(scheming_get_preset('canada_jurisdiction')['choices'])
        resource_type_codes = scheming_choices_label_by_value(scheming_get_preset('canada_resource_type')['choices'])
        frequency_codes = scheming_choices_label_by_value(scheming_get_preset('canada_frequency')['choices'])

        org_title_at_publication = json.loads(data_dict['org_title_at_publication']) if \
            isinstance(data_dict['org_title_at_publication'], str) else data_dict['org_title_at_publication']
        owner_org_title_en = org_title_at_publication['en']
        owner_org_title_fr = org_title_at_publication['fr']

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
            elif 'fr-t-en' in resource_name:
                resource_title_en.append(resource_name['fr-t-en'])
            if 'fr' in resource_name:
                resource_title_fr.append(resource_name['fr'].strip())
            elif 'en-t-fr' in resource_name:
                resource_title_fr.append(resource_name['en-t-fr'].strip())

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
            'description_xlt_txt_en': notes_translated['en-t-fr'] if 'en-t-f-r' in notes_translated else '',
            'title_en_s': title_translated['en'].encode('utf-8').strip() if 'en' in title_translated else '',
            'title_fr_s': title_translated['fr'].encode('utf-8').strip() if 'fr' in title_translated else '',
            'title_xlt_fr_s': title_translated['fr-t-en'] if 'fr-t-en' in title_translated else '',
            'title_xlt_en_s': title_translated['en-t-fr'] if 'en-t-fr' in title_translated else '',
            'resource_format_s': list(set(resource_fmt)),
            'resource_title_en_s': resource_title_en,
            'resource_title_fr_s': resource_title_fr,
            'last_modified_tdt': datetime.datetime.now().replace(microsecond=0).isoformat() + 'Z',
            'ogp_link_en_s': '{0}{1}'.format(od_search_od_url_en, data_dict['name']),
            'ogp_link_fr_s': '{0}{1}'.format(od_search_od_url_fr, data_dict['name']),
        }

        keywords = json.loads(data_dict['keywords']) if \
            isinstance(data_dict['keywords'], str) else data_dict['keywords']
        if 'en' in keywords:
            od_obj['keywords_en_s'] = keywords['en']
        elif 'fr-t-en' in keywords:
            od_obj['keywords_en_s'] = keywords['fr-t-en']
        if 'fr' in keywords:
            od_obj['keywords_fr_s'] = keywords['fr']
        elif 'en-t-fr' in keywords:
            od_obj['keywords_fr_s'] = keywords['en-t-fr']

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


def rebuild_search_index(portal, unidexed_only=False):

    log = logging.getLogger('ckan.logic')
    data_sets = portal.action.package_list()
    od_search_solr_url = config.get(SEARCH_INTEGRATION_URL_OPTION, "")

    try:
        search_solr = pysolr.Solr(od_search_solr_url)
        if not unidexed_only:
            search_solr.delete(q='*:*')
        row_counter = 0
        for dsid in data_sets:
            if unidexed_only:
                sr = search_solr.search(q='id:{0}'.format(dsid))
                if len(sr.docs) > 0:
                    continue
            dataset = portal.action.package_show(id=dsid)
            add_to_search_index(dataset, in_bulk=True)
            row_counter += 1
            if row_counter % SEARCH_INTEGRATION_LOADING_PAGESIZE == 0:
                print("{0} Records Indexed".format(row_counter))
        search_solr.commit()
        print("Total {0} Records Indexed".format(row_counter))
    except Exception as x:
        log.error("Exception: {} {}".format(x.message, x.args))


