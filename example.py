import netCDF4
import numpy
import scipy.interpolate as interpolate

#open the file for reading
rootgrp = netCDF4.Dataset("era40files/Feb1978_1200.nc", "r", format="NETCDF4")

#get some dimension sizes
nlong = rootgrp.dimensions['longitude'].size
nlat = rootgrp.dimensions['latitude'].size

#use the first day (dataset is midday for all days in February)
timeslice = 0

#extract the temperature
t = rootgrp.variables['t2m']

#restrict to the selected timeslice as numpy array
t = t[timeslice, : , :]

#get coordinates of grid points as numpy arrays
long = rootgrp.variables['longitude'][:]
lat = rootgrp.variables['latitude'][:]

#interpolator expects grid coordinates in increasing order
#so we flip latitudes (first axis)
t = numpy.flip(t, axis=0)
lat = numpy.flip(lat, axis=0)

#make a copy to contain the antipodal values
t2 = 0.*t
#rotate by 180 degrees [longitude is second index]
nlong_half = int(nlong/2)
t2[: , :] = numpy.concatenate((t[:, nlong_half:],
                               t[:, :nlong_half]), axis=1)
#flip in the latitude direction
t2 = numpy.flip(t2, axis=0)

#construct an interpolator
f = interpolate.RegularGridInterpolator((lat[:], long[:]), t-t2)


