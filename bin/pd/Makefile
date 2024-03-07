.DELETE_ON_ERROR:

targets := ati briefingt qpnotes consultations contracts contractsa dac experiment grants hospitalityq inventory \
	nap5 reclassification service travela travelq wrongdoing adminaircraft

csv_files := \
	ati.csv ati-nil.csv \
	briefingt.csv briefingt-nil.csv \
	qpnotes.csv qpnotes-nil.csv \
        contractsa.csv \
        contracts.csv contracts-nil.csv \
	consultations.csv \
	dac.csv \
	experiment.csv \
        grants.csv grants-nil.csv \
        hospitalityq.csv hospitalityq-nil.csv \
	inventory.csv \
	nap5.csv \
        reclassification.csv reclassification-nil.csv \
	service.csv service-std.csv \
        travela.csv \
        travelq.csv travelq-nil.csv \
        wrongdoing.csv \
		adminaircraft.csv

fdir := $(PD_FILTER_SCRIPT_DIRECTORY)
paster := $(REGISTRY_PASTER_COMMAND)
registry_python := $(REGISTRY_PYTHON_COMMAND)
combine := --plugin=ckanext-recombinant recombinant combine
registry_ini := $(REGISTRY_INI)
portal_ini := $(PORTAL_INI)
ckanapi := $(REGISTRY_CKANAPI_COMMAND)
ogc_search := $(OGC_SEARCH_COMMAND)
oc_search := $(OC_SEARCH_COMMAND)
backup_dir := $(PD_BACKUP_DIRECTORY)
tmp_dir := $(or $(PD_TMP_DIRECTORY),$(TMPDIR),/tmp)
registry_static := $(REGISTRY_STATIC_SMB_DIRECTORY)
portal_static := $(PORTAL_STATIC_SMB_DIRECTORY)

yyyy_mmdd := $(shell date "+%Y %m%d")
yyyy := $(word 1,$(yyyy_mmdd))
yyyymmdd := $(word 1,$(yyyy_mmdd))$(word 2,$(yyyy_mmdd))
isodate := $(shell TZ=UTC date "+%FT%T")
echo_date := echo $(isodate):

ifneq ($(backupsuffix),)
_backupsuffix := -$(backupsuffix)
endif

.PHONY: help
help:
	@echo Usage:
	@echo '    make target ... [workdir=/path/to/working/directory]'
	@echo
	@echo Targets:
	@echo '    nightly                  dump, filter, backup, upload, rebuild all targets'
	@echo '    dump-all                 dump all from datastore (workdir required)'
	@echo '    restore-all              restore all from last backup (workdir required)'
	@echo '    filter-all               filter all (workdir required)'
	@echo '    backup-all               create a new backup in pd_backups folder'
	@echo '                             [backupsuffix=example] to add suffix to backup'
	@echo '    upload-all               upload all targets'
	@echo '    rebuild-all              rebuild search for all targets'
	@echo

	@for t in $(targets); do \
		printf '    %-24s upload and rebuild search\n' "$$t"; \
	done

ifeq ($(fdir),)
$(error PD_FILTER_SCRIPT_DIRECTORY is undefined)
else ifeq ($(paster),)
$(error REGISTRY_PASTER_COMMAND is undefined)
else ifeq ($(registry_python),)
$(error REGISTRY_PYTHON_COMMAND is undefined)
else ifeq ($(registry_ini),)
$(error REGISTRY_INI is undefined)
else ifeq ($(portal_ini),)
$(error PORTAL_INI is undefined)
else ifeq ($(ckanapi),)
$(error REGISTRY_CKANAPI_COMMAND is undefined)
else ifeq ($(ogc_search),)
$(error OGC_SEARCH_COMMAND is undefined)
else ifeq ($(oc_search),)
$(error OC_SEARCH_COMMAND is undefined)
else ifeq ($(backup_dir),)
$(error PD_BACKUP_DIRECTORY is undefined)
else ifeq ($(registry_static),)
$(error REGISTRY_STATIC_SMB_DIRECTORY is undefined)
else ifeq ($(portal_static),)
$(error PORTAL_STATIC_SMB_DIRECTORY is undefined)

