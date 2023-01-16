In gsheets:
* lock the rop row with the headers so it stays on top (drag the thick grey line from above the numbers running down the left to between the 1 and 2)
* click Format > Alternating colors
* change the fill color for the top row to something slighty darker
* to make weeks stand out a little better, click Format > Conditional formatting.
    Apply to range: C1:C635
    Format cells if...: Text starts with   S
    Formatting style: pick a fill color
* to highlight today's date, click Format > Conditional formatting.
    Apply to range: A2:J635 (has to be A2. A1 will make it highlight yesterday)
    Format cells if...: Custom formula is   =$B2=today()
    Formatting style: pick a fill color
