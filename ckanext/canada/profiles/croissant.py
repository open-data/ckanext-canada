import ast
import json
from rdflib import Literal, Namespace, URIRef, BNode
from rdflib.namespace import DCTERMS as DCT, RDF, XSD
from ckan.plugins.toolkit import config
from ckanext.dcat.profiles.croissant import CroissantProfile, JSONLD_CONTEXT, CleanedURIRef
from ckanext.dcat.utils import resource_uri
from bs4 import BeautifulSoup

JSONLD_CONTEXT["name"] = {"@container": "@language"}
JSONLD_CONTEXT["description"] = {"@container": "@language"}
JSONLD_CONTEXT["samplingRate"] = "cr:samplingRate"
JSONLD_CONTEXT["equivalentProperty"] = "cr:equivalentProperty"

SCHEMA = Namespace("https://schema.org/")
CR = Namespace("http://mlcommons.org/croissant/")

MIME_MAP = {
    "CSV": "text/csv",
    "JSON": "application/json",
    "JSONL": "application/jsonl",
    "XML": "application/xml",
    "HTML": "text/html",
    "PDF": "application/pdf",
    "TXT": "text/plain",
    "TSV": "text/tab-separated-values",
    "ZIP": "application/zip",
    "GZ": "application/gzip",
    "TAR": "application/x-tar",
    "PARQUET": "application/vnd.apache.parquet",
    "XLS": "application/vnd.ms-excel",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "GEOJSON": "application/geo+json",
}


