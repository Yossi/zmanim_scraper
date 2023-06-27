Zmanim Scraper

yeartimes.py
Gets all the zmanim for this year and next. Fairly raw, usually needs a little massage in excel/gsheets.


report.py
Computes davening times[^1] to be announced at shul. If run during the first half of the year will make the table for this year, if run during second half it will do next year.
[^1]: Follows the pretty opinionated rules set forth by my local Chabad house. If you want the rules diferent you can change them, but they are not organized for ease of doing this. It's probably not hard, but you will need to skim all the code.

To run either file for your locale, edit in the zipcode(s) you want near the bottom of the script(s) and run at the start of each year. Or a little before, your choice. use whatever scheduler you want, for example crontab.

You can also have github run the jobs for you with github actions. You should edit the user and email in the .yaml files near the bottom.
