#!/usr/bin/env python
# -*- coding: utf-8 -*-
from functools import partial

from rdflib import URIRef, BNode, Literal
from rdflib.namespace import RDF
from ckanext.dcat.profiles import RDFProfile, DCT, DCAT, VCARD
from ckan.lib.helpers import url_for


def _smart_add(g, dataset_dict, dataset_ref, type_, key):
    try:
        value = dataset_dict[key + '_translated']
    except KeyError:
        value = dataset_dict[key]

    if isinstance(value, dict):
        for k, v in value.iteritems():
            if not isinstance(v, list):
                v = [v]

            for vv in v:
                g.add((dataset_ref, type_, Literal(vv, lang=k)))
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
        # FIXME: ckanext-scheming lookup..
        _add(DCT.accuralPeriodicity, 'frequency')
        _add(DCT.identifier, 'id')
        # _add(DCT.spatial, '')
        # _add(DCT.temporal, '')

        g.add((dataset_ref, DCT.language, Literal('en')))
        g.add((dataset_ref, DCT.language, Literal('fr')))

        for subject in dataset_dict.get('subject', []):
            # FIXME: ckanext-scheming lookup..
            g.add((dataset_ref, DCAT.theme, Literal(subject)))

        _add(DCAT.keyword, 'keywords')
        g.add((dataset_ref, DCAT.landing_page, Literal(
            url_for(
                controller='package',
                action='read',
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
