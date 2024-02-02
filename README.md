# WisconsinSC_cleaner
A tool to clean and uniform annotation files from Wisconsin Sleep Cohort (WSC), distributed by NSRR [here](https://sleepdata.org/datasets/wsc).

## Motivation
The Wisconsin Sleep Cohort is a great resource for studing longitudinal history of sleep disorders in a large population.

However, this long time span comes at the price of some issues and inconsistencies in the annotation of events, making the life of researchers more difficult than necessary.
The WSC dataset uses also two different annotation formats (Twin and Gamma) that are slightly incompatible between each other.
For example, obstructive apneas may be formatted as: 'Obs Apnea', 'OBS Apnea', ' Obs Apnea ', 'Obst Apnea', 'OA', 'Apnea', 'Obst. Apnea'
Other issues relates to missing information in the annotations' columns, inconsistent time formats (most are 24h, some am/pm) and other dirty bits that are not necessary and complicate automatic parsing.

## Content of this repo
A single python script parse all the annotation files and produce another set of annotation files with the suffix `_uniform.txt`.
The mapping of annotations is available in the mappings.txt file in the form `A|B|C` (see [https://zzz.bwh.harvard.edu/luna/ref/annotations/#remap] for details), meaning that every instance of `B` or `C` will be mapped as `A`. If a mapping does not exist, the original value is returned.

The code does not remove any existing annotation.

The script is entirely built on Python standard library and tested on Python v3.8.

## How to use this script
`python wsc_clean <your_dataset_folder>`

## Contributing
Please let us know if you encountered issues or bugs through github issues tracker.

If you feel generous and this library helped your project:

[![Buy me a coffee][buymeacoffee-shield]][buymeacoffee]

[buymeacoffee]: https://www.buymeacoffee.com/u2Vb3kO
[buymeacoffee-shield]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
