from datetime import datetime
import simplejson
import sys

# Quick script to transform the CANSIM and Summary Table JSON data from CKAN 2.0 to 2.3
#  -  Replace subject UUID with the list
#  -  Add a portal_release_date field
#  -  Change ready_to_publish value from 1 to "true"
#  -  Change "catalog_type": "Data | Donn\u00e9es" to "type": "dataset"
#
# The script reads from stdin and prints the modified stirng to stdout

subject_replacements = {
    '86EB6B9F-344C-4C3E-982D-53164994516A': ["Arts Music Literature  Arts musique litt\u00e9rature"],
    '04D07B59-8D90-455C-9C84-7C1DF833473B': ["Agriculture  Agriculture"],
    '3AC17C98-F356-4CC8-BAEB-886037E5C2EE': ["Economics and Industry  \u00c9conomie et industrie"],
    '0AA56AD7-4CB3-4F7E-A741-9503231BC697': ["Education and Training  \u00c9ducation et formation"],
    '1BEB670E-8A73-4217-BCD2-6189F92053E2': ["Government and Politics  Gouvernement et vie politique"],
    '7D5846DC-74D0-415A-A853-318DCD89E731': ["Health and Safety  Sant\u00e9 et s\u00e9curit\u00e9"],
    '704B3281-511F-4FFB-85C7-D437892CECE2': ["History and Archaeology  Histoire et arch\u00e9ologie"],
    '70B236D3-B7CE-443C-89C2-FEE7277F41C9': ["Information and Communications  Information et communication"],
    'F97F8830-B980-4A20-9B13-D572F1C094F0': ["Labour  Travail et emploi"],
    '43BB3E2A-DA38-4005-9A57-8CBEB60F5FE0': ["Language and Linguistics  Langue et linguistique"],
    'BBBDFE5C-9EC2-4393-A801-5866D176CF08': ["Law  Droit"],
    '8ACBA39A-BD70-4113-98F8-8A8A11E095C1': ["Military  Histoire et science militaire"],
    '9E3985CD-58EC-4DBA-AF73-5711AF379DE4': ["Nature and Environment  Nature et environnement"],
    'BEF4D60C-E2D1-46B9-96C0-B55902F076F1': ["Persons  Personnes"],
    'D1EFA3C1-FC9D-4E53-9BD4-90434626D213': ["Processes  Liens et fonctions"],
    '8C3A29E9-292D-47E3-8163-51FF8AB4E6D3': ["Society and Culture  Soci\u00e9t\u00e9 et culture"],
    'FB6B00F0-6271-42D6-ACB7-FFE664843698': ["Science and Technology  Sciences et technologie"],
    '949D4BF7-0AF0-49BD-8C76-AF0B82E72CC2': ["Transport  Transport"]
}


def main():
    release_date = datetime.now().strftime("%Y-%m-%d")
    try:
        for line in sys.stdin:
            rec = simplejson.loads(line)
            rec["portal_release_date"] = release_date
            rec["ready_to_publish"] = "true"
            if "catalog_type" in rec:
                del rec["catalog_type"]
            rec["type"] = "dataset"
            if "subject" in rec:
                if rec["subject"] in subject_replacements:
                    rec["subject"] = subject_replacements[rec["subject"]]
                else:
                    print >> sys.stderr, 'Invalid subject "{0}" for {1}'.format(rec["subject"], rec["id"])
                    continue
            print simplejson.dumps(rec)

    except IOError:
        print >> sys.stderr, 'Error while reading line.'


main()
