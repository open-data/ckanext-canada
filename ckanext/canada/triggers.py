from ckanapi import LocalCKAN


def update_triggers():
    """Create/update triggers used by PD tables"""

    lc = LocalCKAN()

    # *_error functions return NULL or ARRAY[[field_name, error_message]]
    # required_error
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
            {u'argname': u'value', u'argtype': u'numeric'},
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
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'money'},
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
            {u'argname': u'value', u'argtype': u'boolean'},
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
    # END required_error
    # conditional_required_error
    lc.action.datastore_function_create(
        name=u'conditional_required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF (value = '') IS NOT FALSE THEN
                    RETURN ARRAY[[field_name, 'This field is required due to a response in a different field.']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'conditional_required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL OR value = '{}' THEN
                    RETURN ARRAY[[field_name, 'This field is required due to a response in a different field.']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'conditional_required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'date'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RETURN ARRAY[[field_name, 'This field is required due to a response in a different field.']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'conditional_required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'numeric'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RETURN ARRAY[[field_name, 'This field is required due to a response in a different field.']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'conditional_required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'int4'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RETURN ARRAY[[field_name, 'This field is required due to a response in a different field.']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'conditional_required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'money'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RETURN ARRAY[[field_name, 'This field is required due to a response in a different field.']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'conditional_required_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'boolean'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NULL THEN
                    RETURN ARRAY[[field_name, 'This field is required due to a response in a different field.']];
                END IF;
                RETURN NULL;
            END;
        ''')
    # END conditional_required_error
    lc.action.datastore_function_create(
        name=u'choice_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'choices', u'argtype': u'_text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition='''
            BEGIN
                IF value IS NOT NULL AND value <> '' AND NOT (value = ANY (choices)) THEN
                    -- \\t is used when converting errors to string
                    RETURN ARRAY[[field_name, 'Invalid choice: {}\uF8FF"'
                        || replace(value, E'\\t', ' ') || '"']];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'max_char_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'max_chars', u'argtype': u'numeric'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NOT NULL AND value <> '' AND LENGTH(value) > max_chars THEN
                    RETURN ARRAY[[field_name, 'This field has a maximum length of {} characters.\uF8FF' || max_chars]];
                END IF;
                RETURN NULL;
            END;
        ''')
    lc.action.datastore_function_create(
        name=u'trim_lead_trailing',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'}],
        rettype=u'text',
        definition=u'''
            DECLARE
                value_trimmed text := trim(both E'\t\n\x0b\x0c\r ' from value);
            BEGIN
                RETURN value_trimmed;
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
        definition='''
            DECLARE
                bad_choices text := array_to_string(ARRAY(
                    SELECT c FROM(SELECT unnest(value) as c) u
                    WHERE NOT c = ANY(choices)), ',');
            BEGIN
                IF bad_choices <> '' THEN
                    -- \\t is used when converting errors to string
                    error := ARRAY[[field_name, 'Invalid choice: {}\uF8FF"'
                        || replace(bad_choices, E'\\t', ' ') || '"']];
                END IF;
                clean := ARRAY(
                    SELECT c FROM(SELECT unnest(choices) as c) u
                    WHERE c = ANY(value));
            END;
        ''')

    # return record with .clean (normalized value) and .error
    # (NULL or ARRAY[[field_name, error_message]])
    # Dev NOTE: \p{} regex does not work in PSQL, need to use the [:alpha:] from POSIX
    #FIXME: blanks E.g. Ottawa, , Canada or Ottawa, Canada,
    lc.action.datastore_function_create(
        name='destination_clean_error',
        or_replace=True,
        arguments=[
            {'argname': 'value', 'argtype': 'text'},
            {'argname': 'field_name', 'argtype': 'text'},
            {'argname': 'clean', 'argtype': 'text', 'argmode': 'out'},
            {'argname': 'error', 'argtype': '_text', 'argmode': 'out'}],
        rettype='record',
        definition='''
            DECLARE
                destination_match text[] := regexp_split_to_array(value::text, ','::text);
                destination_match_group text;
                clean_val text := NULL;
            BEGIN
                IF value <> '' AND (array_length(destination_match, 1) <= 1 OR array_length(destination_match, 1) > 3) THEN
                    error := ARRAY[[field_name, 'Invalid format for destination: "{}". Use <City Name>, <State/Province Name>, <Country Name> for Canada and US, or <City Name>, <Country Name> for international (e.g. Ottawa, Ontario, Canada or London, England)\uF8FF' || value]];
                END IF;
                IF value <> '' AND array_length(destination_match, 1) > 1 AND array_length(destination_match, 1) <= 3 THEN
                    FOREACH destination_match_group IN ARRAY destination_match LOOP
                        clean_val := array_to_string(ARRAY[clean_val, array_to_string(regexp_match(destination_match_group::text, '^\s*(.+?)\s*$'::text), ''::text)], ', '::text);
                    END LOOP;
                    clean := clean_val;
                END IF;
            END;
        ''')

    # return record with .clean (normalized value) and .error
    # (NULL or ARRAY[[field_name, error_message]])
    # Dev NOTE: \p{} regex does not work in PSQL, need to use the [:alpha:] from POSIX
    #FIXME: blanks E.g. Ottawa, , Canada or Ottawa, Canada,
    lc.action.datastore_function_create(
        name='multi_destination_clean_error',
        or_replace=True,
        arguments=[
            {'argname': 'value', 'argtype': 'text'},
            {'argname': 'field_name', 'argtype': 'text'},
            {'argname': 'clean', 'argtype': 'text', 'argmode': 'out'},
            {'argname': 'error', 'argtype': '_text', 'argmode': 'out'}],
        rettype='record',
        definition='''
            DECLARE
                destination_matches text[] := regexp_split_to_array(value::text, ';'::text);
                destination_matches_group text;
                destination_match text[];
                destination_match_group text;
                clean_val text := NULL;
                clean_inner_val text := NULL;
            BEGIN
                IF value <> '' THEN
                    FOREACH destination_matches_group IN ARRAY destination_matches LOOP
                        destination_match := regexp_split_to_array(destination_matches_group, ','::text);
                        IF array_length(destination_match, 1) <= 1 OR array_length(destination_match, 1) > 3 THEN
                            error := error || ARRAY[[field_name, 'Invalid format for destination: "{}". Use <City Name>, <State/Province Name>, <Country Name> for Canada and US, or <City Name>, <Country Name> for international (e.g. Ottawa, Ontario, Canada or London, England)\uF8FF' || destination_matches_group]];
                        ELSE
                            clean_inner_val := NULL;
                            FOREACH destination_match_group IN ARRAY destination_match LOOP
                                clean_inner_val := array_to_string(ARRAY[clean_inner_val, array_to_string(regexp_match(destination_match_group::text, '^\s*(.+?)\s*$'::text), ''::text)], ', '::text);
                            END LOOP;
                        END IF;
                        clean_val := array_to_string(ARRAY[clean_val, clean_inner_val], ';'::text);
                    END LOOP;
                    clean := clean_val;
                END IF;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'must_be_empty_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'numeric'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF value IS NOT NULL THEN
                    RETURN ARRAY[[field_name, 'This field must be empty']];
                END IF;
                RETURN NULL;
            END;
        ''')

    # A: When sysadmin passes '*' as user_modified, replace with '' and
    #    set created+modified values to NULL. This is used when restoring
    #    earlier migrated data that had no record of the
    #    user/created/modified values
    # B: If the contextual user is a sysadmin, do not update the modified time
    #    or the modified user.
    # C: Otherwise update created+modified dates and replace user with
    #    current user
    lc.action.datastore_function_create(
        name=u'update_record_modified_created_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            DECLARE
                req_record_modified timestamp := NEW.record_modified;
                req_user_modified text := NEW.user_modified;
                username text NOT NULL := (SELECT username
                    FROM datastore_user LIMIT 1);
                sysadmin boolean NOT NULL := (SELECT sysadmin
                    FROM datastore_user LIMIT 1);
            BEGIN
                IF NOT sysadmin THEN
                    NEW.record_created := NULL;
                    req_record_modified := NULL;
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
                IF req_record_modified IS NULL THEN
                    NEW.record_modified := now() at time zone 'utc';
                ELSE
                    NEW.record_modified := req_record_modified;
                END IF;
                IF (req_user_modified = '') IS NOT FALSE THEN
                    NEW.user_modified := username;
                ELSE
                    NEW.user_modified := req_user_modified;
                END IF;
                RETURN NEW;
            END;
            ''')

    lc.action.datastore_function_create(
        name=u'protect_user_votes_trigger',
        or_replace=True,
        rettype=u'trigger',
        definition=u'''
            DECLARE
                req_user_votes int := NEW.user_votes;
                sysadmin boolean NOT NULL := (SELECT sysadmin
                    FROM datastore_user LIMIT 1);
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
        name=u'int_na_nd_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value', u'argtype': u'text'},
            {u'argname': u'field_name', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            DECLARE
                value text := value;
            BEGIN
                IF value ~ '^-?[0-9]+$' THEN
                    IF value::int < 0 THEN
                        RETURN ARRAY[[field_name, 'This value must not be negative']];
                    END IF;
                ELSE
                    IF value != 'NA' AND value != 'ND' THEN
                        RETURN ARRAY[[field_name, 'This field must be either a number, "NA", or "ND"']];
                    END IF;
                END IF;
                RETURN NULL;
            END;
        ''')

    lc.action.datastore_function_create(
        name=u'both_languages_error',
        or_replace=True,
        arguments=[
            {u'argname': u'value_en', u'argtype': u'text'},
            {u'argname': u'field_name_en', u'argtype': u'text'},
            {u'argname': u'value_fr', u'argtype': u'text'},
            {u'argname': u'field_name_fr', u'argtype': u'text'}],
        rettype=u'_text',
        definition=u'''
            BEGIN
                IF (value_en = '') IS NOT FALSE AND NOT((value_fr = '') IS NOT FALSE) THEN
                  RETURN ARRAY[[field_name_en, 'This text must be provided in both languages']];
                END IF;
                IF (value_fr = '') IS NOT FALSE AND NOT((value_en = '') IS NOT FALSE) THEN
                  RETURN ARRAY[[field_name_fr, 'This text must be provided in both languages']];
                END IF;
                RETURN NULL;
            END;
        ''')
