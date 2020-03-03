import netCDT4
import numpy

#open the file for reading
rootgrp = netCDF4.Dataset("era40files/Feb1978_1200.nc", "r", format="NETCDF4")

#get some dimension sizes
nlong = rootgrp.dimensions['longitude'].size
nlat = rootgrp.dimensions['lstitude'].size

#use the first day (dataset is midday for all days in February)
timeslice = 0

#extract the temperature
t = rootgrp.variables['t2m']

#restrict to the selected timeslice
t = t[timeslice, : , :]

#make a copy to contain the antipodal values
t2 = 0.*t
#rotate by 180 degrees [longitude is second index]
nlong_half = int(nlong_half/2)
t2[: , :] = t[: , -nlong_half:nlong_half]
