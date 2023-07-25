# coding=UTF-8
"""
Copies of strings that need translations but babel can't find, e.g. text embedded in triggers
"""
_ = lambda x: x

# contracts.yaml
_("This field must be populated with an NA if an amendment is disclosed under Instrument Type.")
_("If N/A, then Instrument Type must be identified as a standing offer/supply arrangement (SOSA)")
_("If the value XX (none) is entered, then no other value can be entered in this field.")
_("If the value NA (not applicable) is entered, then no other value can be entered in this field.")
_("This field must be NA (not applicable) if the Agreement Type or Trade Agreement field is not 0 (none) "
  "or XX (none), as applicable.")
_("If the value 00 (none) is entered, then no other value can be entered in this field.")
_('This field must contain the first three digits of a postal code in A1A format or the value "NA"')
_("This field must be N, No or Non, if the Agreement Type or Trade Agreement field is not 0 (none) or XX "
  "(none), as applicable.")
_("This field must be N, No or Non, if the Procurement Strategy for Aboriginal Business field is MS or VS.")
_("This field may only be populated with a 1 if the solicitation procedure is identified as "
  "non-competitive (TN) or Advance Contract Award Notice (AC)")
_("This field may only be populated with a 0 if a Call-up against a standing offer or supply arrangement "
  "was identified in the Contracting Entity data field")
_('This field may only be populated with "0" if the procurement was identified as non-competitive (TN) or '
  "advance contract award notice (AC).")
_("This field may not be populated with 1, 2, 3 or 4 if the procurement was identified as non-competitive "
  "or Advance Contract Award Notice.")
_("Commodity Type of G for Goods which requires a Delivery Date and not a Contract Period Start Date. "
  "Please either change the Commodity Type to S or remove the date from the Contract Period Start Date "
  "field")
_("If the value XX (none) is entered here, then the following three fields must be identified as NA or N, "
  "as applicable: Comprehensive Land Claim Agreement, Procurement Strategy for Aboriginal Business, "
  "Procurement Strategy for Aboriginal Business Incidental Indicator")

# strings from core
_("Create Dataset")
