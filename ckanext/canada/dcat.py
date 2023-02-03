#!/usr/bin/env python
# -*- coding: utf-8 -*-
from functools import partial

from rdflib import URIRef, BNode, Literal
from rdflib.namespace import RDF
from ckanext.dcat.profiles import RDFProfile, DCT, DCAT, VCARD
from ckan.lib.helpers import url_for
from ckanext.scheming import helpers as scheming_helpers


def _smart_add(g, dataset_dict, dataset_ref, type_, key, sc_key=None):
    if sc_key:
        preset = scheming_helpers.scheming_get_preset(sc_key)

    try:
        values = dataset_dict[key + '_translated']
    except KeyError:
        values = dataset_dict[key]

    if not isinstance(values, list):
        values = [values]

    for value in values:
        if sc_key:
            for c in preset['choices']:
                if c['value'] == value:
                    value = c.get('label', value)
                    break

        if isinstance(value, dict):
            for k, v in value.iteritems():
                if not isinstance(v, list):
                    v = [v]

                for vv in v:
                    g.add((dataset_ref, type_, Literal(vv, lang=k)))
        elif value is None:
            return
        else:
            g.add((dataset_ref, type_, Literal(value)))


class CanadaDCATProfile(RDFProfile):
    def graph_from_dataset(self, dataset_dict, dataset_ref):
        g = self.g

        _add = partial(_smart_add, g, dataset_dict, dataset_ref)

        g.bind('dct', DCT)
        g.bind('dcat', DCAT)
        g.bind('vcard', VCARD)

        g.add((dataset_ref, RDF.type, DCAT.Dataset))

        _add(DCT.title, 'title')
        _add(DCT.description, 'notes')
        _add(DCT.issued, 'date_published')
        _add(DCT.modified, 'metadata_modified')
        _add(DCT.publisher, 'org_title_at_publication')
        _add(DCT.accuralPeriodicity, 'frequency', 'canada_frequency')
        _add(DCT.identifier, 'id')
        _add(DCT.spatial, 'spatial')
        # This *should* be the period (from start to finish) that the dataset
        # covers, however we don't seem to have a field for this.
        # _add(DCT.temporal, '')

        g.add((dataset_ref, DCT.language, Literal('en')))
        g.add((dataset_ref, DCT.language, Literal('fr')))

        _add(DCAT.theme, 'subject', 'canada_subject')
        _add(DCAT.keyword, 'keywords')
        g.add((dataset_ref, DCAT.landing_page, Literal(
            url_for(
                'package.read',
                id=dataset_dict['id'],
                qualified=True
            )
        )))

        contact_details = BNode()
        g.add((contact_details, RDF.type, VCARD.organization))
        g.add((dataset_ref, DCAT.contact_point, contact_details))

        g.add((contact_details, VCARD.hasEmail, Literal(
            dataset_dict['maintainer_email']
        )))

        for resource_dict in dataset_dict.get('resources', []):
            resource = URIRef(url_for(
                'package.resource_read',
                id=resource_dict['id'],
                qualified=True
            ))

            _r_add = partial(_smart_add, g, resource_dict, resource)

            g.add((dataset_ref, DCAT.distrubtion, resource))
            g.add((resource, RDF.type, DCAT.Distribution))

            _r_add(DCT.title, 'name')
            _r_add(DCT.description, 'description')
            _r_add(DCT.issued, 'created')
            _r_add(DCT.modified, 'last_modified')
            _r_add(DCAT.media_type, 'mimetype')
            _r_add(DCT['format'], 'format')
            _r_add(DCAT.access_url, 'url')
            _smart_add(
                g,
                dataset_dict,
                resource,
                DCT.license,
                'license_title'
            )
