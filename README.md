# attendance

GUI -

1. Heading - Week Attendance Tracking (current weekday = date - time)

2. Tabular weekday-wise hours management system; the user can mark the day as "office attended/office not attended". 

3. If marking the day as office attended, the user can input the start time and end time for the day, and the remaining hours are calculated accordingly.

4. For office not attended, do not ask for any hours input.

5. Make a dynamic GUI so that the website dimensions auto-modify based pc / mobile.


Calculation - 

1. Total hours required for a week is 45 hours. Each day 9 hours, but there is flexibility like user can do 5 hours one day then remaining 4 hours get split for remaining days. Same in case 
user does some extra hours for a day, like 11 hours (which is 2 hours extra, then it gets reduced on average from the required 9 hours from remaining days.

2. If marking office as attended, get start time from user and show suggested time based on required hours for that day. (if not split from previous days, then show 9 hours; otherwise, based on the split-time calculation).

3. If marking office as not attended, reduce 9 hours automatically from the required 45 hours weekly total. Do it for all days that the user marks as "office not attended". If the user reverts the day
from "office not attended" to "office attended", then add 9 hours back to the required weekly total hours and do calculations accordingly.

3. Working days are from Monday to Friday. Saturday and Sunday are off.

4. Ignore all other cases like lunchtime, break time, etc. Do not consider such scenarios.
