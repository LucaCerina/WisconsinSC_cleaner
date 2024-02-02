# Known Issues

## Gamma
* Some respiratory events annotated the negative drop in SpO2 and not the absolute value of the minimum SpO2. Example in visit2-21949
* Some events do not have a duration. Defaulting to 3 seconds. Example arousal - plm in visit2-39972
* Some desaturations may have an invalid value for a reasonable drop. Example drop of 1.6 in visit2-55274