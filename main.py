#!/bin/usr/env python3
import math
import re
from sys import stdout
from datetime import datetime
import time
from requests import get
from yaml import load, dump, FullLoader
from typing import Tuple
from logging import Formatter, getLogger, DEBUG, INFO, StreamHandler


def set_up_logging(debug=False):
    logger = getLogger(__name__)
    logger.setLevel(DEBUG if debug else INFO)
    formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineni)d - %(message)s") if debug \
        else Formatter("%(asctime)s - %(message)s", datefmt='%X')
    console_handler = StreamHandler(stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def load_local_calendar_file(file: str) -> Tuple[str, list[str]]:
    with open(file, 'r') as calendar_file:
        cal = calendar_file.read()
    header = re.match(r'[\s\S.]*?BEGIN:VEVENT', cal)[0].replace('BEGIN:VEVENT', '')
    events = re.findall(r'BEGIN:VEVENT[\s\S.]*?END:VEVENT\n', cal)
    return header, events


def load_remote_calendar_file(id: int) -> Tuple[str, list[str]]:
    cal = get(f"http://planwe.pollub.pl/plan.php?type=0&id={id}&cvsfile=true&wd=10", allow_redirects=True).content
    header = re.match(r'[\s\S.]*?BEGIN:VEVENT', cal.decode('utf-8'))[0].replace('BEGIN:VEVENT', '')
    events = re.findall(r'BEGIN:VEVENT[\s\S.]*?END:VEVENT\n', cal.decode('utf-8'))
    return header, events


# Some StackOverflow code
def datetime_from_utc_to_local(utc_datetime: datetime) -> datetime:
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    return utc_datetime + offset


# More code I ""borrowed"" from Stack
def from_roman(num: str) -> int:
    roman_numerals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    for i, c in enumerate(num):
        if (i + 1) == len(num) or roman_numerals[c] >= roman_numerals[num[i + 1]]:
            result += roman_numerals[c]
        else:
            result -= roman_numerals[c]
    return result


def assemble_calendar_file(header: str, events: list[str], outfile: str) -> bool:
    with open(outfile, 'w') as outfile_fo:
        outfile_fo.write(header + ''.join(events) + 'END:VCALENDAR')
    return True


def wishes(event: str, settings: dict) -> str:
    # Minus 1hrs, minus 2hrs
    for wish in settings['time_wishes']:
        if re.match(rf'[\s\S.]*?{wish[0]}[\s\S.]*?', event):
            # Starting hours (tz are weird, that's why this code looks the way it does)
            event = event.replace(str(int(wish[1]) - 10000).zfill(6), str(int(wish[3]) - 10000).zfill(6)) \
                .replace(str(int(wish[1]) - 20000).zfill(6), str(int(wish[3]) - 20000).zfill(6))
            # Ending hours
            event = event.replace(str(int(wish[2]) - 10000).zfill(6), str(int(wish[4]) - 10000).zfill(6)) \
                .replace(str(int(wish[2]) - 20000).zfill(6), str(int(wish[4]) - 20000).zfill(6))
            log.info(f'Replaced start and end date as requested for {wish[0]}')
    return event


if __name__ == "__main__":
    log = set_up_logging()
    try:
        with open('settings.yml') as f:
            settings = load(f, Loader=FullLoader)
    except FileNotFoundError:
        with open('settings.yml', 'w') as f:
            dump({
                'group_id': "00000",
                'time_to_go': {'pentagon': 0,
                               'weii': 0,
                               'centech': 0,
                               'oxford': 0,
                               'rdzewiak': 0,
                               'mechaniczny': 0,
                               'random': 0},
                'time_wishes': [['name', 'original_start', 'original_end', 'new_start', 'new_end']]
            }, f, sort_keys=False)
        raise SystemExit("See and edit newly created settings.yml")

    log.info(f"Downloading timetable for id {settings['group_id']} and passing it for cleanup and fixes")
    header, events = load_remote_calendar_file(settings['group_id'])
    week_name = None
    fixed = []
    for index, event in enumerate(events):
        log.debug(event)
        # Find if event is a one_occurence_event occurrence
        one_occurence_event = re.match(r'[\s\S.]*?SUMMARY:.*?- (\d\d\.\d\d)', event)
        if one_occurence_event:
            reported_start = re.match(r'[\s\S.]*?DTSTART:(.*)', event).group(1)
            reported_month, reported_day = datetime_from_utc_to_local(
                datetime.strptime(reported_start, '%Y%m%dT%H%M%SZ')).month, datetime_from_utc_to_local(
                datetime.strptime(reported_start, '%Y%m%dT%H%M%SZ')).day
            correct_month, correct_day = datetime.strptime(one_occurence_event.group(1),
                                                           '%d.%m').month, datetime.strptime(
                one_occurence_event.group(1), '%d.%m').day
            if not ((reported_day == correct_day) and (reported_month == correct_month)):
                # it's incorrect, skip adding alarms and fixes, as it will not be included
                continue
            else:
                event = wishes(event, settings)
                fixed.append(event)
                log.info(f'Found single occurrence event on {reported_day, reported_month} and added it to calendar')

        # Week based events
        # Get only the first week based event, to get baseline for weeks
        previous_week_name = week_name
        week_tracker = re.match(r'[\s\S.]*?SUMMARY:(.*?)- tyg\.(\d+)-(\d+)', event)
        if not week_tracker:
            # Some events FOR SOME REASON use Roman numerals
            week_tracker = re.match(r'[\s\S.]*?SUMMARY:(.*?)- tyg\.'
                                    r'(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})', event)
            # Roman numerals are a pain
        try:
            week_name = week_tracker.group(1)
        except AttributeError:
            # re.match returned None, meaning not found
            week_name = None
        if week_tracker and not (week_name == previous_week_name):
            log.debug(week_tracker, week_name)
            first_week = re.match(r'[\s\S.]*?DTSTART:(.*)', event).group(1)
            first_week_datetime = datetime_from_utc_to_local(
                datetime.strptime(first_week, '%Y%m%dT%H%M%SZ'))

        week_tracker = re.match(r'[\s\S.]*?SUMMARY:(.*?)- tyg\.(\d+)-(\d+)', event)
        roman = False
        if not week_tracker:
            week_tracker = re.match(r'[\s\S.]*?SUMMARY:(.*?)- tyg\.'
                                    r'((?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3}))', event)
            roman = True
        try:
            week_name_test = week_tracker.group(1)
        except AttributeError:
            # re.match returned None, meaning not found
            week_name_test = None
        if week_tracker and week_name_test == week_name:
            if roman:
                # Please be a single Roman numeral in event, I can't be bothered to make this two
                week_range = list(range(from_roman(week_tracker.group(2)), 30))
                # Why 30? Why not, one term shouldn't be longer than 30 weeks
            else:
                week_range = list(range(int(week_tracker.group(2)), int(week_tracker.group(3)) + 1))
            week_event = re.match(r'[\s\S.]*?DTSTART:(.*)', event).group(1)
            week_event_datetime = datetime_from_utc_to_local(
                datetime.strptime(week_event, '%Y%m%dT%H%M%SZ'))
            delta = (week_event_datetime - first_week_datetime).days + 7  # account for same week check
            week_delta = math.ceil(delta / 7)
            log.debug(week_name, week_range, week_event_datetime, delta, week_delta)
            if roman:
                if from_roman(week_tracker.group(2)) != 1:
                    if not week_delta % from_roman(week_tracker.group(2)):
                        log.info(f"Added week-based event {week_name} on week {week_delta}")
                        event = wishes(event, settings)
                        fixed.append(event)
                    else:
                        continue
                else:
                    if week_delta in [k for k in week_range if k % 2]:
                        log.info(f"Added week-based event {week_name} on week {week_delta}")
                        event = wishes(event, settings)
                        fixed.append(event)
                    else:
                        continue
            else:
                if week_delta in week_range:
                    log.info(f"Added week-based event {week_name} on week {week_delta}")
                    event = wishes(event, settings)
                    fixed.append(event)
                else:
                    continue

        event = wishes(event, settings)

        # Check location and adjust time to alert before
        if re.match(r'[\s\S.]*?SUMMARY:.*? E', event):
            # WEII
            togo = settings['time_to_go']['weii']
        elif re.match(r'[\s\S.]*?SUMMARY:.*? CT', event):
            # Centech
            togo = settings['time_to_go']['centech']
        elif re.match(r'[\s\S.]*?SUMMARY:.*? PE', event):
            # Pentagon
            togo = settings['time_to_go']['pentagon']
        elif re.match(r'[\s\S.]*?SUMMARY:.*? CI', event):
            # Rdzewiak
            togo = settings['time_to_go']['rdzewiak']
        elif re.match(r'[\s\S.]*?SUMMARY:.*? Ox', event):
            # Oxford
            togo = settings['time_to_go']['oxford']
        elif re.match(r'[\s\S.]*?SUMMARY:.*? Aula', event) or re.match(r'[\s\S.]*?SUMMARY:.*? M', event):
            # Mechaniczny
            togo = settings['time_to_go']['mechaniczny']
        else:
            # Random, not matched
            togo = settings['time_to_go']['random']
        # Find second last newline to locate line before ending of event entry
        second_last_newline = event.rfind('\n', 0, len(event) - 1)
        # Append full event with added alarm according to location to a new list
        fixed.append(
            event[:second_last_newline + 1] + f'BEGIN:VALARM\nTRIGGER:-PT{togo}M\nATTACH;VALUE=URI:Chord\nACTION'
                                              f':AUDIO\nEND:VALARM' +
            event[second_last_newline:])
    log.info('Success!' if assemble_calendar_file(header, fixed, 'newcal.ics')
          else 'Something has gone catastrophically wrong')
