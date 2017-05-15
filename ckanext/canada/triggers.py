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
                PERFORM not_empty(NEW.title_en, 'title_en');
                PERFORM not_empty(NEW.title_fr, 'title_fr');
                PERFORM not_empty(NEW.description_en, 'description_en');
                PERFORM not_empty(NEW.description_fr, 'description_fr');
                PERFORM not_empty(NEW.date_published, 'date_published');
                PERFORM year_optional_month_day(NEW.date_published, 'date_published');
                PERFORM not_empty(NEW.language, 'language');
                PERFORM choice_one_of(NEW.language, {language}, 'language');
                PERFORM not_empty(NEW.size, 'size');
                PERFORM not_empty(NEW.eligible_for_release, 'eligible_for_release');
                PERFORM choice_one_of(NEW.eligible_for_release, {eligible_for_release}, 'eligible_for_release');
                PERFORM not_empty(NEW.program_alignment_architecture_en, 'program_alignment_architecture_en');
                PERFORM not_empty(NEW.program_alignment_architecture_fr, 'program_alignment_architecture_fr');
                PERFORM not_empty(NEW.date_released, 'date_released');
                PERFORM year_optional_month_day(NEW.date_released, 'date_released');
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

    lc.action.datastore_function_create(
        name=u'contracts_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM not_empty(NEW.reference_number, 'reference_number');
                NEW.aboriginal_business := truthy_to_yn(NEW.aboriginal_business);
                NEW.potential_commercial_exploitation := truthy_to_yn(NEW.potential_commercial_exploitation);
                NEW.former_public_servant := truthy_to_yn(NEW.former_public_servant);
                RETURN NEW;
            END;
            ''')

def pg_array(choices):
    from ckanext.datastore.helpers import literal_string
    return u'ARRAY[' + u','.join(
        literal_string(unicode(c[0])) for c in choices) + u']'
