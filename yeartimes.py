import csv
import datetime

import feedparser


def chabad_org(zipcode, date):
    feed = 'http://www.chabad.org/tools/rss/zmanim.xml?z=%s&tDate=%s' % (zipcode, date)
    info = feedparser.parse(feed)
    return {entry['title'].split('-')[0]:entry['title'].split('-')[1] for entry in info.entries}

def main(zipcode, start, end):
    filename = f'{zipcode}_zmanim_{start}_to_{end}.csv'
    with open(filename, 'w') as csvfile:
        fieldnames = [
            'date',
            'Dawn (Alot Hashachar) ',
            'Dawn (Alot Hashachar) | Fast Begins ',
            'Earliest Tallit and Tefillin (Misheyakir) ',
            'Earliest Tallit (Misheyakir) ',
            'Sunrise (Hanetz Hachamah) ',
            'Latest Shema ',
            'Latest Shacharit ',
            'Finish Eating Chametz before ',
            'Sell and Burn Chametz before ',
            'Nullify Chametz before ',
            'Midday (Chatzot Hayom) ',
            'Earliest Mincha (Mincha Gedolah) ',
            'Mincha Ketanah (“Small Mincha”) ',
            'Plag Hamincha (“Half of Mincha”) ',
            'Plag Hamincha (“Half of Mincha”) | Earliest time to kindle Chanukah Menorah ',
            'Candle Lighting ',
            'Candle Lighting | Fast Begins ',
            'Sunset (Shkiah) ',
            'Sunset (Shkiah) | Fast Begins ',
            'Sunset (Shkiah) | Earliest time to kindle Chanukah Menorah ',
            'Candle Lighting after ',
            'Shabbat Ends ',
            'Shabbat Ends | Earliest time to kindle Chanukah Menorah ',
            'Holiday Ends ',
            'Shabbat/Holiday Ends ',
            'Shabbat/Holiday/Fast Ends ',
            'Holiday/Fast Ends ',
            'Nightfall (Tzeit Hakochavim) ',
            'Nightfall (Tzeit Hakochavim) | Fast Ends ',
            'Bedikat Chametz (Search for Chametz) ',
            'Midnight (Chatzot HaLailah) ',
            'Shaah Zmanit (proportional hour) ',
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        d1 = datetime.date(*start)
        d2 = datetime.date(*end)

        dates = (d1 + datetime.timedelta(days=x) for x in range((d2-d1).days + 1))

        for date in dates:
            print(date.strftime('%m/%d/%Y'), zipcode)
            times = {}
            while not times:
                times = chabad_org(zipcode, date.strftime('%m/%d/%Y'))
            times['date'] = date

            errata = {
                'Sunset (Shkiah)Fast Begins ': 'Sunset (Shkiah) | Fast Begins ',
                'Sunset (Shkiah)  | Earliest time to kindle Chanukah Menorah ': 'Sunset (Shkiah) | Earliest time to kindle Chanukah Menorah ',
                'Plag Hamincha (“Half of Mincha”)  | Earliest time to kindle Chanukah Menorah ': 'Plag Hamincha (“Half of Mincha”) | Earliest time to kindle Chanukah Menorah ',
                'Shabbat Ends  | Earliest time to kindle Chanukah Menorah ': 'Shabbat Ends | Earliest time to kindle Chanukah Menorah '
            }

            for error, correction in errata.items():
                if error in times:
                    times[correction] = times.pop(error)

            writer.writerow(times)



if __name__ == '__main__':
    today = datetime.date.today()
    year = today.year
    zipcodes = [94303, 16504]
    for zipcode in zipcodes:
        main(zipcode, (year,1,1), (year+1,12,31))
