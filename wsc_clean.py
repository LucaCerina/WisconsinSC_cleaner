# -*- coding: utf-8 -*-
import re
import sys
from csv import DictWriter
from datetime import datetime, timedelta
from glob import glob
from itertools import zip_longest
from time import perf_counter
from typing import Tuple, Union

from pathlib2 import Path

__version__ = "0.0.1"
__author__      = "Luca Cerina"
__copyright__   = "Copyright 2024, Luca Cerina"
__email__       = "lccerina@duck.com"

OUTPUT_HEADER = ["Timestamp","EventKey","Duration","Param1","Param2","Param3"]
map_event = lambda x,m: m.get(x, f"misc:{x}")

def datetime_sorter(start_time:datetime, input_time:datetime) -> int:
    """Return distance from start of recording in seconds to sort output list in Twin parsing.

    Args:
        start_time (datetime): Start time of the recording from Twin log file
        input_time (datetime): Input time to be aligned

    Returns:
        int: Total seconds between start time and input
    """
    delta = input_time - start_time
    while delta.days < 0:
        delta += timedelta(days=1)
    return delta.total_seconds()

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
        
def process_gamma_log(recording:str, input_filename:str, output_filename:str, mapping:dict) -> Tuple[bool, set]:
    """Parse lines from Gamma/allscore files. This function receives the filename ending as 'allscore.txt'

    Args:
        recording (str): id of the recording
        input_filename (str): Input log file e.g wsc-visit1-100000-nsrr.allscore.txt
        output_filename (str): Output '.uniform.txt' log file
        mapping (dict): Dictionary to map event keys. See mappings.txt

    Returns:
        bool: True if parsing concluded with no errors
        set: Set of values that were not mapped (misc: prefix)
    """
    no_error = True
    unmapped = set()

    assert input_filename.endswith('allscore.txt'), f"Error in Gamma parser. Expected an allscore log file, got {input_filename}"
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
            
            # Log non mapped / misc lines
            if output_line['EventKey'].startswith('misc'):
                unmapped.add(f"{recording} - {output_line['Timestamp']} - {output_line['EventKey']}")
            writer.writerow(output_line)

    return no_error, unmapped

def parse_timestamp_twin(timestamp_str:str, start_time:datetime=None) -> Union[datetime,None]:
    """Parse timestamps in Twin logs using the hh:mm:ss string or the epoch if start time is available.

    Args:
        timestamp_str (str): String in the first (if correctly formatted) column of the log file.
        start_time (datetime, optional): Start time of the recording from the first line of the log file. Defaults to None.

    Returns:
        datetime: parsed datetime
        None: error in parsing
    """
    timestamp_split = re.sub("\s+", " ", timestamp_str).split()
    if len(timestamp_split)<=2 and re.match(r"\d{2}:\d{2}:\d{2}", timestamp_split[0]):
        return datetime.strptime(timestamp_split[0], "%H:%M:%S")
    elif len(timestamp_split)<=2 and start_time is not None:
        if re.match(r"\d+", timestamp_split[0]):
            return start_time+timedelta(seconds=(int(timestamp_split[0])-1)*30)
        elif len(timestamp_split)==2 and re.match(r"\d+", timestamp_split[1]):
            return start_time+timedelta(seconds=(int(timestamp_split[1])-1)*30)
        else:
            return None
    else:
        print(timestamp_split)
        return None