else ifeq ($(workdir),)
location = $(CURDIR)/$(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
self := $(location)

# Create and clean up working directory workdir=... not passed
# by calling the Makefile recursively
%:
	@workdir=`mktemp -d -p $(tmp_dir) -t pdmake.XXXXXXXX`; \
	trap 'rm -rf "$$workdir"' EXIT; \
	$(MAKE) -f $(self) --no-print-directory workdir=$$workdir $@

else

# needed by multiple filter rules, always create
$(shell mkdir -p $(workdir)/filtered)

.PHONY: nightly
nightly: filter-all backup-all upload-all rebuild-all

# no backup-all for staging
.PHONY: nightly-staging
nightly: filter-all upload-all rebuild-all


.PHONY: dump-all
dump-all:
# don't generate all at once when running in parallel
ifeq ($(findstring j,$(MAKEFLAGS)),)
	$(paster) $(combine) -a -d $(workdir) -c $(registry_ini)
endif

.PHONY: filter-all
filter-all: $(csv_files:%=$(workdir)/filtered/%)

.PHONY: backup-all
backup-all: $(backup_dir)/$(yyyy)/pd-$(yyyymmdd)$(_backupsuffix).tar.gz

$(backup_dir)/$(yyyy)/pd-$(yyyymmdd)$(_backupsuffix).tar.gz: \
                $(csv_files:%=$(workdir)/%)
              mkdir -p "$(backup_dir)/$(yyyy)"
              cd "$(workdir)" && tar czvf $@ $(csv_files)

.PHONY: restore-all
restore-all:
	cd "$(workdir)" && tar xzvf $(lastword $(sort $(wildcard $(backup_dir)/$(yyyy)/pd-*.tar.gz)))

.PHONY: upload-all
upload-all: $(targets:%=upload-%)

.PHONY: rebuild-all
rebuild-all: $(targets:%=rebuild-%)

###
###  ATI Summaries
###
.PHONY: ati
ati: upload-ati rebuild-ati

.PHONY: upload-ati
upload-ati: $(workdir)/filtered/ati-nil.csv $(workdir)/filtered/ati-all.csv
	@$(echo_date) Uploading ATI Summaries...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=19383ca2-b01a-487d-88f7-e1ffbc7d39c2 upload@"$(workdir)/filtered/ati-all.csv" \
	> /dev/null
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=5a1386a5-ba69-4725-8338-2f26004d7382 upload@"$(workdir)/filtered/ati-nil.csv" \
	> /dev/null

.PHONY: rebuild-ati
rebuild-ati: $(workdir)/filtered/ati.csv $(workdir)/filtered/ati-nil.csv
	@$(echo_date) Rebuilding ATI Summaries...
	@$(paster) --plugin=ckanext-canada ati rebuild --lenient -c $(portal_ini) \
	-f "$(workdir)/filtered/ati.csv" "$(workdir)/filtered/ati-nil.csv"

$(workdir)/ati.csv:
	$(paster) $(combine) ati -d $(workdir) -c $(registry_ini)

$(workdir)/ati-nil.csv:
	$(paster) $(combine) ati-nil -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/ati.csv: $(workdir)/ati.csv
	$(fdir)/filter_ati.py < $< > $@

$(workdir)/filtered/ati-all.csv: $(workdir)/ati.csv
	$(fdir)/filter_modified_created.py < $< > $@

$(workdir)/filtered/ati-nil.csv: $(workdir)/ati-nil.csv
	$(fdir)/filter_ati.py < $< > $@

###
###  Briefing Note Titles
###
.PHONY: briefingt
briefingt: upload-briefingt rebuild-briefingt

.PHONY: upload-briefingt
upload-briefingt: $(workdir)/filtered/briefingt.csv $(workdir)/filtered/briefingt-nil.csv
	@$(echo_date) Uploading Briefing Note Titles...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=299a2e26-5103-4a49-ac3a-53db9fcc06c7 upload@"$(workdir)/filtered/briefingt.csv" \
	> /dev/null
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=5e28b544-720b-4745-9e55-3aac6464a4fb upload@"$(workdir)/filtered/briefingt-nil.csv" \
	> /dev/null

.PHONY: rebuild-briefingt
rebuild-briefingt: $(workdir)/filtered/briefingt.csv $(workdir)/filtered/briefingt-nil.csv
	@$(echo_date) Rebuilding Briefing Note Titles...
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/briefingt.csv" --search briefingt --quiet

$(workdir)/briefingt.csv:
	$(paster) $(combine) briefingt -d $(workdir) -c $(registry_ini)

$(workdir)/briefingt-nil.csv:
	$(paster) $(combine) briefingt-nil -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/briefingt.csv: $(workdir)/briefingt.csv
	$(fdir)/filter_modified_created.py < $< > $@

$(workdir)/filtered/briefingt-nil.csv: $(workdir)/briefingt-nil.csv
	$(fdir)/filter_modified_created.py < $< > $@

###
###  Question Period Notes
###
.PHONY: qpnotes
qpnotes: upload-qpnotes rebuild-qpnotes

.PHONY: upload-qpnotes
upload-qpnotes: $(workdir)/filtered/qpnotes.csv $(workdir)/filtered/qpnotes-nil.csv
	@$(echo_date) Uploading Question Period Notes...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=c55a2862-7ec4-462c-a844-22acab664812 upload@"$(workdir)/filtered/qpnotes.csv" \
	> /dev/null
	# @$(ckanapi) action resource_patch -c $(registry_ini) \
	# id=TBD upload@"$(workdir)/filtered/qpnotes-nil.csv" \
	# > /dev/null

.PHONY: rebuild-qpnotes
rebuild-qpnotes: $(workdir)/filtered/qpnotes.csv $(workdir)/filtered/qpnotes-nil.csv
	@$(echo_date) Rebuilding Question Period Notes...
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/qpnotes.csv" --search qpnotes --quiet

	# @$(oc_search) import_data_csv --csv "$(workdir)/filtered/qpnotes-nil.csv" --search qpnotes --nothing_to_report

$(workdir)/qpnotes.csv:
	$(paster) $(combine) qpnotes -d $(workdir) -c $(registry_ini)

$(workdir)/qpnotes-nil.csv:
	$(paster) $(combine) qpnotes-nil -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/qpnotes.csv: $(workdir)/qpnotes.csv
	$(fdir)/filter_qpnotes.py < $< > $@

$(workdir)/filtered/qpnotes-nil.csv: $(workdir)/qpnotes-nil.csv
	$(fdir)/filter_modified_created.py < $< > $@

###
###  Contracts
###
.PHONY: contracts
contracts: upload-contracts rebuild-contracts

.PHONY: upload-contracts
upload-contracts: $(workdir)/filtered/contracts.csv $(workdir)/filtered/contracts-nil.csv
	@$(echo_date) Uploading Contracts...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=fac950c0-00d5-4ec1-a4d3-9cbebf98a305 upload@"$(workdir)/filtered/contracts.csv" \
	> /dev/null
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=fa4ff6c4-e9af-4491-9d4e-2b468e415a68 upload@"$(workdir)/filtered/contracts-nil.csv" \
	> /dev/null

.PHONY: rebuild-contracts
rebuild-contracts: $(workdir)/filtered/contracts.csv $(workdir)/filtered/contracts-nil.csv
	@$(echo_date) Rebuilding Contracts...
	@$(oc_search) contracts_amendments --contracts $(workdir)/filtered/contracts.csv --amendments $(workdir)/filtered/contract-amendments.csv --tmpdir $(workdir)
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/contract-amendments.csv" --search contracts --quiet

$(workdir)/contracts.csv:
	$(paster) $(combine) contracts -d $(workdir) -c $(registry_ini)

$(workdir)/contracts-nil.csv:
	$(paster) $(combine) contracts-nil -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/contracts.csv: $(workdir)/contracts.csv
	$(fdir)/filter_contracts.py < $< > $@
$(workdir)/filtered/contracts-nil.csv: $(workdir)/contracts-nil.csv
	$(fdir)/filter_contracts_nil.py < $< > $@

###
###  Aggregated Contracts
###
.PHONY: contractsa
contractsa: upload-contractsa rebuild-contractsa

.PHONY: upload-contractsa
upload-contractsa: $(workdir)/filtered/contractsa.csv
	@$(echo_date) Uploading Aggregated Contracts...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=2e9a82e2-bb18-4bff-a61e-59af3b429672 upload@"$(workdir)/filtered/contractsa.csv" \
	> /dev/null
.PHONY: rebuild-contractsa
	# no search for aggregated contracts

$(workdir)/contractsa.csv:
	$(paster) $(combine) contractsa -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/contractsa.csv: $(workdir)/contractsa.csv
	$(fdir)/filter_contractsa.py < $< > $@

###
###  Consultations
###
.PHONY: consultations
consultations: upload-consultations rebuild-consultations

.PHONY: upload-consultations
upload-consultations: $(workdir)/filtered/consultations.csv \
		$(workdir)/filtered/consultations.csv \
		$(workdir)/filtered/current_consultations.csv \
		$(workdir)/filtered/current_consultations_open.csv
	@$(echo_date) Publishing Consultations to registry and portal...
	cp $(workdir)/consultations.csv $(registry_static)
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=897d3008-b258-4a68-8c02-3e3c099a42c8 last_modified=$(isodate) \
	> /dev/null
	cp $(workdir)/filtered/consultations.csv $(registry_static)/consultations_open.csv
	cp $(workdir)/filtered/consultations.csv $(portal_static)/consultations_open.csv
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=92bec4b7-6feb-4215-a5f7-61da342b2354 upload@"$(workdir)/filtered/consultations.csv" \
	> /dev/null
	cp $(workdir)/filtered/current_consultations.csv $(registry_static)
	cp $(workdir)/filtered/current_consultations_open.csv $(registry_static)
	cp $(workdir)/filtered/current_consultations_open.csv $(portal_static)
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=aa606d25-4387-4bc6-89eb-12d66f5e9044 last_modified=$(isodate)\
	> /dev/null

.PHONY: rebuild-consultations
rebuild-consultations:
	# no search for consultations

$(workdir)/consultations.csv:
	$(paster) $(combine) consultations -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/consultations.csv: $(workdir)/consultations.csv
	$(fdir)/filter_consultations.py < $< > $@

$(workdir)/filtered/current_consultations.csv: $(workdir)/consultations.csv
	$(fdir)/filter_current_consultations.py < $< > $@

$(workdir)/filtered/current_consultations_open.csv: \
		$(workdir)/filtered/consultations.csv
	 $(fdir)/filter_current_consultations.py < $< > $@

###
###  Departmental Audit Committee
###
.PHONY: dac
dac: upload-dac rebuild-dac

.PHONY: upload-dac
upload-dac: $(workdir)/filtered/dac.csv $(workdir)/dac.csv
	@$(echo_date) Uploading Departmental Audit Committee...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=499383b6-cd2a-466a-9fcf-910d3e427700 upload@"$(workdir)/filtered/dac.csv" \
	> /dev/null

.PHONY: rebuild-dac
rebuild-dac: $(workdir)/filtered/dac.csv $(workdir)/dac.csv
	# no search for dac

$(workdir)/dac.csv:
	$(paster) $(combine) dac -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/dac.csv: $(workdir)/dac.csv
	$(fdir)/filter_dac.py < $< > $@

###
###  Experimental Inventory
###
.PHONY: experiment
experiment: upload-experiment rebuild-experiment

.PHONY: upload-experiment
upload-experiment: $(workdir)/filtered/experiment.csv $(workdir)/experiment.csv
	@$(echo_date) Uploading Experimental Inventory...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=07151ad9-52e2-4f99-b4fd-7cd208816a64 upload@"$(workdir)/filtered/experiment.csv" \
	> /dev/null

.PHONY: rebuild-experiment
rebuild-experiment: $(workdir)/filtered/experiment.csv $(workdir)/experiment.csv
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/experiment.csv" --search experiment --quiet

$(workdir)/experiment.csv:
	$(paster) $(combine) experiment -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/experiment.csv: $(workdir)/experiment.csv
	$(fdir)/filter_experiment.py < $< > $@

###
###  Grants and Contributions
###
.PHONY: grants
grants: upload-grants rebuild-grants

.PHONY: upload-grants
upload-grants: $(workdir)/filtered/grants.csv $(workdir)/filtered/grants-nil.csv
	@$(echo_date) Uploading Grants and Contributions...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=1d15a62f-5656-49ad-8c88-f40ce689d831 upload@"$(workdir)/filtered/grants.csv" \
	> /dev/null
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=4e4db232-f5e8-43c7-b8b2-439eb7d55475 upload@"$(workdir)/filtered/grants-nil.csv" \
	> /dev/null

.PHONY: rebuild-grants
rebuild-grants: $(workdir)/filtered/grants.csv $(workdir)/filtered/grants-nil.csv
	@$(echo_date) Rebuilding Grants and Contributions...
	mkdir -p $(workdir)/amendments
	$(registry_python) $(fdir)/amendment_delta_records.py \
	"$(workdir)/filtered/grants.csv" "$(workdir)/amendments/grants.csv"
	@$(oc_search) import_data_csv --csv "$(workdir)/amendments/grants.csv" --search grants --quiet
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/grants-nil.csv" --search grants --quiet --nothing_to_report

$(workdir)/grants.csv:
	$(paster) $(combine) grants -d $(workdir) -c $(registry_ini)

$(workdir)/grants-nil.csv:
	$(paster) $(combine) grants-nil -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/grants.csv: $(workdir)/grants.csv
	$(fdir)/filter_grants.py < $< > $@

$(workdir)/filtered/grants-nil.csv: $(workdir)/grants-nil.csv
	$(fdir)/filter_grants.py < $< > $@

###
###  Hospitality Expenses
###
.PHONY: hospitalityq
hospitalityq: upload-hospitalityq rebuild-hospitalityq

.PHONY: upload-hospitalityq
upload-hospitalityq: $(workdir)/filtered/hospitalityq.csv $(workdir)/filtered/hospitalityq-nil.csv
	@$(echo_date) Uploading Hospitality Expenses..
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=7b301f1a-2a7a-48bd-9ea9-e0ac4a5313ed upload@"$(workdir)/filtered/hospitalityq.csv" \
	> /dev/null
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=36a3b6cc-4f45-4081-8dbd-2340ca487041 upload@"$(workdir)/filtered/hospitalityq-nil.csv" \
	> /dev/null

.PHONY: rebuild-hospitalityq
rebuild-hospitalityq: $(workdir)/filtered/hospitalityq.csv $(workdir)/filtered/hospitalityq-nil.csv
	@$(echo_date) Rebuilding Hospitality Expenses...
	$(paster) --plugin=ckanext-canada hospitalityq rebuild --lenient -c $(portal_ini) \
	-f "$(workdir)/filtered/hospitalityq.csv" "$(workdir)/filtered/hospitalityq-nil.csv"

$(workdir)/hospitalityq.csv:
	$(paster) $(combine) hospitalityq -d $(workdir) -c $(registry_ini)

$(workdir)/hospitalityq-nil.csv:
	$(paster) $(combine) hospitalityq-nil -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/hospitalityq.csv: $(workdir)/hospitalityq.csv
	$(fdir)/filter_modified_created.py < $< > $@

$(workdir)/filtered/hospitalityq-nil.csv: $(workdir)/hospitalityq-nil.csv
	$(fdir)/filter_modified_created.py < $< > $@

###
###  Travel Expenses
###
.PHONY: travelq
travelq: upload-travelq rebuild-travelq

.PHONY: upload-travelq
upload-travelq: $(workdir)/filtered/travelq.csv $(workdir)/filtered/travelq-nil.csv
	@$(echo_date) Uploading Travel Expenses..
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=8282db2a-878f-475c-af10-ad56aa8fa72c upload@"$(workdir)/filtered/travelq.csv" \
	> /dev/null
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=d3f883ce-4133-48da-bc76-c6b063d257a2 upload@"$(workdir)/filtered/travelq-nil.csv" \
	> /dev/null

.PHONY: rebuild-travelq
rebuild-travelq: $(workdir)/filtered/travelq.csv $(workdir)/filtered/travelq-nil.csv
	@$(echo_date) Rebuilding Travel Expenses...
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/travelq.csv" --search travelq --quiet
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/travelq-nil.csv" --search travelq --nothing_to_report

$(workdir)/travelq.csv:
	$(paster) $(combine) travelq -d $(workdir) -c $(registry_ini)

$(workdir)/travelq-nil.csv:
	$(paster) $(combine) travelq-nil -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/travelq.csv: $(workdir)/travelq.csv
	$(fdir)/filter_modified_created.py < $< > $@

$(workdir)/filtered/travelq-nil.csv: $(workdir)/travelq-nil.csv
	$(fdir)/filter_modified_created.py < $< > $@

###
###  National Action Plan 5
###
.PHONY: nap5
nap5: upload-nap5 rebuild-nap5

.PHONY: upload-nap5
upload-nap5: $(workdir)/filtered/nap5.csv $(workdir)/nap5.csv
	@echo Uploading 5th NAP...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=0305a157-9d10-4ec2-8ca4-e39ab2b34396 upload@"$(workdir)/filtered/nap5.csv" \
	> /dev/null

.PHONY: rebuild-nap5
rebuild-nap5: $(workdir)/filtered/nap5.csv $(workdir)/nap5.csv
	@$(oc_search) nap5_preprocess_csv --csv "$(workdir)/filtered/nap5.csv" --out "$(workdir)/filtered/nap5_search.csv"
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/nap5_search.csv" --search nap5

$(workdir)/nap5.csv:
	$(paster) $(combine) nap5 -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/nap5.csv: $(workdir)/nap5.csv
	$(fdir)/filter_nap5.py < $< > $@

###
###  Open Data Inventory
###
.PHONY: inventory
inventory: upload-inventory rebuild-inventory

.PHONY: upload-inventory
upload-inventory: $(workdir)/filtered/inventory.csv
	@$(echo_date) Uploading Open Data Inventory...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=d0df95a8-31a9-46c9-853b-6952819ec7b4 upload@"$(workdir)/filtered/inventory.csv" \
	> /dev/null

.PHONY: rebuild-inventory
rebuild-inventory: $(workdir)/filtered/inventory.csv
	@$(echo_date) Rebuilding Open Data Inventory...
	$(paster) --plugin=ckanext-canada inventory rebuild --lenient -c $(portal_ini) \
	-f "$(workdir)/filtered/inventory.csv"

$(workdir)/inventory.csv:
	$(paster) $(combine) inventory -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/inventory.csv: $(workdir)/inventory.csv
	$(fdir)/filter_inventory.py < $< > $@

###
###  Position Reclassification
###
.PHONY: reclassification
reclassification: upload-reclassification rebuild-reclassification

.PHONY: upload-reclassification
upload-reclassification: $(workdir)/filtered/reclassification.csv $(workdir)/filtered/reclassification-nil.csv
	@$(echo_date) Uploading Position Reclassification...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=bdaa5515-3782-4e5c-9d44-c25e032addb7 upload@"$(workdir)/filtered/reclassification.csv" \
	> /dev/null
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=1e955e4d-df35-4441-bf38-b7086192ece2 upload@"$(workdir)/filtered/reclassification-nil.csv" \
	> /dev/null

.PHONY: rebuild-reclassification
rebuild-reclassification: $(workdir)/filtered/reclassification.csv $(workdir)/filtered/reclassification-nil.csv
	@$(echo_date) Rebuilding Position Reclassification...
	$(paster) --plugin=ckanext-canada reclassification rebuild --lenient -c $(portal_ini) \
	-f "$(workdir)/filtered/reclassification.csv" "$(workdir)/filtered/reclassification-nil.csv"

$(workdir)/reclassification.csv:
	$(paster) $(combine) reclassification -d $(workdir) -c $(registry_ini)

$(workdir)/reclassification-nil.csv:
	$(paster) $(combine) reclassification-nil -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/reclassification.csv: $(workdir)/reclassification.csv
	$(fdir)/filter_reclassification.py < $< > $@

$(workdir)/filtered/reclassification-nil.csv: $(workdir)/reclassification-nil.csv
	$(fdir)/filter_reclassification.py < $< > $@

###
###  Service Inventory
###
.PHONY: service
service: upload-service rebuild-service

.PHONY: upload-service
upload-service: $(workdir)/filtered/service.csv $(workdir)/filtered/service-std.csv
	# disable publishing service inventory as of 2020-06-08
	# @$(echo_date) Uploading Service Inventory...
	# @$(ckanapi) action resource_patch -c $(registry_ini) \
	# id=3acf79c0-a5f5-4d9a-a30d-fb5ceba4b60a upload@"$(workdir)/filtered/service.csv" \
	# > /dev/null
	# @$(ckanapi) action resource_patch -c $(registry_ini) \
	# id=272143a7-533e-42a1-b72d-622116474a21 upload@"$(workdir)/filtered/service-std.csv" \
	# > /dev/null

.PHONY: rebuild-service
rebuild-service: $(workdir)/filtered/service.csv $(workdir)/filtered/service-std.csv
	# disabled search rebuild like in update_search_cores.sh
	# $(ogc_search)/load_si_to_solr.py "$(workdir)/filtered/service.csv" "$(workdir)/filtered/service-std.csv"

$(workdir)/service.csv:
	$(paster) $(combine) service -d $(workdir) -c $(registry_ini)

$(workdir)/service-std.csv:
	$(paster) $(combine) service-std -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/service.csv: $(workdir)/service.csv
	$(fdir)/filter_service.py < $< > $@

$(workdir)/filtered/service-std.csv: $(workdir)/service-std.csv
	$(fdir)/filter_service_std.py < $< > $@

###
###  Annual Travel, Hospitality and Conferences
###
.PHONY: travela
travela: upload-travela rebuild-travela

.PHONY: upload-travela
upload-travela: $(workdir)/filtered/travela.csv
	@$(echo_date) Uploading Annual Travel, Hospitality and Conferences...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=a811cac0-2a2a-4440-8a81-2994fc753171 upload@"$(workdir)/filtered/travela.csv" \
	> /dev/null

.PHONY: rebuild-travela
rebuild-travela: $(workdir)/filtered/travela.csv
	@$(echo_date) Rebuilding Annual Travel, Hospitality and Conferences...
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/travela.csv" --search travela

$(workdir)/travela.csv:
	$(paster) $(combine) travela -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/travela.csv: $(workdir)/travela.csv
	$(fdir)/filter_travela.py < $< > $@

###
###  Acts of Founded Wrongdoing
###
.PHONY: wrongdoing
wrongdoing: upload-wrongdoing rebuild-wrongdoing

.PHONY: upload-wrongdoing
upload-wrongdoing: $(workdir)/filtered/wrongdoing.csv
	@$(echo_date) Uploading Acts of Founded Wrongdoing...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=84a77a58-6bce-4bfb-ad67-bbe452523b14 upload@"$(workdir)/filtered/wrongdoing.csv" \
	> /dev/null

.PHONY: rebuild-wrongdoing
rebuild-wrongdoing: $(workdir)/filtered/wrongdoing.csv
	@$(echo_date) Rebuilding Acts of Founded Wrongdoing...
	$(paster) --plugin=ckanext-canada wrongdoing rebuild --lenient -c $(portal_ini) \
	-f "$(workdir)/filtered/wrongdoing.csv"

$(workdir)/wrongdoing.csv:
	$(paster) $(combine) wrongdoing -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/wrongdoing.csv: $(workdir)/wrongdoing.csv
	$(fdir)/filter_wrongdoing.py < $< > $@



###
###  Government Administrative Aircraft Use
###
.PHONY: adminaircraft
adminaircraft: upload-adminaircraft rebuild-adminaircraft

.PHONY: upload-adminaircraft
upload-adminaircraft: $(workdir)/filtered/adminaircraft.csv $(workdir)/adminaircraft.csv
	@$(echo_date) Uploading Administrative Aircraft...
	@$(ckanapi) action resource_patch -c $(registry_ini) \
	id=1495406e-338c-43ec-9995-ec8d8c90d17e upload@"$(workdir)/filtered/adminaircraft.csv" \
	> /dev/null

.PHONY: rebuild-adminaircraft
rebuild-adminaircraft: $(workdir)/filtered/adminaircraft.csv
	@$(oc_search) import_data_csv --csv "$(workdir)/filtered/adminaircraft.csv" --search adminaircraft

$(workdir)/adminaircraft.csv:
	$(paster) $(combine) adminaircraft -d $(workdir) -c $(registry_ini)

$(workdir)/filtered/adminaircraft.csv: $(workdir)/adminaircraft.csv
	$(fdir)/filter_adminaircraft.py < $< > $@


endif
