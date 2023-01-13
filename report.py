import csv
from collections import defaultdict
from datetime import datetime, date, time, timedelta
from typing import List
from zoneinfo import ZoneInfo

import dateparser
import feedparser
import holidays
from holidays.constants import FEB, JAN, JUL, NOV
from dateutil.relativedelta import MO, TH
from dateutil.relativedelta import relativedelta as rd
from pyluach import dates
from timezonefinder import TimezoneFinder
from uszipcode import SearchEngine



class ChabadCivilHolidays(holidays.US):
    def _populate(self, year):
        super()._populate(year)
        self.pop_named('New Year')
        self.pop_named('Washington')
        self.pop_named('Juneteenth')
        self.pop_named('Independence')
        self.pop_named('Columbus')
        self.pop_named('Veterans')
        self.pop_named('Chr')

        self._add_with_observed(date(year, JAN, 1), "New Year's Day", before=False) # stricly no backtracks to fridays
        self[date(year, FEB, 1) + rd(weekday=MO(+3))] = "Presidents' Day"
        self._add_with_observed(date(year, JUL, 4), 'Independence Day', before=False)
        self[date(year, NOV, 1) + rd(weekday=TH(+4)) + rd(days=+1)] = 'Black Friday'
        self[date(year, 12, 25)] = 'Nittel'

civil_holidays = ChabadCivilHolidays()



