# Harvesting data from Open.alberta.ca

The Province of Alberta operates a CKAN-based [open data portal](https://open.alberta.ca/opendata). As part of an agreement with the Province of Alberta, their meta-data catalogue's entries have been added to the Government of Canada's open data catalog. 

The following scripts were used to perform the meta data harvest.
1.	A script is run to import the data from  Alberta to a local file: [ab.sh](https://github.com/open-data/ckanext-canada/blob/master/bin/harvest/ab.sh)
2.	English strings are then extracted from the harvested data to another file: [ab_strings.py](https://github.com/open-data/ckanext-canada/blob/master/bin/harvest/ab_strings.py)
3.	Translation is then done using a separate script that uses the DeepL API to translate and write the translated text to a CSV file:  [deepl.py](https://github.com/open-data/ckanext-canada/blob/master/bin/harvest/deepl.py)
4.	A final script merges the translated text with the harvested data and does the necessary transformations to create an Open Data bulk upload JSON lines file: [ab_transform.py](https://github.com/open-data/ckanext-canada/blob/master/bin/harvest/ab_transform.py)

_Note:_ Because it is machine translated, and may not have been reviewed by a human translator, it's important to set a different language code for text that was translated by an AI program. 

 - `en-t-fr`: English text machine translated from French
 - `fr-t-en`: French text machine translated from English 
