# -*- coding: utf-8 -*-
import re
import sys
from csv import DictWriter
from glob import glob
from itertools import zip_longest
from typing import Tuple, Union

from pathlib2 import Path

__version__ = "0.0.1"
__author__      = "Luca Cerina"
__copyright__   = "Copyright 2024, Luca Cerina"
__email__       = "lccerina@duck.com"

OUTPUT_HEADER = ["Timestamp","EventKey","Duration","Param1","Param2","Param3"]
map_event = lambda x,m: m.get(x, f"misc:{x}")

def load_mappings(mapping_file:str) -> dict:
    """Convert maps in mappings.txt file to a dictionary to be used later.
    Raise ValueError in case of badly formatted map
    """
    with open(mapping_file) as map_file:
        maps = map_file.read().splitlines()
    
    output = {}
    for map_line in maps:
        # Ignore comment lines
        if map_line.startswith('#') or len(map_line)==0:
            continue
        # Check spurious | characters
        map_line = re.sub(r"(\|)\1+", r"\1", map_line)

        # Split source and destination map
        map_split = map_line.split('|')
        if len(map_split)<2:
            raise ValueError(f"Found badly formatted map: '{map_line}'. Please fix")
        destination_value = map_split[0]
        source_values = [map_split[1]] if len(map_split)==2 else map_split[1:]
        # Assign it to output
        output.update({k.lower():v.lower() for (k,v) in zip_longest(source_values,[destination_value], fillvalue=destination_value)})
    return output

def parse_event_gamma(event_string:str, mapping:dict) -> Union[dict, None]:
    """Parse events with duration and extra parameters from Gamma/allscore log files.
       Return None in case of errors

    Args:
        event_string (str): String description of the event
        mapping (dict): Dictionary to map event keys. See mappings.txt

    Returns:
        dict: Mapped event with duration and params. None in case of errors
    """
    output = {}
    # Select matcher
    if event_string.startswith('respiratory event'):
        regex = r"(?P<event_key>[\w]+\s[\w]+) - dur: (?P<Duration>[\d]+.[\d]) sec. - (?P<event_type>[\w]+\s?[\w]*) - desat (?P<Param1>[-]?[\d]+.[\d]|<n/a>)\s?[%]?"
    elif event_string.startswith('desat'):
        regex = r"(?P<event_key>[\w]+) - dur: (?P<Duration>[\d]+.[\d]) sec. - min (?P<Param1>[\d]+.[\d]) % - drop (?P<Param2>[-]?[\d]+.[\d]) %"
    elif any(event_string.startswith(x) for x in ['arousal', 'lm', 'ekg', 'snore']):
        regex = r"(?P<event_key>([\w]+|[\w]+\s[\w]+))( - dur: (?P<Duration>[\d]+.[\d]) sec. |\s)- (?P<event_type>[\w]+\s?[\w]*)"
    else:
        return None

    # Parse string
    match = re.match(regex,event_string)
    if match:
        try:
            # Fill results
            match_dict = match.groupdict()
            # if match_dict['event_key']=='arousal':
            #     print(event_string)
            #     print(match_dict)
            output['EventKey'] = map_event(f"{match_dict['event_key']} {match_dict.get('event_type','')}".strip(), mapping)
            output['Duration'] = match_dict.get('Duration', 3.0) # Default for some events in Gamma recordings (e.g. arousals)
            for i in range(1, 4):
                output[f'Param{i}'] = match_dict.get(f'Param{i}', 0)
        except Exception:
            return None
        return output
    else:
        return None
        


def process_gamma_log(input_filename:str, output_filename:str, mapping:dict) -> Tuple[bool, set]:
    """Parse lines from Gamma/allscore files.

    Args:
        input_filename (str): Input log file
        output_filename (str): Output '.uniform.txt' log file
        mapping (dict): Dictionary to map event keys. See mappings.txt

    Returns:
        bool: True if parsing concluded with no errors
        set: Set of values that were not mapped (misc: prefix)
    """
    no_error = True
    unmapped = set()

    with open(input_filename, 'r', encoding='utf-8', errors='ignore') as input_file, open(output_filename, 'w', encoding='utf-8') as output_file:
        # Write output header
        writer = DictWriter(output_file, fieldnames=OUTPUT_HEADER, lineterminator='\n')
        writer.writeheader()
        # Parse lines
        for input_line in input_file:
            # Lowercase
            input_line = input_line.lower()
            # Split columns
            input_line_split = input_line.strip('\n \t').split('\t')
            if len(input_line_split)<=1:
                continue
            
            # Create output line
            output_line = {k:v for (k,v) in zip(OUTPUT_HEADER, ['00:00:00.00', 'error', -1, 0, 0, 0])}

            # Timestamp
            timestamp = input_line_split[0]
            output_line['Timestamp'] = timestamp

            # Primary event key
            event_string_split = input_line_split[1].split(' -')
            event_key = event_string_split[0]
            # Parse events with or without durations
            if event_key in ['arousal', 'respiratory event', 'desaturation', 'lm', 'ekg events', 'snore'] and len(event_string_split)>1:
                parsed_line = parse_event_gamma(input_line_split[1], mapping)
                if parsed_line is None:
                    print(f"Parsing error Gamma in line: {input_line_split[1]}")
                    no_error = False
                    continue
                output_line.update(parsed_line)
            else:
                output_line['EventKey'] = map_event(input_line_split[1], mapping)
            if output_line['EventKey'].startswith('misc'):
                unmapped.add(output_line['EventKey'])
            writer.writerow(output_line)

    return no_error, unmapped

if __name__ == "__main__":
    # Get data folder
    if len(sys.argv)<2:
        print("Error! Usage wsc_clean.py <wsc_polysomnography_folder>")
        sys.exit(1)
    folder = sys.argv[1]
    if not Path(folder).exists():
        print(f"Error! Folder '{folder}' not available or not found")
        sys.exit(1)

    # Load annotations mappings
    print("Loading mappings")
    mapping = load_mappings('./mappings.txt')

    # Get all recordings
    print("Identifying recordings")
    log_exists = lambda x: Path(f"{folder}/{x}.log.txt").exists() or Path(f"{folder}/{x}.allscore.txt").exists()
    recordings = [Path(recording).stem for recording in glob(f"{folder}*.edf") if log_exists(Path(recording).stem)]
    n_recordings = len(recordings)
    print(f"Starting the cleaning of {n_recordings} recordings")

    # Keep track of non mapped lines
    non_mapped_lines = set()

    # Process recordings
    # recordings = ['wsc-visit2-31738-nsrr']
    for i, recording in enumerate(recordings, start=1):
        print(f"Processing {recording} : {i}|{n_recordings}")
        # Output file
        output_filename = f"{folder}/{recording}.uniform.txt"

        # Detect type of log
        allscore_filename = f"{folder}/{recording}.allscore.txt"
        has_allscore = Path(allscore_filename).exists()

        # Parse file
        if not has_allscore:
            no_error = True
            raise NotImplementedError
        else:
            no_error, unmapped  = process_gamma_log(allscore_filename, output_filename, mapping)
            non_mapped_lines.update(unmapped)
        if no_error == False:
            print(f"Error in parsing recording {recording}. Exiting.")
            sys.exit(1)
    
    print(f"Non mapped lines that may need further checks: {len(non_mapped_lines)}")
    with open('./WSC_non_mapped_lines.txt', 'w', encoding='utf-8') as nfile:
        for line in non_mapped_lines:
            print(line)
            nfile.write(line+'\n')
        