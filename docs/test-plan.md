## Test Plan

|icon | interaction method |
| --- | --- |
| ⚫ | console server access |
| 🔴 | sysadmin user web |
| 🔵 | admin user web |
| 🔘 | editor user web |

### Registry

- [ ] ⚫ create/update organizations with `ckanapi load organizations -I transitional_orgs.jsonl`
- [ ] :white_square_button: create/update organizations with `ckanapi load organizations -I transitional_orgs.jsonl`
- [ ] :white_square_button: create/set :wrench: sysadmin user with `ckan --plugin=ckan sysadmin add <user>`

- [ ] :white_square_button: export organizations with `ckanapi dump organizations | bin/transitional_org_filter.py > exported_orgs.jsonl`
  - [ ] :white_square_button: verify no differences with imported `transitional_orgs.jsonl` file

- [ ] :microphone: new admin visit front page then fills request account form
  - [ ] :microphone: retrieves confirmation email
  - [ ] :microphone: log in and see limited home page with no access to records (yet)
- [ ] :wrench: sysadmin user assigns :microphone: admin user to an existing organization as an Admin

- [ ] :eyeglasses: editor user signs up as above
- [ ] :microphone: admin user assigns :eyeglasses: editor user to an organization as an Editor

- [ ] :eyeglasses: user resets password with password reset form
  - [ ] :eyeglasses: retrieve reset email and follow link
  - [ ] :eyeglasses: log in with new password


- [ ] :microphone:

- [ ] :bicyclist: new user log in and sees full home page with all quick links
  - [ ] :bicyclist: search all datasets shows


### Portal
