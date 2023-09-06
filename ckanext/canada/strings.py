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

# strings from security
_("Please upload a file or link to an external resource")
_("Cannot upload files of this type")
_("Cannot link files of this type")

# strings from scheming
_('These fields have been removed, click update below to save your changes.')
_('These fields have been removed.')

# PD types
## Administrative Aircraft
_('Proactive Disclosure - Use of Administrative Aircraft')
_('Use of Administrative Aircraft')
_('Access, upload and modify government administrative aircraft use')
## ATI
_('ATI Summaries')
_('Access, upload and modify the monthly ATI Summaries and ATI Nothing to Report for your organization')
_('ATI Nothing to Report')
_('Please enter a valid year')
_('Please enter a month number from 1-12')
_('This value must not be negative')
## Briefing Notes
_('Proactive Disclosure - Briefing Note Titles and Numbers')
_('Briefing Note Titles and Numbers')
_('Access, upload and modify the Briefing Note Titles and Numbers reports for your organization')
## Consultations
_('Open Dialogue - Consultations')
_('Consultations')
_('Access, upload and modify consultation reports for your organization')
_('If Status is set to: Not Going Forward, Publish Record must be set to No')
## Contracts
_('Proactive Publication - Contracts over $10,000')
_('Contracts over $10,000')
_('Access, upload and modify the Contracts over 10K reports for your organization')
_('Proactive Publication - Contracts Nothing to Report')
_('Contracts Nothing to Report')
_('This field must contain the first three digits of a postal code in A1A format or the value "NA"')
_("This field must be populated with an NA if an amendment is disclosed under Instrument Type.")
_('This field is limited to only 3 or 4 digits.')
_("If N/A, then Instrument Type must be identified as a standing offer/supply arrangement (SOSA)")
_("If the value XX (none) is entered, then no other value can be entered in this field.")
_('Discontinued as of 2022-01-01')
_('Must be left blank when trade agreements specified')
_("If the value NA (not applicable) is entered, then no other value can be entered in this field.")
_('The field is limited to eight alpha-numeric digits or less.')
_("If the value 00 (none) is entered, then no other value can be entered in this field.")
_('If TC, TN or AC is selected in the Solicitation Procedure data field with a value other than XX (None) selected in the Trade Agreement data field, then a Limited Tendering value other than 00 (none) must be entered.')
_('If “TC” (Competitive - Traditional), “TN” (Non-Competitive) or “AC” (Advanced Contract Award Notice) is selected and trade agreement with a value other than “XX” (None) is selected, limited tendering cannot have a value of “0” or “00” (None).')
_("This field must be N, No or Non, if the Procurement Strategy for Aboriginal Business field is MS or VS.")
_('This field must be populated with a 1 if the solicitation procedure is identified as non-competitive (TN) or Advance Contract Award Notice (AC).')
_('If this field is populated, it must be with a “0” if the procurement was identified as non-competitive (TN) or advance contract award notice (AC) or was identified as an Amendment (A) in the Instrument type data field.')
_('This field may only be populated with “0” if the procurement was identified as competitive (open bidding (OB), traditional competitive (TC) or selective tendering (ST)).')
## Contracts Aggregated
_('Proactive Publication - Aggregated Contracts from -$10,000 to $10,000')
_('Aggregated Contracts from -$10,000 to $10,000')
_('Access, upload and modify the aggregated Contracts from -$10K to $10K reports for your organization')
_('This must list the year you are reporting on (not the fiscal year).')
## DAC
_('Proactive Disclosure - Departmental Audit Committee')
_('Departmental Audit Committee')
_('Access, upload and modify your Departmental Audit Committee members’ remuneration and expenses.')
## Experimental
_('Experimentation Inventory')
_('Access, upload and modify the Experimentation Inventory for your organization')
## Grants
_('Proactive Disclosure - Grants and Contributions')
_('Grants and Contributions')
_('Access, upload and modify the Grants and Contributions reports for your organization')
_('Proactive Disclosure - Grants and Contributions Nothing to Report')
_('Grants and Contributions Nothing to Report')
## Hospitality
_('Proactive Disclosure - Hospitality Expenses')
_('Hospitality Expenses')
_('Access, upload and modify the quarterly hospitality expenses for your organization')
_('Proactive Disclosure - Hospitality Nothing to Report')
_('Hospitality Nothing to Report')
## Inventory
_('Open Data Inventory')
_('This dataset houses your departmental open data inventory. This is where you can access and upload your open data inventory template.')
## NAP5
_('5th National Action Plan on Open Government Tracker')
_('Access, upload and modify the National Action Plan on Open Government Tracker for your organization')
## QP Notes
_('Proactive Disclosure - Question Period Notes')
_('Question Period Notes')
_('Access, upload and modify Question Period notes for your organization')
## Reclassification
_('Proactive Disclosure - Position Reclassification')
_('Position Reclassification')
_('Access, upload and modify the position reclassification reports for your organization')
_('Proactive Disclosure - Position Reclassification Nothing to Report')
_('Position Reclassification Nothing to Report')
## Service Inventory
_('Service Inventory')
_('Access, upload and modify the Service Inventory of external and internal enterprise services for your organization')
## Travel Annual
_('Proactive Disclosure - Annual Travel, Hospitality and Conferences')
_('Annual Travel, Hospitality and Conferences')
_('This dataset includes all of the annual reports on travel expenses incurred within your organization.')
## Travel Quaterly
_('Proactive Disclosure - Travel Expenses')
_('Travel Expenses')
_('Access, upload and modify the monthly travel expense reports for your organization')
_('Proactive Disclosure - Travel Expenses Nothing to Report')
_('Travel Expenses Nothing to Report')
## Wrongdoing
_('Proactive Disclosure - Acts of Founded Wrongdoing')
_('Acts of Founded Wrongdoing')
_('Access, upload and modify the Acts of Founded Wrongdoing reports for your organization')
