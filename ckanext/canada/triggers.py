from ckanapi import LocalCKAN
from ckantoolkit import h


def update_triggers():
    """Create/update triggers used by PD tables"""

    lc = LocalCKAN()

    lc.action.datastore_function_create(
        name=u'not_empty',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF (value = '') IS NOT FALSE THEN
                    RAISE EXCEPTION 'This field must not be empty: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'not_empty',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'date'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RAISE EXCEPTION 'This field must not be empty: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'not_empty',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value = '{}' THEN
                    RAISE EXCEPTION 'This field must not be empty: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'not_empty',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'int4'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RAISE EXCEPTION 'This field must not be empty: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'not_empty',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'money'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RAISE EXCEPTION 'This field must not be empty: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'no_surrounding_whitespace',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=ur'''
            BEGIN
                IF trim(both E'\t\n\x0b\x0c\r ' from value) <> value THEN
                    RAISE EXCEPTION 'This field must not have surrounding whitespace: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'year_optional_month_day',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            DECLARE
                ymd _text := regexp_matches(value,
                    '(\d\d\d\d)(?:-(\d\d)(?:-(\d\d))?)?');
            BEGIN
                IF ymd IS NULL THEN
                    RAISE EXCEPTION 'Dates must be in YYYY-MM-DD format: %', field_name;
                END IF;
                IF ymd[3] IS NOT NULL THEN
                    PERFORM value::date;
                ELSIF NOT ymd[2]::int BETWEEN 1 AND 12 THEN
                    RAISE EXCEPTION 'Dates must be in YYYY-MM-DD format: %', field_name;
                END IF;
            EXCEPTION
                WHEN others THEN
                    RAISE EXCEPTION 'Dates must be in YYYY-MM-DD format: %', field_name;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'choice_one_of',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'choices', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF NOT (value = ANY (choices)) THEN
                    RAISE EXCEPTION 'Invalid choice for %: "%"', field_name, value;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'choices_from',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'_text'},
            {u'argname': u'choices', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            DECLARE
                bad_choices text := array_to_string(ARRAY(
                    SELECT unnest(value)
                    EXCEPT SELECT unnest(choices)), ', ');
            BEGIN
                IF bad_choices <> '' THEN
                    RAISE EXCEPTION 'Invalid choice for %: "%"', field_name, bad_choices;
                END IF;
                RETURN ARRAY(
                    SELECT c FROM(SELECT unnest(choices) as c) u
                    WHERE c in (SELECT unnest(value)));
            END;
        ''')

    consultations_choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('consultations'))
    lc.action.datastore_function_create(
        name=u'consultations_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM not_empty(NEW.registration_number, 'registration_number');
                PERFORM choice_one_of(NEW.publishable, {publishable}, 'publishable');
                NEW.partner_departments := choices_from(
                    NEW.partner_departments, {partner_departments}, 'partner_departments');
                PERFORM choice_one_of(NEW.sector, {sectors}, 'sector');
                PERFORM not_empty(NEW.subjects, 'subjects');
                NEW.subjects := choices_from(
                    NEW.subjects, {subjects}, 'subjects');
                PERFORM not_empty(NEW.title_en, 'title_en');
                PERFORM not_empty(NEW.title_fr, 'title_fr');
                PERFORM not_empty(NEW.goals, 'goals');
                NEW.goals := choices_from(NEW.goals, {goals}, 'goals');
                PERFORM not_empty(NEW.description_en, 'description_en');
                PERFORM not_empty(NEW.description_fr, 'description_fr');
                PERFORM choice_one_of(
                    NEW.public_opinion_research,
                    {public_opinion_research},
                    'public_opinion_research');
                PERFORM choice_one_of(
                    NEW.public_opinion_research_standing_offer,
                    {public_opinion_research_standing_offer},
                    'public_opinion_research_standing_offer');
                PERFORM not_empty(
                    NEW.target_participants_and_audience,
                    'target_participants_and_audience');
                NEW.target_participants_and_audience := choices_from(
                    NEW.target_participants_and_audience,
                    {target_participants_and_audience},
                    'target_participants_and_audience');
                PERFORM not_empty(NEW.planned_start_date, 'planned_start_date');
                PERFORM not_empty(NEW.planned_end_date, 'planned_end_date');
                PERFORM choice_one_of(NEW.status, {status}, 'status');
                PERFORM not_empty(NEW.further_information_en, 'further_information_en');
                PERFORM not_empty(NEW.further_information_fr, 'further_information_fr');
                PERFORM choice_one_of(
                    NEW.report_available_online,
                    {report_available_online},
                    'report_available_online');
                PERFORM not_empty(NEW.rationale, 'rationale');
                NEW.rationale := choices_from(
                    NEW.rationale, {rationale}, 'rationale');

                RETURN NEW;
            END;
            '''.format(
                sectors=pg_array(consultations_choices['sector']),
                publishable=pg_array(consultations_choices['publishable']),
                partner_departments=pg_array(
                    consultations_choices['partner_departments']),
                subjects=pg_array(consultations_choices['subjects']),
                goals=pg_array(consultations_choices['goals']),
                target_participants_and_audience=pg_array(
                    consultations_choices['target_participants_and_audience']),
                public_opinion_research=pg_array(
                    consultations_choices['public_opinion_research']),
                public_opinion_research_standing_offer=pg_array(
                    consultations_choices['public_opinion_research_standing_offer']),
                status=pg_array(consultations_choices['status']),
                report_available_online=pg_array(
                    consultations_choices['report_available_online']),
                rationale=pg_array(consultations_choices['rationale']),
            )
        )
    lc.action.datastore_function_create(
        name=u'update_record_modified_created_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            DECLARE
                req_user_modified text := NEW.user_modified;
                username text NOT NULL := (SELECT username
                    FROM datastore_user);
                sysadmin boolean NOT NULL := (SELECT sysadmin
                    FROM datastore_user);
            BEGIN
                IF NOT sysadmin OR (req_user_modified = '') IS NOT FALSE THEN
                    req_user_modified := NULL;
                END IF;
                IF TG_OP = 'INSERT' THEN
                    IF NEW.record_created IS NULL THEN
                        NEW.record_created := now() at time zone 'utc';
                    END IF;
                    IF NEW.record_modified IS NULL THEN
                        NEW.record_modified := NEW.record_created;
                    END IF;
                    IF req_user_modified IS NULL THEN
                        NEW.user_modified := username;
                    END IF;
                    RETURN NEW;
                END IF;

                IF NEW.record_created IS NULL THEN
                    NEW.record_created := OLD.record_created;
                END IF;
                IF NEW.record_modified IS NULL THEN
                    NEW.record_modified := OLD.record_modified;
                END IF;
                IF req_user_modified IS NULL THEN
                    NEW.user_modified := OLD.user_modified;
                END IF;
                IF OLD = NEW THEN
                    RETURN NULL;
                END IF;
                NEW.record_modified := now() at time zone 'utc';
                IF req_user_modified IS NULL THEN
                    NEW.user_modified := username;
                ELSE
                    NEW.user_modified := req_user_modified;
                END IF;
                RETURN NEW;
            END;
            ''')

    inventory_choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('inventory'))
    lc.action.datastore_function_create(
        name=u'inventory_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM not_empty(NEW.ref_number, 'ref_number');
                PERFORM no_surrounding_whitespace(NEW.ref_number, 'ref_number');
                PERFORM not_empty(NEW.title_en, 'title_en');
                PERFORM not_empty(NEW.title_fr, 'title_fr');
                -- PERFORM not_empty(NEW.description_en, 'description_en');
                -- PERFORM not_empty(NEW.description_fr, 'description_fr');
                -- PERFORM not_empty(NEW.date_published, 'date_published');
                -- PERFORM year_optional_month_day(NEW.date_published, 'date_published');
                -- PERFORM not_empty(NEW.language, 'language');
                -- PERFORM choice_one_of(NEW.language, {language}, 'language');
                -- PERFORM not_empty(NEW.size, 'size');
                NEW.eligible_for_release := truthy_to_yn(NEW.eligible_for_release);
                -- PERFORM not_empty(NEW.eligible_for_release, 'eligible_for_release');
                -- PERFORM choice_one_of(NEW.eligible_for_release, {eligible_for_release}, 'eligible_for_release');
                -- PERFORM not_empty(NEW.program_alignment_architecture_en, 'program_alignment_architecture_en');
                -- PERFORM not_empty(NEW.program_alignment_architecture_fr, 'program_alignment_architecture_fr');
                -- PERFORM not_empty(NEW.date_released, 'date_released');
                -- PERFORM year_optional_month_day(NEW.date_released, 'date_released');
                RETURN NEW;
            END;
            '''.format(
                language=pg_array(inventory_choices['language']),
                eligible_for_release=pg_array(inventory_choices['eligible_for_release']),
            )
        )

    lc.action.datastore_function_create(
        name=u'protect_user_votes_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            DECLARE
                req_user_votes int := NEW.user_votes;
                sysadmin boolean NOT NULL := (SELECT sysadmin
                    FROM datastore_user);
            BEGIN
                IF NOT sysadmin THEN
                    req_user_votes := NULL;
                END IF;

                IF req_user_votes IS NULL AND TG_OP = 'UPDATE' THEN
                    NEW.user_votes := OLD.user_votes;
                ELSE
                    NEW.user_votes = req_user_votes;
                END IF;

                IF NEW.user_votes IS NULL THEN
                    NEW.user_votes := 0;
                END IF;
                RETURN NEW;
            END;
            ''')

    lc.action.datastore_function_create(
        name=u'truthy_to_yn',
        or_replace=True,
        arguments=[{u'argname': u'value', u'argtype': u'text'}],
        rettype=u'text',
        definition=u'''
            DECLARE
                truthy boolean := value ~*
                    '[[:<:]](true|t|vrai|v|1|yes|y|oui|o)[[:>:]]';
                falsy boolean := value ~*
                    '[[:<:]](false|f|faux|0|no|n|non)[[:>:]]';
            BEGIN
                IF truthy AND NOT falsy THEN
                    RETURN 'Y';
                ELSIF falsy AND NOT truthy THEN
                    RETURN 'N';
                ELSE
                    RETURN NULL;
                END IF;
            END;
            ''')

    contracts_choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('contracts'))
    lc.action.datastore_function_create(
        name=u'contracts_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM not_empty(NEW.reference_number, 'reference_number');
                PERFORM no_surrounding_whitespace(NEW.reference_number, 'reference_number');
                NEW.aboriginal_business := truthy_to_yn(NEW.aboriginal_business);
                NEW.potential_commercial_exploitation := truthy_to_yn(NEW.potential_commercial_exploitation);
                NEW.former_public_servant := truthy_to_yn(NEW.former_public_servant);

                PERFORM not_empty(NEW.contract_date, 'contract_date');
                IF NEW.contract_date >= '2018-04-01'::date THEN
                    PERFORM not_empty(NEW.procurement_id, 'procurement_id');
                    PERFORM not_empty(NEW.vendor_name, 'vendor_name');
                    PERFORM not_empty(NEW.economic_object_code, 'economic_object_code');
                    PERFORM not_empty(NEW.description_en, 'description_en');
                    PERFORM not_empty(NEW.description_fr, 'description_fr');
                    PERFORM not_empty(NEW.contract_period_start, 'contract_period_start');
                    PERFORM not_empty(NEW.delivery_date, 'delivery_date');
                    PERFORM not_empty(NEW.contract_value, 'contract_value');
                    PERFORM not_empty(NEW.original_value, 'original_value');
                    PERFORM not_empty(NEW.agreement_type_code, 'agreement_type_code');
                    PERFORM not_empty(NEW.commodity_type_code, 'commodity_type_code');
                    PERFORM choice_one_of(NEW.commodity_type_code,
                        {commodity_type_code},
                        'commodity_type_code');
                    PERFORM not_empty(NEW.commodity_code, 'commodity_code');
                    PERFORM choice_one_of(NEW.commodity_code,
                        {commodity_code},
                        'commodity_code');
                    PERFORM not_empty(NEW.country_of_origin, 'country_of_origin');
                    PERFORM choice_one_of(NEW.country_of_origin,
                        {country_of_origin},
                        'country_of_origin');
                    PERFORM not_empty(NEW.solicitation_procedure_code, 'solicitation_procedure_code');
                    PERFORM choice_one_of(NEW.solicitation_procedure_code,
                        {solicitation_procedure_code},
                        'solicitation_procedure_code');
                    PERFORM not_empty(NEW.limited_tendering_reason_code, 'limited_tendering_reason_code');
                    PERFORM choice_one_of(NEW.limited_tendering_reason_code,
                        {limited_tendering_reason_code},
                        'limited_tendering_reason_code');
                    PERFORM not_empty(NEW.exemption_code, 'exemption_code');
                    PERFORM choice_one_of(NEW.exemption_code,
                        {exemption_code},
                        'exemption_code');
                    PERFORM not_empty(NEW.aboriginal_business, 'aboriginal_business');
                    PERFORM not_empty(NEW.intellectual_property_code, 'intellectual_property_code');
                    PERFORM choice_one_of(NEW.intellectual_property_code,
                        {intellectual_property_code},
                        'intellectual_property_code');
                    PERFORM not_empty(NEW.former_public_servant, 'former_public_servant');
                    PERFORM choice_one_of(NEW.standing_offer,
                        {standing_offer},
                        'standing_offer');
                    PERFORM not_empty(NEW.document_type_code, 'document_type_code');
                    PERFORM choice_one_of(NEW.document_type_code,
                        {document_type_code},
                        'document_type_code');
                    PERFORM not_empty(NEW.reporting_period, 'reporting_period');
                    PERFORM choice_one_of(NEW.reporting_period,
                        {reporting_period},
                        'reporting_period');
                END IF;

                RETURN NEW;
            END;
            '''.format(
                commodity_type_code = pg_array(contracts_choices['commodity_type_code']),
                commodity_code = pg_array(contracts_choices['commodity_code']),
                country_of_origin = pg_array(contracts_choices['country_of_origin']),
                solicitation_procedure_code = pg_array(contracts_choices['solicitation_procedure_code']),
                limited_tendering_reason_code = pg_array(contracts_choices['limited_tendering_reason_code']),
                exemption_code = pg_array(contracts_choices['exemption_code']),
                intellectual_property_code = pg_array(contracts_choices['intellectual_property_code']),
                standing_offer = pg_array(contracts_choices['standing_offer']),
                document_type_code = pg_array(contracts_choices['document_type_code']),
                reporting_period = pg_array(contracts_choices['reporting_period']),
            )
        )

    lc.action.datastore_function_create(
        name=u'valid_percentage',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'int4'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value < 0 OR value > 100 THEN
                    RAISE EXCEPTION 'This field must be a valid percentage: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'integer_or_na_nd',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value <> 'NA' AND value <> 'ND' AND NOT value ~ '^[0-9]+$' THEN
                    RAISE EXCEPTION 'This field must be NA or an integer: %', field_name;
                END IF;
            END;
        ''')

    service_choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('service'))
    lc.action.datastore_function_create(
        name=u'service_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM not_empty(NEW.service_id_number, 'service_id_number');
                PERFORM no_surrounding_whitespace(NEW.service_id_number, 'service_id_number');
                PERFORM not_empty(NEW.service_name_en, 'service_name_en');
                PERFORM not_empty(NEW.service_name_fr, 'service_name_fr');
                PERFORM not_empty(NEW.external_internal, 'external_internal');
                PERFORM choice_one_of(NEW.external_internal, {external_internal}, 'external_internal');
                PERFORM not_empty(NEW.service_type, 'service_type');
                PERFORM choice_one_of(NEW.service_type, {service_type}, 'service_type');
                PERFORM not_empty(NEW.special_designations, 'special_designations');
                PERFORM choice_one_of(NEW.special_designations, {special_designations}, 'special_designations');
                PERFORM not_empty(NEW.service_description_en, 'service_description_en');
                PERFORM not_empty(NEW.service_description_fr, 'service_description_fr');
                PERFORM not_empty(NEW.responsibility_area_en, 'responsibility_area_en');
                PERFORM not_empty(NEW.responsibility_area_fr, 'responsibility_area_fr');
                PERFORM not_empty(NEW.authority_en, 'authority_en');
                PERFORM not_empty(NEW.authority_fr, 'authority_fr');
                PERFORM not_empty(NEW.program_name_en, 'program_name_en');
                PERFORM not_empty(NEW.program_name_fr, 'program_name_fr');
                PERFORM not_empty(NEW.program_id_number, 'program_id_number');
                PERFORM not_empty(NEW.service_owner, 'service_owner');
                PERFORM choice_one_of(NEW.service_owner, {service_owner}, 'service_owner');
                PERFORM not_empty(NEW.service_agreements, 'service_agreements');
                PERFORM choice_one_of(NEW.service_agreements, {service_agreements}, 'service_agreements');
                PERFORM not_empty(NEW.client_target_groups, 'client_target_groups');
                NEW.client_target_groups := choices_from(
                    NEW.client_target_groups, {client_target_groups}, 'client_target_groups');
                PERFORM not_empty(NEW.cra_business_number, 'cra_business_number');
                PERFORM choice_one_of(NEW.cra_business_number, {cra_business_number}, 'cra_business_number');
                PERFORM not_empty(NEW.volumes_per_channel_online, 'volumes_per_channel_online');
                PERFORM integer_or_na_nd(NEW.volumes_per_channel_online, 'volumes_per_channel_online');
                PERFORM not_empty(NEW.volumes_per_channel_telephone, 'volumes_per_channel_telephone');
                PERFORM integer_or_na_nd(NEW.volumes_per_channel_telephone, 'volumes_per_channel_telephone');
                PERFORM not_empty(NEW.volumes_per_channel_in_person, 'volumes_per_channel_in_person');
                PERFORM integer_or_na_nd(NEW.volumes_per_channel_in_person, 'volumes_per_channel_in_person');
                PERFORM not_empty(NEW.volumes_per_channel_mail, 'volumes_per_channel_mail');
                PERFORM integer_or_na_nd(NEW.volumes_per_channel_mail, 'volumes_per_channel_mail');
                PERFORM not_empty(NEW.user_fee, 'user_fee');
                PERFORM choice_one_of(NEW.user_fee, {user_fee}, 'user_fee');
                PERFORM not_empty(NEW.targets_published_en, 'targets_published_en');
                PERFORM not_empty(NEW.targets_published_fr, 'targets_published_fr');
                PERFORM not_empty(NEW.e_registration, 'e_registration');
                PERFORM choice_one_of(NEW.e_registration, {e_registration}, 'e_registration');
                PERFORM not_empty(NEW.e_authentication, 'e_authentication');
                PERFORM choice_one_of(NEW.e_authentication, {e_authentication}, 'e_authentication');
                PERFORM not_empty(NEW.e_application, 'e_application');
                PERFORM choice_one_of(NEW.e_application, {e_application}, 'e_application');
                PERFORM not_empty(NEW.e_decision, 'e_decision');
                PERFORM choice_one_of(NEW.e_decision, {e_decision}, 'e_decision');
                PERFORM not_empty(NEW.e_issuance, 'e_issuance');
                PERFORM choice_one_of(NEW.e_issuance, {e_issuance}, 'e_issuance');
                PERFORM not_empty(NEW.e_feedback, 'e_feedback');
                PERFORM choice_one_of(NEW.e_feedback, {e_feedback}, 'e_feedback');
                PERFORM not_empty(NEW.interaction_points_online, 'interaction_points_online');
                PERFORM choice_one_of(NEW.interaction_points_online, {interaction_points_online}, 'interaction_points_online');
                PERFORM not_empty(NEW.interaction_points_total, 'interaction_points_total');
                PERFORM choice_one_of(NEW.interaction_points_total, {interaction_points_total}, 'interaction_points_total');
                PERFORM not_empty(NEW.percentage_online, 'percentage_online');
                PERFORM valid_percentage(NEW.percentage_online, 'percentage_online');
                RETURN NEW;
            END;
            '''.format(
                external_internal=pg_array(service_choices['external_internal']),
                service_type=pg_array(service_choices['service_type']),
                special_designations=pg_array(service_choices['special_designations']),
                service_owner=pg_array(service_choices['service_owner']),
                service_agreements=pg_array(service_choices['service_agreements']),
                client_target_groups=pg_array(service_choices['client_target_groups']),
                cra_business_number=pg_array(service_choices['cra_business_number']),
                user_fee=pg_array(service_choices['user_fee']),
                e_registration=pg_array(service_choices['e_registration']),
                e_authentication=pg_array(service_choices['e_authentication']),
                e_application=pg_array(service_choices['e_application']),
                e_decision=pg_array(service_choices['e_decision']),
                e_issuance=pg_array(service_choices['e_issuance']),
                e_feedback=pg_array(service_choices['e_feedback']),
                interaction_points_online=pg_array(service_choices['interaction_points_online']),
                interaction_points_total=pg_array(service_choices['interaction_points_total']),
            )
        )

    grants_choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('grants'))
    lc.action.datastore_function_create(
        name=u'grants_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM not_empty(NEW.project_identifier, 'project_identifier');

                IF NEW.amendment_number IS NOT NULL OR
                        NEW.amendment_date IS NOT NULL THEN
                    PERFORM not_empty(NEW.amendment_number, 'amendment_number');
                    PERFORM not_empty(NEW.amendment_date, 'amendment_date');
                END IF;

                IF NOT ((NEW.foreign_currency_type = '') IS NOT FALSE) OR
                        NEW.foreign_currency_value IS NOT NULL THEN
                    PERFORM not_empty(NEW.foreign_currency_type, 'foreign_currency_type');
                    PERFORM choice_one_of(
                        NEW.foreign_currency_type,
                        {foreign_currency_type},
                        'foreign_currency_type');
                    PERFORM not_empty(NEW.foreign_currency_value, 'foreign_currency_value');
                END IF;

                PERFORM not_empty(NEW.agreement_value, 'agreement_value');

                PERFORM not_empty(NEW.agreement_start_date, 'agreement_start_date');
                IF NEW.agreement_start_date >= '2018-04-01'::date THEN
                    PERFORM not_empty(NEW.recipient_legal_name, 'recipient_legal_name');
                    PERFORM not_empty(NEW.agreement_type, 'agreement_type');
                    PERFORM choice_one_of(
                        NEW.agreement_type,
                        {agreement_type},
                        'agreement_type');
                    PERFORM not_empty(NEW.recipient_type, 'recipient_type');
                    PERFORM choice_one_of(
                        NEW.recipient_type,
                        {recipient_type},
                        'recipient_type');
                    PERFORM not_empty(NEW.recipient_country, 'recipient_country');
                    PERFORM choice_one_of(
                        NEW.recipient_country,
                        {recipient_country},
                        'recipient_country');
                    IF NEW.recipient_country = 'CA' THEN
                        PERFORM not_empty(NEW.recipient_province, 'recipient_province');
                    END IF;
                    PERFORM choice_one_of(
                        NEW.recipient_province,
                        {recipient_province},
                        'recipient_province');
                    PERFORM not_empty(NEW.recipient_city_en, 'recipient_city_en');
                    PERFORM not_empty(NEW.recipient_city_fr, 'recipient_city_fr');
                    PERFORM not_empty(NEW.agreement_end_date, 'agreement_end_date');
                    PERFORM not_empty(NEW.description_en, 'description_en');
                    PERFORM not_empty(NEW.description_fr, 'description_fr');
                    PERFORM not_empty(NEW.expected_results_en, 'expected_results_en');
                    PERFORM not_empty(NEW.expected_results_fr, 'expected_results_fr');
                    PERFORM not_empty(NEW.agreement_title_en, 'agreement_title_en');
                    PERFORM not_empty(NEW.agreement_title_fr, 'agreement_title_fr');
                    PERFORM not_empty(NEW.prog_name_en, 'prog_name_en');
                    PERFORM not_empty(NEW.prog_name_fr, 'prog_name_fr');
                    PERFORM not_empty(NEW.prog_purpose_en, 'prog_purpose_en');
                    PERFORM not_empty(NEW.prog_purpose_fr, 'prog_purpose_fr');
                    IF NEW.recipient_country = 'CA' THEN
                        PERFORM not_empty(NEW.recipient_postal_code,
                            'recipient_postal_code');
                    END IF;
                END IF;
                RETURN NEW;
            END;
            '''.format(
                agreement_type=pg_array(grants_choices['agreement_type']),
                recipient_type=pg_array(grants_choices['recipient_type']),
                recipient_country=pg_array(grants_choices['recipient_country']),
                recipient_province=pg_array(grants_choices['recipient_province']),
                foreign_currency_type=pg_array(grants_choices['foreign_currency_type']),
            )
        )

def pg_array(choices):
    from ckanext.datastore.helpers import literal_string
    return u'ARRAY[' + u','.join(
        literal_string(unicode(c[0])) for c in choices) + u']'
