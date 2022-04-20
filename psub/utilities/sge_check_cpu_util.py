import psutil 
print('{}%'.format(psutil.cpu_percent(interval=4)))
