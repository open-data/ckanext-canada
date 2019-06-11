from ckanapi import LocalCKAN
from ckantoolkit import h


def update_triggers():
    """Create/update triggers used by PD tables"""

    lc = LocalCKAN()

    # *_error functions return NULL or ARRAY[[field_name, error_message]]
    lc.action.datastore_function_create(
        name=u'required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF (value = '') IS NOT FALSE THEN
                    RETURN ARRAY[[field_name, 'This field must not be empty']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL OR value = '{}' THEN
                    return ARRAY[[field_name, 'This field must not be empty']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'date'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RETURN ARRAY[[field_name, 'This field must not be empty']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'int4'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RETURN ARRAY[[field_name, 'This field must not be empty']];
                END IF;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'choice_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'choices', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=ur'''
            BEGIN
                IF NOT (value = ANY (choices)) THEN
                    -- \t is used when converting errors to string
                    RETURN ARRAY[[field_name, 'Invalid choice: "'
                        || replace(value, E'\t', ' ') || '"']];
                END IF;
                RETURN NULL;
            END;
        ''')
    # return record with .clean (normalized value) and .error
    # (NULL or ARRAY[[field_name, error_message]])
    lc.action.datastore_function_create(
        name=u'choices_clean_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'_text'},
            {u'argname': u'choices', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'},
            {u'argname': u'clean', u'argtype': u'_text', u'argmode': u'out'},
            {u'argname': u'error', u'argtype': u'_text', u'argmode': u'out'}],
        rettype=u'record',
        definition=ur'''
            DECLARE
                bad_choices text := array_to_string(ARRAY(
                    SELECT unnest(value)
                    EXCEPT SELECT unnest(choices)), ', ');
            BEGIN
                IF bad_choices <> '' THEN
                    -- \t is used when converting errors to string
                    error := ARRAY[[field_name, 'Invalid choice: "'
                        || replace(bad_choices, E'\t', ' ') || '"']];
                END IF;
                clean := ARRAY(
                    SELECT c FROM(SELECT unnest(choices) as c) u
                    WHERE c in (SELECT unnest(value)));
            END;
        ''')

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
                IF value IS NULL OR value = '{}' THEN
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
        name=u'not_empty',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'numeric'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RAISE EXCEPTION 'This field must not be empty: %', field_name;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'only_empty',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'numeric'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        definition=u'''
            BEGIN
                IF value IS NOT NULL THEN
                    RAISE EXCEPTION 'This field must be empty: %', field_name;
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

    # A: When sysadmin passes '*' as user_modified, replace with '' and
    #    set created+modified values to NULL. This is used when restoring
    #    earlier migrated data that had no record of the
    #    user/created/modified values
    # B: Otherwise update created+modified dates and replace user with
    #    current user
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
                IF NOT sysadmin THEN
                    req_user_modified := NULL;
                END IF;
                IF TG_OP = 'INSERT' THEN
                    IF req_user_modified = '*' THEN
                        NEW.user_modified := '';
                        NEW.record_created := NULL;
                        NEW.record_modified := NULL;
                        RETURN NEW;
                    END IF;
                    IF NEW.record_created IS NULL THEN
                        NEW.record_created := now() at time zone 'utc';
                    END IF;
                    IF NEW.record_modified IS NULL THEN
                        NEW.record_modified := NEW.record_created;
                    END IF;
                    IF (req_user_modified = '') IS NOT FALSE THEN
                        NEW.user_modified := username;
                    END IF;
                    RETURN NEW;
                END IF;

                IF req_user_modified = '*' THEN
                    NEW.user_modified := '';
                    NEW.record_created := NULL;
                    NEW.record_modified := NULL;
                    IF OLD = NEW THEN
                        RETURN NULL;
                    END IF;
                    RETURN NEW;
                END IF;

                IF NEW.record_created IS NULL THEN
                    NEW.record_created := OLD.record_created;
                END IF;
                IF NEW.record_modified IS NULL THEN
                    NEW.record_modified := OLD.record_modified;
                END IF;
                IF (req_user_modified = '') IS NOT FALSE THEN
                    NEW.user_modified := OLD.user_modified;
                END IF;
                IF OLD = NEW THEN
                    RETURN NULL;
                END IF;
                NEW.record_modified := now() at time zone 'utc';
                IF (req_user_modified = '') IS NOT FALSE THEN
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

    grants_choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('grants'))
    lc.action.datastore_function_create(
        name=u'grants_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM not_empty(NEW.ref_number, 'ref_number');

                PERFORM not_empty(NEW.amendment_number, 'amendment_number');
                IF NEW.amendment_number <> 0 THEN
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
                    PERFORM not_empty(NEW.agreement_type, 'agreement_type');
                    PERFORM choice_one_of(
                        NEW.agreement_type,
                        {agreement_type},
                        'agreement_type');
                    IF NOT ((NEW.recipient_type = '') IS NOT FALSE) THEN
                        PERFORM choice_one_of(
                            NEW.recipient_type,
                            {recipient_type},
                            'recipient_type');
                    END IF;
                    PERFORM not_empty(NEW.recipient_legal_name, 'recipient_legal_name');
                    PERFORM not_empty(NEW.recipient_country, 'recipient_country');
                    PERFORM choice_one_of(
                        NEW.recipient_country,
                        {recipient_country},
                        'recipient_country');
                    IF NEW.recipient_country = 'CA' THEN
                        PERFORM not_empty(NEW.recipient_province, 'recipient_province');
                        PERFORM choice_one_of(
                            NEW.recipient_province,
                            {recipient_province},
                            'recipient_province');
                    END IF;
                    PERFORM not_empty(NEW.recipient_city, 'recipient_city');
                    PERFORM not_empty(NEW.description_en, 'description_en');
                    PERFORM not_empty(NEW.description_fr, 'description_fr');
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

    grants_nil_choices = dict(
        (f['datastore_id'], f['choices'])
        for f in h.recombinant_choice_fields('grants-nil'))
    lc.action.datastore_function_create(
        name=u'grants_nil_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            BEGIN
                PERFORM not_empty(NEW.fiscal_year, 'fiscal_year');
                PERFORM choice_one_of(NEW.fiscal_year, {fiscal_year}, 'fiscal_year');
                PERFORM not_empty(NEW.quarter, 'quarter');
                PERFORM choice_one_of(NEW.quarter, {quarter}, 'quarter');
                RETURN NEW;
            END;
            '''.format(
                fiscal_year=pg_array(grants_nil_choices['fiscal_year']),
                quarter=pg_array(grants_nil_choices['quarter']),
            )
        )

def pg_array(choices):
    from ckanext.datastore.helpers import literal_string
    return u'ARRAY[' + u','.join(
        literal_string(unicode(c[0])) for c in choices) + u']'