class CanadaCroissantProfile(CroissantProfile):
    """Map bilingual ckanext-fluent and custom scheming fields to JSON-LD."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        orig_serialize = self.g.serialize

        def custom_serialize(*s_args, **s_kwargs):
            result = orig_serialize(*s_args, **s_kwargs)
            if isinstance(result, bytes):
                result = result.decode("utf-8")
            if isinstance(result, str) and '"@context"' in result:
                data = json.loads(result)
                data = self._normalize_croissant_jsonld(data)
                return json.dumps(data, indent=4, ensure_ascii=False)
            return result

        self.g.serialize = custom_serialize

    def _normalize_croissant_jsonld(self, node):
        """
         - unwraps non-language-tagged @value/@type literals into clean strings
         - preserves @language tags on properties like issueNumber/keywords
         """
        if isinstance(node, dict):
            if "@value" in node and "@language" not in node and set(node.keys()) <= {"@value", "@type"}:
                return node["@value"]
            return {
                k: self._normalize_croissant_jsonld(v)
                for k, v in node.items()
            }
        if isinstance(node, list):
            return [
                self._normalize_croissant_jsonld(item)
                for item in node
            ]
        return node

    def _parse_dict(self, value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(value)
                    if isinstance(parsed, dict):
                        return parsed
                except (ValueError, SyntaxError, TypeError):
                    continue
        return {}

    def _clean_text(self, text):
        if not text or not isinstance(text, str):
            return ""
        return BeautifulSoup(text, "html.parser").get_text().strip()

    def _add_bilingual_triples(self, g, subject, predicate, value, fallback="", replace=True):
        """Emits separate @en and @fr RDF literals for a bilingual string or list field."""
        parsed = self._parse_dict(value) if value else {}
        
        values_by_lang = {
            "en": parsed.get("en") or parsed.get("en-t-fr") or fallback,
            "fr": parsed.get("fr") or parsed.get("fr-t-en"),
        }

        triples = []
        for lang, raw in values_by_lang.items():
            items = raw if isinstance(raw, list) else [raw]
            for item in items:
                if cleaned := self._clean_text(item):
                    triples.append((subject, predicate, Literal(cleaned, lang=lang)))

        if not triples:
            return
        if replace:
            g.remove((subject, predicate, None))
        for triple in triples:
            g.add(triple)

    def graph_from_dataset(self, dataset_dict, dataset_ref):
        org_slug = (dataset_dict.get("organization") or {}).get("name")

        super().graph_from_dataset(dataset_dict, dataset_ref)
        g = self.g

        # Croissant 1.1 for multilingual name & description
        # https://github.com/mlcommons/croissant/blob/main/python/mlcroissant/mlcroissant/_src/tests/graphs/1.1/multilingual_fields/metadata.json
        g.remove((dataset_ref, DCT.conformsTo, None))
        g.add((dataset_ref, DCT.conformsTo, Literal("http://mlcommons.org/croissant/1.1")))

        # Map title_translated to SCHEMA.name (required)
        self._add_bilingual_triples(
            g, dataset_ref, SCHEMA.name,
            dataset_dict.get("title_translated"),
            fallback=dataset_dict.get("title"),
        )

        # Map notes_translated to SCHEMA.description (required)
        self._add_bilingual_triples(
            g, dataset_ref, SCHEMA.description,
            dataset_dict.get("notes_translated"),
            fallback=dataset_dict.get("notes"),
        )

        # Map additional_notes to SCHEMA.disambiguatingDescription (optional)
        if dataset_dict.get("additional_notes"):
            self._add_bilingual_triples(
                g, dataset_ref, SCHEMA.disambiguatingDescription,
                dataset_dict.get("additional_notes"),
            )

        # Map keywords to SCHEMA.keywords (optional)
        keywords = self._parse_dict(dataset_dict.get("keywords"))
        if keywords:
            g.remove((dataset_ref, SCHEMA.keywords, None))
            self._add_bilingual_triples(
                g, dataset_ref, SCHEMA.keywords,
                dataset_dict.get("keywords")
            )

        # Map organization to SCHEMA.publisher (optional)
        org = dataset_dict.get("organization") or {}
        org_id = org.get("id")
        org_title = self._clean_text(org.get("title"))

        if org_title and " | " in org_title:
            org_en, _, org_fr = org_title.partition(" | ")
            org_pub = {"en": org_en.strip(), "fr": org_fr.strip()}
        else:
            org_pub = self._parse_dict(dataset_dict.get("org_title_at_publication"))

        pub_node = None
        if org_pub or org_title:
            g.remove((dataset_ref, SCHEMA.publisher, None))
            pub_node = CleanedURIRef(org_id) if org_id else BNode()
            g.add((pub_node, RDF.type, SCHEMA.Organization))
            self._add_bilingual_triples(g, pub_node, SCHEMA.name, org_pub, fallback=org_title)

            email = self._clean_text(dataset_dict.get("maintainer_email") or dataset_dict.get("author_email"))
            if email:
                g.remove((pub_node, SCHEMA.email, None))
                g.add((pub_node, SCHEMA.email, Literal(email)))

            site_url = (config.get("ckan.site_url") or "").rstrip("/")
            if site_url and org_slug:
                g.remove((pub_node, SCHEMA.url, None))
                g.add((pub_node, SCHEMA.url, Literal(f"{site_url}/organization/{org_slug}")))

            g.add((dataset_ref, SCHEMA.publisher, pub_node))

        # Map creator to SCHEMA.creator (required), fallback to publisher if empty
        for old_creator in list(g.objects(dataset_ref, SCHEMA.creator)):
            if old_creator != pub_node:
                g.remove((old_creator, None, None))
        g.remove((dataset_ref, SCHEMA.creator, None))

        creators = dataset_dict.get("creator")
        if isinstance(creators, str) and creators.strip():
            for person in [self._clean_text(c) for c in creators.split(",") if self._clean_text(c)]:
                p_node = BNode()
                g.add((p_node, RDF.type, SCHEMA.Person))
                g.add((p_node, SCHEMA.name, Literal(person, lang="en")))
                g.add((dataset_ref, SCHEMA.creator, p_node))
        elif pub_node is not None:
            g.add((dataset_ref, SCHEMA.creator, pub_node))

        # Map contributor to SCHEMA.contributor (optional)
        contrib_dict = self._parse_dict(dataset_dict.get("contributor"))
        if any(self._clean_text(contrib_dict.get(lang)) for lang in ("en", "fr")):
            c_node = BNode()
            g.add((c_node, RDF.type, SCHEMA.Organization))
            self._add_bilingual_triples(g, c_node, SCHEMA.name, contrib_dict, replace=False)
            g.add((dataset_ref, SCHEMA.contributor, c_node))

        # Map credit to SCHEMA.contributor (optional)
        for credit_item in dataset_dict.get("credit") or []:
            credit_val = credit_item.get("credit_name") if isinstance(credit_item, dict) else credit_item
            credit_dict = self._parse_dict(credit_val)
            if any(self._clean_text(v) for v in credit_dict.values()):
                cr_node = BNode()
                g.add((cr_node, RDF.type, SCHEMA.Organization))
                self._add_bilingual_triples(g, cr_node, SCHEMA.name, credit_dict)
                g.add((dataset_ref, SCHEMA.contributor, cr_node))

        # Map maintainer_contact_form or contact_information to SCHEMA.ContactPoint
        def _add_contact(self, g, dataset_ref, data_dict, fallback=None):
            parsed = self._parse_dict(data_dict)
            en = v if isinstance(v := parsed.get("en"), dict) else {}
            fr = v if isinstance(v := parsed.get("fr"), dict) else {}

            fb = self._parse_dict(fallback)
            fb_en = self._clean_text(fb.get("en"))
            fb_fr = self._clean_text(fb.get("fr"))

            if not (en or fr or fb_en or fb_fr):
                return

            cp_node = BNode()
            g.add((cp_node, RDF.type, SCHEMA.ContactPoint))

            name_en = self._clean_text(en.get("organization_name"))
            name_fr = self._clean_text(fr.get("organization_name"))
            if name_en:
                g.add((cp_node, SCHEMA.name, Literal(name_en, lang="en")))
            if name_fr:
                g.add((cp_node, SCHEMA.name, Literal(name_fr, lang="fr")))

            direct_map = (
                ("phone", SCHEMA.telephone),
                ("electronic_mail_address", SCHEMA.email),
                ("role", SCHEMA.contactType),
            )

            for key, pred in direct_map:
                val_en = en.get(key)
                val_fr = fr.get(key)
                if val_en and val_en == val_fr:
                    g.add((cp_node, pred, Literal(val_en)))
                else:
                    if val_en:
                        g.add((cp_node, pred, Literal(val_en, lang="en")))
                    if val_fr:
                        g.add((cp_node, pred, Literal(val_fr, lang="fr")))

            url_en = en.get("contact_form") or fb_en
            url_fr = fr.get("contact_form") or fb_fr
            if url_en and url_en == url_fr:
                g.add((cp_node, SCHEMA.url, Literal(url_en)))
            else:
                if url_en:
                    g.add((cp_node, SCHEMA.url, Literal(url_en, lang="en")))
                if url_fr:
                    g.add((cp_node, SCHEMA.url, Literal(url_fr, lang="fr")))

            address_map = (
                ("address", SCHEMA.streetAddress),
                ("delivery_point", SCHEMA.streetAddress),
                ("city", SCHEMA.addressLocality),
                ("administrative_area", SCHEMA.addressRegion),
                ("postal_code", SCHEMA.postalCode),
                ("country", SCHEMA.addressCountry),
            )

            addr_node = None
            for key, pred in address_map:
                val_en = self._clean_text(en.get(key))
                val_fr = self._clean_text(fr.get(key))
                if val_en or val_fr:
                    if addr_node is None:
                        addr_node = BNode()
                        g.add((addr_node, RDF.type, SCHEMA.PostalAddress))
                        g.add((cp_node, SCHEMA.address, addr_node))
                    if val_en and val_en == val_fr:
                        g.add((addr_node, pred, Literal(val_en)))
                    else:
                        if val_en:
                            g.add((addr_node, pred, Literal(val_en, lang="en")))
                        if val_fr:
                            g.add((addr_node, pred, Literal(val_fr, lang="fr")))

            g.add((dataset_ref, SCHEMA.contactPoint, cp_node))

        for old_cp in list(g.objects(dataset_ref, SCHEMA.contactPoint)):
            for old_addr in list(g.objects(old_cp, SCHEMA.address)):
                g.remove((old_addr, None, None))
            g.remove((old_cp, None, None))
        g.remove((dataset_ref, SCHEMA.contactPoint, None))

        contact_information = self._parse_dict(dataset_dict.get("contact_information"))
        maintainer_contact_form = self._parse_dict(dataset_dict.get("maintainer_contact_form"))
        _add_contact(
            self, g, dataset_ref,
            contact_information,
            fallback=maintainer_contact_form,
        )

        # Map distributor to SCHEMA.ContactPoint
        distributor = self._parse_dict(dataset_dict.get("distributor"))
        if distributor and distributor != contact_information:
            _add_contact(
                self, g, dataset_ref,
                distributor,
            )

        # Map date_published to SCHEMA.datePublished (ISO 8601)
        if dataset_dict.get("date_published"):
            g.remove((dataset_ref, SCHEMA.datePublished, None))
            iso_pub = dataset_dict["date_published"].strip().replace(" ", "T")
            g.add((dataset_ref, SCHEMA.datePublished, Literal(iso_pub, datatype=XSD.dateTime)))

        # Map date_modified to SCHEMA.dateModified (ISO 8601)
        mod_date = dataset_dict.get("date_modified") or dataset_dict.get("federated_date_modified")
        if mod_date:
            g.remove((dataset_ref, SCHEMA.dateModified, None))
            iso_mod = mod_date.strip().replace(" ", "T")
            g.add((dataset_ref, SCHEMA.dateModified, Literal(iso_mod, datatype=XSD.dateTime)))

        # Map date_expires to SCHEMA.expires (ISO 8601)
        if dataset_dict.get("date_expires"):
            iso_exp = dataset_dict["date_expires"].strip().replace(" ", "T")
            g.add((dataset_ref, SCHEMA.expires, Literal(iso_exp)))

        # Map Temporal Coverage to SCHEMA.temporalCoverage
        start = dataset_dict.get("time_period_coverage_start")
        end = dataset_dict.get("time_period_coverage_end")
        if start and end:
            g.add((dataset_ref, SCHEMA.temporalCoverage, Literal(f"{start}/{end}")))
        elif start:
            g.add((dataset_ref, SCHEMA.temporalCoverage, Literal(f"{start}/..")))

        # Map dataset-level inLanguage to SCHEMA.inLanguage
        bilingual_fields = (
            self._parse_dict(dataset_dict.get("title_translated")),
            self._parse_dict(dataset_dict.get("notes_translated")),
        )
        resource_langs = {
            lang for res in dataset_dict.get("resources") or [] for lang in (res.get("language") or [])
        }

        g.remove((dataset_ref, SCHEMA.inLanguage, None))
        for lang_code in ("en", "fr"):
            if lang_code in resource_langs or any(field.get(lang_code) for field in bilingual_fields):
                g.add((dataset_ref, SCHEMA.inLanguage, Literal(lang_code)))

        # Map frequency to CR.isLiveDataset
        frequency = (dataset_dict.get("frequency") or "").strip().lower()
        non_live_frequencies = {"as_needed", "irregular", "not_planned", "unknown", ""}
        is_live = frequency not in non_live_frequencies

        g.remove((dataset_ref, CR.isLiveDataset, None))
        g.add((dataset_ref, CR.isLiveDataset, Literal(is_live, datatype=XSD.boolean)))

        # Map subject and topic_category to SCHEMA.about
        for field_key in ("subject", "topic_category"):
            for val in dataset_dict.get(field_key) or []:
                if val:
                    g.add((dataset_ref, SCHEMA.about, Literal(str(val))))

        # Map collection to SCHEMA.genre
        if dataset_dict.get("collection"):
            g.add((dataset_ref, SCHEMA.genre, Literal(str(dataset_dict["collection"]))))

        # Map audience to SCHEMA.audience
        audiences = dataset_dict.get("audience") or []
        if audiences:
            aud_node = URIRef(f"{dataset_ref}#audience")
            g.add((aud_node, RDF.type, SCHEMA.Audience))
            aud_str = ", ".join(audiences) if isinstance(audiences, list) else str(audiences)
            g.add((aud_node, SCHEMA.audienceType, Literal(aud_str)))
            g.add((dataset_ref, SCHEMA.audience, aud_node))

        # Map restrictions to SCHEMA.conditionsOfAccess
        restrictions = dataset_dict.get("restrictions")
        if restrictions:
            g.add((dataset_ref, SCHEMA.conditionsOfAccess, Literal(restrictions)))

        # Map series (series_name, series_id) to SCHEMA.isPartOf
        series_name = self._parse_dict(dataset_dict.get("data_series_name"))
        series_id = self._parse_dict(dataset_dict.get("data_series_issue_identification"))
        if series_name or series_id:
            series_node = URIRef(f"{dataset_ref}#series")
            g.add((series_node, RDF.type, SCHEMA.CreativeWorkSeries))
            if series_name:
                self._add_bilingual_triples(g, series_node, SCHEMA.name, series_name)
            if series_id:
                self._add_bilingual_triples(g, series_node, SCHEMA.issueNumber, series_id)
            g.add((dataset_ref, SCHEMA.isPartOf, series_node))

        # Map isbn to SCHEMA.isbn
        if dataset_dict.get("isbn"):
            g.add((dataset_ref, SCHEMA.isbn, Literal(str(dataset_dict["isbn"]))))

        # Map issn to SCHEMA.issn
        if dataset_dict.get("issn"):
            g.add((dataset_ref, SCHEMA.issn, Literal(str(dataset_dict["issn"]))))

        # Map program_page_url (fallback url) to SCHEMA.sameAs
        g.remove((dataset_ref, SCHEMA.sameAs, None))
        ext_urls = self._parse_dict(dataset_dict.get("program_page_url")) or self._parse_dict(dataset_dict.get("url"))
        for lang in ("en", "fr"):
            ext_url = ext_urls.get(lang)
            if isinstance(ext_url, str) and ext_url.strip().startswith("http"):
                g.add((dataset_ref, SCHEMA.sameAs, Literal(ext_url.strip())))

        # Map doi to SCHEMA.sameAs
        doi = (dataset_dict.get("digital_object_identifier") or "").strip()
        if doi:
            if doi.lower().startswith("doi:"):
                doi = doi[4:].strip()
            doi_uri = doi if doi.startswith("http") else f"https://doi.org/{doi.lstrip('/')}"
            g.add((dataset_ref, SCHEMA.sameAs, Literal(doi_uri)))

        # Map Resources as SCHEMA.distribution
        file_objects = {str(s): s for s in g.subjects(RDF.type, CR.FileObject)}
        for resource in dataset_dict.get("resources", []):
            res_id = resource.get("id", "")
            res_ref = next((uri for s, uri in file_objects.items() if s.endswith(res_id)), URIRef(resource_uri(resource)))

            # Map name_transalted to SCHEMA.name and SCHEMA.alternateName
            res_names = self._parse_dict(resource.get("name_translated"))
            res_en_name = res_names.get("en") or res_names.get("en-t-fr")
            res_fr_name = res_names.get("fr") or res_names.get("fr-t-en")

            if res_en_name:
                g.remove((res_ref, SCHEMA.name, None))
                g.add((res_ref, SCHEMA.name, Literal(res_en_name)))
            if res_fr_name:
                g.remove((res_ref, SCHEMA.alternateName, None))
                g.add((res_ref, SCHEMA.alternateName, Literal(res_fr_name, lang="fr")))

            # Map download url to SCHEMA.encodingFormat
            res_url = (resource.get("url") or "").lower()
            raw_fmt = (resource.get("format") or "").upper()
            if res_url.endswith(".zip"):
                g.remove((res_ref, SCHEMA.encodingFormat, None))
                g.add((res_ref, SCHEMA.encodingFormat, Literal("application/zip")))
            elif raw_fmt in MIME_MAP:
                g.remove((res_ref, SCHEMA.encodingFormat, None))
                g.add((res_ref, SCHEMA.encodingFormat, Literal(MIME_MAP[raw_fmt])))

            # Map character_set to SCHEMA.encoding
            if resource.get("character_set"):
                g.add((res_ref, SCHEMA.encoding, Literal(resource["character_set"])))

            # Map hash to SCHEMA.sha256
            if resource.get("hash"):
                g.add((res_ref, SCHEMA.sha256, Literal(resource["hash"])))

            # Map language to SCHEMA.inLanguage
            g.remove((res_ref, SCHEMA.inLanguage, None))
            for lang_code in resource.get("language") or []:
                g.add((res_ref, SCHEMA.inLanguage, Literal(lang_code)))