def process_twin_log(recording:str, input_filename:str, output_filename:str, mapping:dict) -> Tuple[bool, set]:
    """Parse lines from Twin/(log,sco,stg) files. This function receives only the recording id and then apply the specific suffixes

    Args:
        recording (str): id of the recording
        input_filename (str): Input log file e.g wsc-visit1-100000-nsrr
        output_filename (str): Output '.uniform.txt' log file
        mapping (dict): Dictionary to map event keys. See mappings.txt

    Returns:
        bool: True if parsing concluded with no errors
        set: Set of values that were not mapped (misc: prefix)
    """
    no_error = True
    unmapped = set()

    assert input_filename.endswith("-nsrr"), f"Error in Twin parser. Expected input filename to indicate recording id, not specific files. Got {input_filename}"

    # Output is stored in a list of tuples (timestamp, values) so it can be ordered before writing the output file
    temp_output = []
    start_time = datetime.fromtimestamp(0)

    # Start by parsing the log file
    log_filename = f"{input_filename}.log.txt"
    with open(log_filename, "r") as log_file:
        for i, log_line in enumerate(log_file):
            log_line = log_line.lower().strip('\t \n')
            log_line_split = log_line.split('\t')
            if len(log_line)<=1 or len(log_line_split)<=2:
                continue

            # Some lines do not start correctly
            if log_line_split[0].startswith('--/'):
                log_line_split = log_line_split[1:]
            
            # Parse timestamp
            timestamp = parse_timestamp_twin(log_line_split[0], start_time)
            if timestamp is None:
                print(f"Parsing error Twin in line: {log_line}")
                continue

            # First line checks
            if i == 0:
                if timestamp.hour>12: # Most of the timestamps are on 24h, some have am/pm timestamps
                    timestamp_correction = timedelta(hours=0)
                else:
                    timestamp_correction = timedelta(hours=12)
                start_time = timestamp+timestamp_correction

            # Create output line
            output_line = {k:v for (k,v) in zip(OUTPUT_HEADER, ['00:00:00.00', 'error', -1, 0, 0, 0])}

            # Parse line
            timestamp = timestamp + timestamp_correction
            output_line['Timestamp'] = timestamp.strftime("%H:%M:%S.00")
            event_key = log_line_split[1].strip("\t ")
            # Skip empty lines
            if len(event_key)==0:
                continue
            output_line['EventKey'] = map_event(event_key, mapping)
            
            # Log non mapped / misc lines
            if output_line['EventKey'].startswith('misc'):
                unmapped.add(f"{recording} - {timestamp} - {output_line['EventKey']}")

            # Append results
            temp_output.append((timestamp, output_line))


    # Sort and write output
    temp_output.sort(key=lambda x:datetime_sorter(start_time, x[0]))
    with open(output_filename, 'w', encoding='utf-8') as output_file:
        # Write output header
        writer = DictWriter(output_file, fieldnames=OUTPUT_HEADER, lineterminator='\n')
        writer.writeheader()
        # Write lines
        for _,output_line in temp_output:
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
    eta = None
    total_time = 0
    for i, recording in enumerate(recordings, start=1):
        eta_str = f"ETA : {eta}" if eta is not None else ""
        print(f"Processing {recording} : {i}|{n_recordings}. {eta_str}")

        # Log time start
        t_start = perf_counter()

        # Filenames
        recording_path = f"{folder}/{recording}"
        allscore_filename = f"{recording_path}.allscore.txt"
        output_filename = f"{folder}/{recording}.uniform.txt"

        # Detect type of log
        has_allscore = Path(allscore_filename).exists()

        # Parse file
        if not has_allscore:
            no_error = True
            # raise NotImplementedError
            no_error, unmapped  = process_twin_log(recording, recording_path, output_filename, mapping)
            non_mapped_lines.update(unmapped)
        else:
            no_error = True
            # TODO passthrough while working on twin files
            # no_error, unmapped  = process_gamma_log(recording, allscore_filename, output_filename, mapping)
            # non_mapped_lines.update(unmapped)
        if no_error == False:
            print(f"Error in parsing recording {recording}. Exiting.")
            sys.exit(1)

        # Log time end and update ETA
        t_end = perf_counter()
        total_time += (t_end-t_start)
        eta = timedelta(seconds=(n_recordings-i)*(total_time/(i+1)))

    print(f"Parsing of {n_recordings} recordings completed in {timedelta(seconds=total_time)}.")
    
    # Store unmapped lines
    non_mapped_filename = 'WSC_non_mapped_lines.txt'
    non_mapped_lines = sorted(list(non_mapped_lines), key=lambda x:x.split(' - ')[-1])
    print(f"Non mapped lines that may need further checks: {len(non_mapped_lines)}. See {non_mapped_filename}")
    with open(f'./{non_mapped_filename}', 'w', encoding='utf-8') as nfile:
        for line in non_mapped_lines:
            nfile.write(line+'\n')
        