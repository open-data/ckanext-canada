# coding=UTF-8
"""
Copies of strings that need translations but babel can't find, e.g. text embedded in triggers
"""
_ = lambda x: x

# CKAN Core
# Include any custom strings put into our CKAN fork.
# And any strings that are fuzzy in French so that
# we can fully transalate them in this extension.
_("Create Dataset")
_("Not authorized to access {group} members download")
_("Members not found")
_("N/A")
_("Username")
_("Email")
_("Name")
_("Role")
_("members")
_("CSV")
_("A related item has been added")
_("A resource has been added")
_("Resource id already exists.")
_("Invalid characters in resource id")
_("Invalid length for resource id")
_("Resource view id already exists")
_("Value must be one of {}")
_("Could not parse the value as a valid JSON object")
_("Could not parse extra '{name}' as valid JSON")
_("Dear %(user_name)s,")
_("Invite for %(site_title)s")
_("Dataset Deleted")
_("Created On")
_("Choose format")
_("Submit")
_("{actor} deleted the {view_type} view {view}")
_("Request Reset")
_("Create API Token")
_("Token")
_("Last access")
_("Actions")
_("Revoke")
_("You haven't created any API Tokens.")
_("Beta")  # in our fork only
_("Deleted API token %s")  # TODO: remove after upstream fix
_("Organization created.")  # TODO: remove after upstream fix
_("Group created.")  # TODO: remove after upstream fix
_("Organization updated.")  # TODO: remove after upstream fix
_("Group updated.")  # TODO: remove after upstream fix
_("Assigned %s as a member.")  # TODO: remove after upstream fix
_("Assigned %s as an editor.")  # TODO: remove after upstream fix
_("Assigned %s as an admin.")  # TODO: remove after upstream fix
_("View deleted.")  # TODO: remove after upstream fix
_("View updated.")  # TODO: remove after upstream fix
_("View created.")  # TODO: remove after upstream fix
_('Promoted {} to sysadmin')
_('Revoked sysadmin permission from {}')
_('Current Sysadmins')
_('Revoke Sysadmin permission')
_('Promote user to Sysadmin')
_('Promote')
_('Cannot modify your own sysadmin privileges')
_('Cannot modify sysadmin privileges for system user')
_('Show more')
_('Hide')

# strings from security
_("Please upload a file or link to an external resource")
_("Cannot upload files of this type")
_("Cannot link files of this type")
_('Your password must be {} characters or longer.')
_('Your password must consist of at least three of the following character sets: '
  'uppercase characters, lowercase characters, digits, punctuation & special characters.')
_('Your password cannot be the same as your username.')

# strings from scheming
_('These fields have been removed, click update below to save your changes.')
_('These fields have been removed.')

# strings from csrf
_("Your form submission could not be validated, please re-submit the form.")

# strings from configurations
_('Open Government Portal')
_('Open Government Portal (staging)')

# strings from misc triggers and recombinant tables
_('Single')
_('Repeatable')
_('Optional')
