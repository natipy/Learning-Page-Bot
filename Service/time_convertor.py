#Before Using This package Give a copyright for the author
from time import time

def time_parse(now:time,time_) -> str:
    time_parse = int(now)-int(time_)
    year = time_parse//60//60//24//7//30//365
    month=time_parse//60//60//24//7//30
    week = time_parse//60//60//24//7
    day=time_parse//60//60//24
    hour = time_parse//60//60
    minute= time_parse//60
    second = time_parse
    if year>=1:
        return str(year)+" Years"  if year > 1 else str(year)+ " Year"
    elif month >=1:
        return str(month)+" Months"  if month > 1 else str(month)+ " Month"
    elif week >=1:
        return str(week)+" Weeks"  if week > 1 else str(week)+ " Week"
    elif day >=1:
        return str(day)+" Days"  if day > 1 else str(day)+ " Day"
    elif hour >=1:
        return str(hour)+" Hours"  if hour > 1 else str(hour)+ " Hour"
    elif minute >=1:
        return str(minute)+" Minutes"  if minute > 1 else str(minute)+ " Minute"
    elif second >=2:
        return str(second)+" Seconds"  if second > 1 else str(second)+ " Second"
    else:
        return 'Just now'
