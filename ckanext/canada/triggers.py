from ckanapi import LocalCKAN
from ckantoolkit import h


def update_triggers():
    """Create/update triggers used by PD tables"""

    lc = LocalCKAN()

    lc.action.datastore_function_create(
        name=u'text_not_empty',
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
        name=u'date_not_empty',
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
        name=u'text_array_not_empty',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value = '{{}}' THEN
                    RAISE EXCEPTION 'This field must not be empty: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'text_choice_one_of',
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
        name=u'text_array_choices_from',
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

    choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('consultations'))
    lc.action.datastore_function_create(
        name=u'consultations_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM text_not_empty(NEW.registration_number, 'registration_number');
                PERFORM text_choice_one_of(NEW.publishable, {publishable}, 'publishable');
                PERFORM text_array_choices_from(NEW.partner_departments, {partner_departments}, 'partner_departments');
                PERFORM text_choice_one_of(NEW.sector, {sectors}, 'sector');
                PERFORM text_array_not_empty(NEW.subjects, 'subjects');
                PERFORM text_array_choices_from(NEW.subjects, {subjects}, 'subjects');
                PERFORM text_not_empty(NEW.title_en, 'title_en');
                PERFORM text_not_empty(NEW.title_fr, 'title_fr');
                PERFORM text_array_not_empty(NEW.goals, 'goals');
                PERFORM text_array_choices_from(NEW.goals, {goals}, 'goals');
                PERFORM text_not_empty(NEW.description_en, 'description_en');
                PERFORM text_not_empty(NEW.description_fr, 'description_fr');
                PERFORM text_choice_one_of(NEW.public_opinion_research, {public_opinion_research}, 'public_opinion_research');
                PERFORM text_choice_one_of(NEW.public_opinion_research_standing_offer, {public_opinion_research_standing_offer}, 'public_opinion_research_standing_offer');
                PERFORM text_array_not_empty(NEW.target_participants_and_audience, 'target_participants_and_audience');
                PERFORM text_array_choices_from(NEW.target_participants_and_audience, {target_participants_and_audience}, 'target_participants_and_audience');
                PERFORM date_not_empty(NEW.planned_start_date, 'planned_start_date');
                PERFORM date_not_empty(NEW.planned_end_date, 'planned_end_date');
                PERFORM text_choice_one_of(NEW.status, {status}, 'status');
                PERFORM text_not_empty(NEW.further_information_en, 'further_information_en');
                PERFORM text_not_empty(NEW.further_information_fr, 'further_information_fr');
                PERFORM text_choice_one_of(NEW.report_available_online, {report_available_online}, 'report_available_online');
                PERFORM text_array_not_empty(NEW.rationale, 'rationale');
                PERFORM text_array_choices_from(NEW.rationale, {rationale}, 'rationale');

                RETURN NEW;
            END;
            '''.format(
                sectors=pg_array(choices['sector']),
                publishable=pg_array(choices['publishable']),
                partner_departments=pg_array(
                    choices['partner_departments']),
                subjects=pg_array(choices['subjects']),
                goals=pg_array(choices['goals']),
                target_participants_and_audience=pg_array(
                    choices['target_participants_and_audience']),
                public_opinion_research=pg_array(
                    choices['public_opinion_research']),
                public_opinion_research_standing_offer=pg_array(
                    choices['public_opinion_research_standing_offer']),
                status=pg_array(choices['status']),
                report_available_online=pg_array(
                    choices['report_available_online']),
                rationale=pg_array(choices['rationale']),
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


def pg_array(choices):
    from ckanext.datastore.helpers import literal_string
    return u'ARRAY[' + u','.join(
        literal_string(unicode(c[0])) for c in choices) + u']'