class Day:
    dow = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    major_holidays = ('Pesach', 'Shavuos', 'Yom Kippur', 'Succos', 'Shmini Atzeres', 'Simchas Torah') # Days when shachris is at 10am. rosh hashana intentionally left out.


    def __init__(self, row: dict):
        # note, civ_date, weekday, heb_date, shachris, shema, mincha, maariv, candles, ending

        self.row: dict = row
        self.end: str = self.get_end()

        self.date: datetime = self.row['date']
        self.DST: bool = bool(self.date.dst())
        self.weekday: str = self.dow[self.date.weekday()]

        self.heb_date: dates.HebrewDate = dates.HebrewDate.from_pydate(self.date)
        self.heb_holiday: str = self.heb_date.festival(include_working_days=False)

        self.reason: str = self.get_reason()

        self.shachris: str = self.get_shachris()

        self.shema: str = dateparser.parse(row['Latest Shema ']).time().strftime("%-I:%M %p")

        self.mincha: str = self.get_mincha()

        self.maariv: str = self.get_maariv()

        self.candles: str = self.get_candle_lighting()


    def __repr__(self):
        return str((
            self.reason,
            self.date.strftime("%Y/%m/%d"),
            self.weekday,
            f'{self.heb_date:%-d %B}',
            self.shachris,
            self.shema,
            self.mincha,
            self.maariv,
            self.candles,
            self.end,
        ))


    def as_dict(self):
        return {
            'note': self.reason,
            'civ_date': self.date.strftime("%Y/%m/%d"),
            'weekday': self.weekday,
            'heb_date': f'{self.heb_date:%-d %B}',
            'shachris': self.shachris,
            'shema': self.shema,
            'mincha': self.mincha,
            'maariv': self.maariv,
            'candles': self.candles,
            'ending': self.end,
        }


    def get_shachris(self) -> str:
        shachris = time(hour=6, minute=45)
        if self.is_chol_hamoed():
            shachris = time(hour=7, minute=30)
        if self.weekday == 'Sun' or civil_holidays.get(self.date):
            shachris = time(hour=8, minute=00) # sunday, or sunday-style
        if self.weekday == 'Sat' or self.heb_holiday in self.major_holidays:
            shachris = time(hour=10, minute=00) # shabbos / yom tov
        if self.heb_holiday == 'Rosh Hashana':
            shachris = time(hour=9, minute=00)
        return shachris.strftime("%-I:%M %p")


    def get_reason(self) -> str:
        reason = self.heb_holiday
        if not reason: reason = self.is_chol_hamoed()
        if not reason: reason = civil_holidays.get(self.date)
        if not reason: reason = self.heb_date.fast_day()
        if not reason: reason = ''
        return reason


    def get_mincha(self) -> str:
        if self.heb_date == dates.HebrewDate(self.heb_date.year, 7, 9): # Erev Yom Kippur
            return time(hour=15, minute=00).strftime("%-I:%M %p")
        if self.heb_date == dates.HebrewDate(self.heb_date.year, 7, 10): # Yom Kippur
            return 'after the break'

        if self.weekday == 'Fri': # 10 minutes after candle lighting rounded to the nearest 5 minutes, but no later than 11 minutes after candle lighting
            candle_time = dateparser.parse(self.get_candle_lighting())
            mincha = candle_time + timedelta(minutes=10) - timedelta(minutes=candle_time.minute % 5)
            if (candle_time + timedelta(minutes=10) - mincha).total_seconds() > 2.5 * 60:
                mincha += timedelta(minutes=5)
            if (mincha - candle_time).total_seconds() > 11 * 60:
                mincha -= timedelta(minutes=5)

            return mincha.strftime("%-I:%M %p")

        return ''


    def get_maariv(self) -> str:
        if self.heb_date == dates.HebrewDate(self.heb_date.year, 7, 9): # Erev Yom Kippur
            return 'after Kol Nidrei'
        if self.heb_date == dates.HebrewDate(self.heb_date.year, 7, 10): # Yom Kippur
            return 'after Neilah'

        if self.weekday == 'Fri':
            return 'after Kabbalas Shabbos'

        if self.weekday == 'Sat' and self.end: # end Shabbos/Yom Tov time rounded to the nearest 5 minutes
            raw_time = dateparser.parse(self.end)
            maariv = raw_time - timedelta(minutes=raw_time.minute % 5)
            if (raw_time - maariv).total_seconds() > 2.5 * 60:
                maariv += timedelta(minutes=5)
            maariv = maariv.time()
        else: # normal standalone maariv
            maariv = time(hour=20, minute=00)

            if self.mincha or self.DST: # can probably get away with not looking at DST if get_maariv() were to be run after self.mincha has been filled in by Report()
                return 'after Mincha'
            # or self.weekday == 'Sun' or civil_holidays.get(self.date)

        if maariv:
            return maariv.strftime("%-I:%M %p")


    def is_chol_hamoed(self) -> str:
        chols = {
            (1, 17): 'Chol Hamoed Pesach',
            (1, 18): 'Chol Hamoed Pesach',
            (1, 19): 'Chol Hamoed Pesach',
            (1, 20): 'Chol Hamoed Pesach',

            (7, 17): 'Chol Hamoed Succos',
            (7, 18): 'Chol Hamoed Succos',
            (7, 19): 'Chol Hamoed Succos',
            (7, 20): 'Chol Hamoed Succos',
            (7, 21): 'Chol Hamoed Succos'
        }
        return chols.get((self.heb_date.month, self.heb_date.day), False)


    def fast_adjust(self) -> timedelta:
        is_fast = self.heb_date.fast_day()

        if is_fast in ('Tzom Gedalia', '10 of Teves','Taanis Esther',  '17 of Tamuz'):
            return timedelta(minutes=15)
        if is_fast == '9 of Av':
            return timedelta(minutes=45)
        return timedelta(microseconds=0)


    def get_candle_lighting(self) -> str:
        lighting = self.row['Candle Lighting ']
        if not lighting:
            lighting = self.row['Candle Lighting | Fast Begins ']
        if not lighting:
            lighting = self.row['Candle Lighting after ']
            if lighting:
                lighting = 'after ' + lighting
        return lighting.strip()


    def get_end(self) -> str:
        endings = (
            'Shabbat Ends ',
            'Shabbat Ends | Earliest time to kindle Chanukah Menorah ',
            'Holiday Ends ',
            'Shabbat/Holiday Ends ',
            'Shabbat/Holiday/Fast Ends ',
            'Holiday/Fast Ends ',
            'Nightfall (Tzeit Hakochavim) | Fast Ends '
        )
        for ending in endings:
            end = self.row.get(ending, '')
            if end:
                break
        return end.strip()



