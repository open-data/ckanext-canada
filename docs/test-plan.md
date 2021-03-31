# Test Plan

|icon | interaction method |
| --- | --- |
| ⚫ | console server access |
| 🔴 | sysadmin user web |
| 🔵 | admin user web |
| 🔘 | editor user web |

## 1. Registry

### 1.1 Initializing an empty db (not required for existing sites)

- [ ] ⚫ create/update organizations with `ckanapi load organizations -I transitional_orgs.jsonl`
- [ ] ⚫ create/set 🔴 sysadmin user with `ckan --plugin=ckan sysadmin add <user>`

- [ ] ⚫ export organizations with `ckanapi dump organizations | bin/transitional_org_filter.py > exported_orgs.jsonl`
  - [ ] ⚫ verify no differences with imported `transitional_orgs.jsonl` file

- [ ] ⚫ load datasets with `ckanapi load datasets -zI od-do-canada.jsonl.gz`

### 1.2 Account sign-up and approval

- [ ] 🔵 new admin visit front page then fills request account form
  - [ ] 🔵 retrieves confirmation email
  - [ ] 🔵 log in and see limited home page with no access to records (yet)
- [ ] 🔴 sysadmin received an email notification of the new account request
- [ ] 🔴 sysadmin user assigns 🔵 admin user to an existing organization as an Admin

- [ ] 🔘 editor user signs up as above
- [ ] 🔵 admin user assigns 🔘 editor user to an organization as an Editor

- [ ] 🔘 editor user resets password with password reset form
  - [ ] 🔘 retrieve reset email and follow link
  - [ ] 🔘 log in with new password

### 1.3 Asset creation, editing and publishing

- [ ] 🔘 editor user creates new dataset
  - [ ] 🔘 submit dataset form with missing values, verify all required fields marked as errors
  - [ ] 🔘 fill and submit complete dataset marked ready to publish, proceed to add a resource
  - [ ] 🔘 submit resource form with missing values, verify all required fields marked as errors
  - [ ] 🔘 fill and submit complete resource with uploaded file, proceed to add another resource
  - [ ] 🔘 fill and submit complete related item, save dataset
  - [ ] 🔘 verify dataset, resource and related items display as expected

- [ ] 🔘 editor user creates new information asset
  - [ ] 🔘 submit asset form with missing values, verify all required fields marked as errors
  - [ ] 🔘 fill and submit complete asset marked ready to publish, proceed to add a resource
  - [ ] 🔘 submit resource form with missing values, verify all required fields marked as errors
  - [ ] 🔘 fill and submit complete resource with uploaded file, proceed to add another resource
  - [ ] 🔘 fill and submit complete related item, save asset
  - [ ] 🔘 verify asset, resource and related items display as expected

- [ ] 🔴 sysadmin views publish datasets page and sees one dataset and one information asset
  - [ ] 🔴 publish both and see no more datasets to publish
  - [ ] PORTAL: wait for publishing job and verify published dataset and information asset are now on the portal
  - [ ] 🔴 edit the dataset just published and remove the "portal release date" value
  - [ ] 🔴 visit the dataset publishing page to confirm that the dataset reappears
  - [ ] PORTAL: wait for publishing job and verify that dataset was removed from the portal

### 1.4 Suggested dataset updates

- [ ] 🔘 editor user add multiple status updates to a suggestion
  - [ ] 🔘 verify that updates are re-sorted into correct date order on save
  - [ ] 🔘 verify that required fields are enforced by the form
  - [ ] 🔘 remove some updates and check that they are properly removed
  - [ ] PORTAL: wait for publishing job and verify that status updates are displayed

### 1.5 Organization changes

- [ ] 🔴 sysadmin create a new organization, verify that it appears in org list
- [ ] 🔵 admin user edit details of their organization
  - [ ] 🔵 verify that title change appears in org list
  - [ ] ⚫ reindex datasets for this organization with `paster --plugin=ckan search-index rebuild -r -e`
  - [ ] 🔵 verify that org title change has been applied to datasets

### 1.6 Proactive disclosure

- [ ] 🔘 editor user visit one of the PD types with enforced validation (e.g. consultations or contracts)
  - [ ] 🔘 download excel template and fill see that errors and missing fields are hilighted as text is entered
  - [ ] 🔘 upload excel template with two new records
  - [ ] 🔘 verify new records are displayed in the preview table
  - [ ] 🔘 select records in preview and click edit in excel to download pre-populated template
  - [ ] 🔘 verify that records appear in downloaded template and can be re-uploaded with changes
  - [ ] 🔘 select and delete records from the preview table
  - [ ] ⚫ publish changes to search and exported csv file with e.g. `make -f bin/pd/Makefile consultations`
  - [ ] PORTAL: verify updated records visible on search and exported csv

## 2. Portal

- [ ] view dataset and resource pages
  - [ ] verify formatting and display of all fields
  - [ ] verify display of map (e.g. for the [open data portal catalogue](https://open.canada.ca/data/en/dataset/c4c5c7f1-bfa6-4ff6-b4a0-c164cb2060f7))
  - [ ] verify similar records are shown and appropriate
  - [ ] verify rate this dataset links to Drupal rating page and shows ratings
- [ ] download an uploaded resource from a dataset page
- [ ] follow link to an external resource from a dataset page
