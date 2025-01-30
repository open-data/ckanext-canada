# coding=UTF-8
"""
Copies of strings that need translations
but babel can't find, e.g. text embedded in triggers
"""
_ = lambda x: x  # noqa: E731

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
_("{actor} added the {view_type} view {view}")
_("{actor} changed the {view_type} view {view}")
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
_('Activity type')  # TODO: remove after upstream fix
_('Show more')
_('Hide')
_('User %s deleted. You are now logged out.')  # TODO: remove after upstream fix
_('User %s deleted.')  # TODO: remove after upstream fix
_('You can use <a href="#markdown" title="Markdown quick reference" data-target="popover" data-content="{}" data-html="true">Markdown formatting</a> here')
_("<pre><p>__bold text__</p><p>_italic text_</p><p>* list<br>* of<br>* items</p><p>1. numbered<br>2. list<br>3. of items</p><p>https://auto.link.ed/</p><p>[Formatted Link](https://formatted.link)</p><p>> block quote</p></pre><p class='text-muted'><b>Please note:</b> HTML tags are stripped out for security reasons</p>")
_('Rebuild Dataset Indices')  # TODO: remove after upstream contrib
_('Rebuild Search Index')  # TODO: remove after upstream contrib
_('Are you sure you want to re-index all the records for this site? This can take a long time if the site has a lot of records.')  # TODO: remove after upstream contrib
_('Re-index Site\'s Records')  # TODO: remove after upstream contrib
_('Are you sure you want to re-index all the records for this group? This can take a long time if the group has a lot of records.')  # TODO: remove after upstream contrib
_('Are you sure you want to re-index all the records for this organization? This can take a long time if the organization has a lot of records.')  # TODO: remove after upstream contrib
_('Re-index Group\'s Record.')  # TODO: remove after upstream contrib
_('Re-index Organization\'s Records')  # TODO: remove after upstream contrib
_('If you update an Group\'s title or name, it\'s datasets in the SOLR Index will not have the new title or name. To solve this, you can re-index all of the Group\'s records in a background job.')  # TODO: remove after upstream contrib
_('Records are in queue to be re-indexed.')  # TODO: remove after upstream contrib
_('Records already in queue to be re-indexed.')  # TODO: remove after upstream contrib
_('Unable to re-index records.')  # TODO: remove after upstream contrib
_('There are no records to index.')  # TODO: remove after upstream contrib
_('In queue to re-index records')  # TODO: remove after upstream contrib
_('Currently re-indexing records')  # TODO: remove after upstream contrib
_('All records indexed')  # TODO: remove after upstream contrib
_('Error indexing records')  # TODO: remove after upstream contrib
_('Could not delete resource because other resources in this dataset have errors:')
_('Could not create or update resource because other resources in this dataset have errors:')

# strings from security
_("Please upload a file or link to an external resource")
_("Cannot upload files of this type")
_("Cannot link files of this type")
_('Your password must be {} characters or longer.')
_('Your password must consist of at least three of the following character sets: '
  'uppercase characters, lowercase characters, digits, punctuation & special characters.')
_('Your password cannot be the same as your username.')
# FIXME: revise flash message
_('Your current password is too weak. Please create a new password before logging in again.')

# strings from scheming
_('These fields have been removed, click update below to save your changes.')
_('These fields have been removed.')

# strings from csrf
_("Your form submission could not be validated, please re-submit the form.")

# strings from configurations
_('Open Government Portal')
_('Open Government Portal (staging)')

# strings from xloader
_('Delete from DataStore')
_('Are you sure you want to delete the DataStore and Data Dictionary?')
_('Confirm Delete')

# strings from validation
_('Validation Information')
_('Validation status:')
_('Validation timestamp:')
_('Duration:')

# strings from misc triggers and recombinant tables
_('Single')
_('Repeatable')
_('Optional')

# strings from validation
_('Validation status')
_('Validation timestamp')
