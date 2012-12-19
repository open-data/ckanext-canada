TARGET = ../ckanext/canada/metadata_schema/schema.json

all:
	./convert_schema.py > ${TARGET}

update-proposed:
	# NOTE: This only works inside the gc.ca network
	wget http://www.gcpedia.gc.ca/gcwiki/images/1/13/OpenGov_Proposed_Metadata_Scheme.xls -O proposed/proposed_schema.xls

.PHONY: all update-proposed
