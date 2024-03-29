# WisconsinSC_cleaner
A tool to clean and uniform annotation files from Wisconsin Sleep Cohort (WSC), distributed by NSRR [here](https://sleepdata.org/datasets/wsc).

## Motivation
The Wisconsin Sleep Cohort is a great resource for studing longitudinal history of sleep disorders in a large population.

However, this long time span comes at the price of some issues and inconsistencies in the annotation of events, making the life of researchers more difficult than necessary.
The WSC dataset uses also two different annotation formats (Twin and Gamma) that are slightly incompatible between each other.
For example, obstructive apneas may be formatted as: 'Obs Apnea', 'OBS Apnea', ' Obs Apnea ', 'Obst Apnea', 'OA', 'Apnea', 'Obst. Apnea'
Other issues relates to missing information in the annotations' columns, inconsistent time formats (most are 24h, some am/pm) and other dirty bits that are not necessary and complicate automatic parsing.

## How to use this script
Clone the repo or download the `wsc_clean.py` and `mappings.txt` file and run it from command line as:

`python wsc_clean.py <your_dataset_polysomnography_folder>`

The package can be also installed from PyPI:

`pip install wisconsinsc_cleaner`

and executed as:

`wsc_clean <your_dataset_polysomnography_folder>`

## Content of this repo
A single python script (no installation needed) parses all the annotation files and produce another set of annotation files with the suffix `.uniform.txt`.
The mapping of annotations is available in the `mappings.txt` file in the form `A|B|C` (see [https://zzz.bwh.harvard.edu/luna/ref/annotations/#remap] for details), meaning that every instance of `B` or `C` will be mapped as `A`. If a mapping does not exist, the original value is returned with a prefix `misc:`.

An extra text file includes all lines that were not mapped.

If a recording uses the Twin format (allscore.txt files) the output is kept as one file.
If it uses the Gamma format (log.txt files) sleep stages and event scoring are merged together with the log.

The code does not remove any existing annotation nor modify original files. However, some redundant information is ignored in Gamma logs (See [Known Issues](./KNOWN_ISSUES.md) file.)

The script is entirely built on Python standard library and tested on Python v3.8. 
The script is not optimized for efficiency and it parse recordings sequentially. Parsing 2570 recordings takes less than 10 minutes.

## Format of the output
The `.uniform.txt` file will have a columnar format (comma separated values) with a header:

| Timestamp   | EventKey | Duration | Param1    | Param2    | Param3    |
|-------------|----------|----------|-----------|-----------|-----------|
| hh:mm:ss.ms | String   | seconds  | see below | see below | see below |

The Duration and Param[1-3] depend on the type of events

### Sleep stages, position and miscellanea
They don't need extra information other than the event itself. Duration set to -1, Params to 0.
The duration is defined by the next event of the same type
### Sensor gain in Gamma files
gain:sensor_affected, -1, new gain value, channel affected, 0
### Respiratory events
event_key, Duration of the event in seconds, SpO2 minimum of the event [%], 0, 0
### Oxygen desaturations
event_key, Duration of the event in seconds, SpO2 minimum of the event [%], SpO2 drop [%], 0
### Leg movements, arousals, ekg events, snore and any other without additional parameters
event_key, Duration of the event in seconds, 0, 0, 0

## Known issues
See [Known Issues](./KNOWN_ISSUES.md) file.

## Contributing
Please let us know if you encountered issues or bugs through github issues tracker.

If you feel generous and this library helped your project:

[![Buy me a coffee][buymeacoffee-shield]][buymeacoffee]

[buymeacoffee]: https://www.buymeacoffee.com/u2Vb3kO
[buymeacoffee-shield]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
