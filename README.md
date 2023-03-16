# Calendar fixer for LUT
###### <sub><sub>that's Lublin University of Technology</sub></sub>


Import your timetable into `calendar_app_name` for classes which actually take place on a given day.

---


#### Fixes:
- Adds one occurence classes (happening only **once**) only once - on the day they are actually taking place, instead of every week
- Adds week-based classes on weeks they are taking place, instead of every week
- Adds building-based alerts, so you can make it on time
- Allows for tweaking start/end time of event

### Usage

Run `main.py`. It should generate a `settings.yml` file. Edit it.
```yaml
group_id: '00000' # Group ID as string
time_to_go:
  pentagon: 0 # Time to notify before the event (in minutes)
  weii: 0
  centech: 0
  oxford: 0
  rdzewiak: 0
  mechaniczny: 0
  random: 0
time_wishes: # Start/end time changes
- - "name"
  - '000000'
  - '000000'
  - '000000'
  - '000000'
```
`group_id` is the ID you see in URL when visiting the timetable website (`http://planwe.pollub.pl/plan.php?id={here_is_your_id}...`)

`time_to_go` - time to notify before the event starts (in minutes), based on the building the classes are in. `random` is used when building is not defined.

<br>

`time_wishes` contains a list of list for start/end time changes. 

The example contains one event to look for and tweak start/end time. `name` is the event name, it should be short, not contain special characters and not be ambiguous (only one possible match).

Times are defined as follows: first - current start, second - current end, third - requested start, fourth - requested end

Format is HH:MM:SS with leading zeroes

Example:
```yaml
time_wishes:
- - "foo"
  - '120000'
  - '140000'
  - '114500'
  - '134500'
- - "bar"
  - '141500'
  - '161500'
  - '140000'
  - '160000'
```
All occurences of event (starting with) `foo` that have previously started at 12:00 and ended at 14:00, now start at 11:45 and end at 13:45. 
Also, all occurences of event (starting with) `bar` that have previously started at 14:15 and ended at 16:15, now start at 14:00 and end at 16:00.

<br>

When you have finished configuring, you can run `main.py` again. If there were no errors, you should have a `newcal.ics` file. This is the file you import to your calendar app of choice.
