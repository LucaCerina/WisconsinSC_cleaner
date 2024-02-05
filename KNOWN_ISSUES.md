# Known Issues

## Twin
* Some log lines start with a `--/--/--` and require extra parsing steps. Example in visit1-10226.
* Some log lines have a epoch but not the timestamp, so the real event may be misplaced in a -/+ 15s range.

## Gamma
* Some respiratory events annotated the negative drop in SpO2 and not the absolute value of the minimum SpO2. Example in visit2-21949
* Some events do not have a duration. Defaulting to 3 seconds. Example arousal - plm in visit2-39972
* Some desaturations may have an invalid value for a reasonable drop. Example drop of 1.6 in visit2-55274
* Some EKG events such as tachycardia have a duration below 1s/1beat(?). To be checked if it's the correct duration or a spurious value in annotations.
* Gama contains many lines like "SaO2 from X to Y", but it is unclear if they should be mapped as desaturations or else.

# Design choices

## Twin
Some fields are ignored when parsing the files:
* Epoch#
* Scan # x2
* Length
* Extra columns in log file

Arousals are set to a fixed duration of 3 seconds as from WSC annotation FAQ file available from NSRR.