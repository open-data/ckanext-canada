from ckanapi import LocalCKAN
from ckantoolkit import h


def update_triggers():
    """Create/update triggers used by PD tables"""

    lc = LocalCKAN()
    choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('consultations'))
    lc.action.datastore_function_create(
        name=u'consultations_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            DECLARE
                bad_partner_departments text := array_to_string(ARRAY(
                    SELECT unnest(NEW.partner_departments)
                    EXCEPT SELECT unnest({partner_departments})), ', ');
                bad_subjects text := array_to_string(ARRAY(
                    SELECT unnest(NEW.subjects)
                    EXCEPT SELECT unnest({subjects})), ', ');
                bad_goals text := array_to_string(ARRAY(
                    SELECT unnest(NEW.goals)
                    EXCEPT SELECT unnest({goals})), ', ');
                bad_target_participants_and_audience text := array_to_string(ARRAY(
                    SELECT unnest(NEW.target_participants_and_audience)
                    EXCEPT SELECT unnest({target_participants_and_audience})), ', ');
                bad_rationale text := array_to_string(ARRAY(
                    SELECT unnest(NEW.rationale)
                    EXCEPT SELECT unnest({rationale})), ', ');
            BEGIN
                IF (NEW.registration_number = '') IS NOT FALSE THEN
                    RAISE EXCEPTION 'This field must not be empty: registration_number';
                END IF;

                IF NOT (NEW.publishable = ANY {publishable}) THEN
                    RAISE EXCEPTION 'Invalid choice for publishable: "%"', NEW.publishable;
                END IF;

                IF bad_partner_departments <> '' THEN
                    RAISE EXCEPTION 'Invalid choice for partner_departments: "%"', bad_partner_departments;
                END IF;
                NEW.partner_departments := ARRAY(
                    SELECT c FROM(SELECT unnest({partner_departments}) as c) u
                    WHERE c in (SELECT unnest(NEW.partner_departments)));

                IF NOT (NEW.sector = ANY {sectors}) THEN
                    RAISE EXCEPTION 'Invalid choice for sector: "%"', NEW.sector;
                END IF;

                IF NEW.subjects = '{{}}' THEN
                    RAISE EXCEPTION 'This field must not be empty: subjects';
                END IF;
                IF bad_subjects <> '' THEN
                    RAISE EXCEPTION 'Invalid choice for subjects: "%"', bad_subjects;
                END IF;
                NEW.subjects := ARRAY(
                    SELECT c FROM(SELECT unnest({subjects}) as c) u
                    WHERE c in (SELECT unnest(NEW.subjects)));

                IF (NEW.title_en = '') IS NOT FALSE THEN
                    RAISE EXCEPTION 'This field must not be empty: title_en';
                END IF;

                IF (NEW.title_fr = '') IS NOT FALSE THEN
                    RAISE EXCEPTION 'This field must not be empty: title_fr';
                END IF;

                IF NEW.goals = '{{}}' THEN
                    RAISE EXCEPTION 'This field must not be empty: goals';
                END IF;
                IF bad_goals <> '' THEN
                    RAISE EXCEPTION 'Invalid choice for goals: "%"', bad_goals;
                END IF;
                NEW.goals := ARRAY(
                    SELECT c FROM(SELECT unnest({goals}) as c) u
                    WHERE c in (SELECT unnest(NEW.goals)));

                IF (NEW.description_en = '') IS NOT FALSE THEN
                    RAISE EXCEPTION 'This field must not be empty: description_en';
                END IF;

                IF (NEW.description_fr = '') IS NOT FALSE THEN
                    RAISE EXCEPTION 'This field must not be empty: description_fr';
                END IF;

                IF NOT (NEW.public_opinion_research = ANY {public_opinion_research}) THEN
                    RAISE EXCEPTION 'Invalid choice for public_opinion_research: "%"', NEW.public_opinion_research;
                END IF;

                IF NOT (NEW.public_opinion_research_standing_offer = ANY {public_opinion_research_standing_offer}) THEN
                    RAISE EXCEPTION 'Invalid choice for public_opinion_research_standing_offer: "%"', NEW.public_opinion_research_standing_offer;
                END IF;

                IF NEW.target_participants_and_audience = '{{}}' THEN
                    RAISE EXCEPTION 'This field must not be empty: target_participants_and_audience';
                END IF;
                IF bad_target_participants_and_audience <> '' THEN
                    RAISE EXCEPTION 'Invalid choice for target_participants_and_audience: "%"', bad_target_participants_and_audience;
                END IF;
                NEW.target_participants_and_audience := ARRAY(
                    SELECT c FROM(SELECT unnest({target_participants_and_audience}) as c) u
                    WHERE c in (SELECT unnest(NEW.target_participants_and_audience)));

                IF NEW.planned_start_date IS NULL THEN
                    RAISE EXCEPTION 'This field must not be empty: planned_start_date';
                END IF;

                IF NEW.planned_end_date IS NULL THEN
                    RAISE EXCEPTION 'This field must not be empty: planned_end_date';
                END IF;

                IF NOT (NEW.status = ANY {status}) THEN
                    RAISE EXCEPTION 'Invalid choice for status: "%"', NEW.status;
                END IF;

                IF (NEW.further_information_en = '') IS NOT FALSE THEN
                    RAISE EXCEPTION 'This field must not be empty: further_information_en';
                END IF;

                IF (NEW.further_information_fr = '') IS NOT FALSE THEN
                    RAISE EXCEPTION 'This field must not be empty: further_information_fr';
                END IF;

                IF NOT (NEW.report_available_online = ANY {report_available_online}) THEN
                    RAISE EXCEPTION 'Invalid choice for report_available_online: "%"', NEW.report_available_online;
                END IF;

                IF NEW.rationale = '{{}}' THEN
                    RAISE EXCEPTION 'This field must not be empty: rationale';
                END IF;
                IF bad_rationale <> '' THEN
                    RAISE EXCEPTION 'Invalid choice for rationale: "%"', bad_rationale;
                END IF;
                NEW.rationale := ARRAY(
                    SELECT c FROM(SELECT unnest({rationale}) as c) u
                    WHERE c in (SELECT unnest(NEW.rationale)));

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
    return u'(ARRAY[' + u','.join(
        literal_string(unicode(c[0])) for c in choices) + u'])'