class Report:
    def __init__(self) -> None:
        self.days: List[Day] = []
        self.have_friday: bool = False


    def process(self, day: Day) -> None:
        if day.weekday == 'Fri':
            self.have_friday = True

            if len(self.days) >= 7:
                last_friday_mincha = dateparser.parse(self.days[-7].mincha)
                if not self.days[-7].DST:
                    last_friday_mincha += timedelta(hours=1)
                last_friday_mincha = last_friday_mincha.time()
                this_friday_mincha = dateparser.parse(day.mincha).time()
                earliest_friday_mincha = min(last_friday_mincha, this_friday_mincha) # earliest friday mincha
                for day_ in self.days[-5:]: # fill in the rest of the week, skipping any that are already set
                    if not day_.mincha and (day_.DST or day_.weekday == 'Sun' or civil_holidays.get(day_.date)): # all DST and any sunday like days
                        computed_mincha = datetime.combine(day_.date, earliest_friday_mincha) - day_.fast_adjust() # adjustments for fast days
                        day_.mincha = computed_mincha.time().strftime("%-I:%M %p")
                        day_.maariv = 'after Mincha'

        if day.weekday == 'Sat' and self.have_friday: # 15 minutes before Friday candle lighting rounded to the nearest 5 minutes
            candle_lighting_less_15: datetime = dateparser.parse(self.days[-1].get_candle_lighting()) - timedelta(minutes=15)
            mincha = candle_lighting_less_15 - timedelta(minutes=candle_lighting_less_15.minute % 5)
            if (candle_lighting_less_15 - mincha).total_seconds() > 2.5 * 60:
                mincha += timedelta(minutes=5)
            day.mincha = mincha.time().strftime("%-I:%M %p")

        self.days.append(day)


    def load_csv(self, filename) -> None:
        ''' for loading .csv files made by yeartimes.py '''
        timezone = self.zip_to_tz(filename[:5])

        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile)
            for n, row in enumerate(reader):
                # if n < 365:
                #     continue
                # if n > 375:
                #     break

                temp_date: datetime = dateparser.parse(row['date'])
                temp_date += timedelta(hours=3)
                row['date'] = temp_date.replace(tzinfo=ZoneInfo(timezone))

                day = Day(row)
                self.process(day)


    def load(self, zipcode: str, start: datetime, end: datetime) -> None:
        extra_days = 6 # to make sure we have 2 fridays bracketing every day we care about
        dates = [start+timedelta(days=x-extra_days) for x in range((end-start).days + 1 + (extra_days*2))]
        for date in dates:
            print(date.strftime('%m/%d/%Y'), zipcode)
            times = self.ingest_times(zipcode, date)
            self.process(Day(times))


    def ingest_times(self, zipcode: str, date: datetime) -> defaultdict:
        times = None
        while not times:
            times = self.chabad_org(zipcode, date)

        date += timedelta(hours=3)
        timezone = self.zip_to_tz(zipcode)
        times['date'] = date.replace(tzinfo=ZoneInfo(timezone))

        errata = {
            'Sunset (Shkiah)Fast Begins ': 'Sunset (Shkiah) | Fast Begins ',
            'Sunset (Shkiah)  | Earliest time to kindle Chanukah Menorah ': 'Sunset (Shkiah) | Earliest time to kindle Chanukah Menorah ',
            'Plag Hamincha (“Half of Mincha”)  | Earliest time to kindle Chanukah Menorah ': 'Plag Hamincha (“Half of Mincha”) | Earliest time to kindle Chanukah Menorah ',
            'Shabbat Ends  | Earliest time to kindle Chanukah Menorah ': 'Shabbat Ends | Earliest time to kindle Chanukah Menorah '
        }

        for error, correction in errata.items():
            if error in times:
                times[correction] = times.pop(error)

        return defaultdict(str, times)


    def save(self, filename: str) -> None:
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ('note', 'civ_date', 'weekday', 'heb_date', 'shachris', 'shema', 'mincha', 'maariv', 'candles', 'ending')
            writer = csv.DictWriter(csvfile, fieldnames, restval='')
            writer.writeheader()
            writer.writerows((day.as_dict() for day in self.days[6:-6]))


    def chabad_org(self, zipcode: str, date: datetime) -> dict:
        feed = f"http://www.chabad.org/tools/rss/zmanim.xml?z={zipcode}&tDate={date.strftime('%m/%d/%Y')}"
        info = feedparser.parse(feed)
        return {entry['title'].split('-')[0]:entry['title'].split('-')[1] for entry in info.entries}


    def zip_to_tz(self, zipcode: str) -> str:
        search = SearchEngine(simple_or_comprehensive=SearchEngine.SimpleOrComprehensiveArgEnum.simple)
        tf = TimezoneFinder()
        result = search.by_zipcode(zipcode)
        return tf.timezone_at(lat=result.lat, lng=result.lng)



if __name__ == '__main__':
    today = date.today()
    year = today.year
    if today.month > 6:
        year += 1
    zipcodes = [94303, 16504]
    for zipcode in zipcodes:
        start =  datetime(year,1,1)
        end = datetime(year,12,31)
        filename = f'davening_times/{zipcode}_davening_times_{start.date()}_to_{end.date()}.csv'

        r = Report()
        r.load(zipcode, start, end)
        r.save(filename)
