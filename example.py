import netCDF4
import numpy
import scipy.interpolate as interpolate
import scipy.optimize as optimize

#open the file for reading
rootgrp = netCDF4.Dataset("era40files/Feb1978_1200_temp.nc", "r", format="NETCDF4")
rootgrp_pressure = netCDF4.Dataset("era40files/Feb1978_1200_pressure.nc", "r", format="NETCDF4")

#print(rootgrp.dimensions['latitude'].size)
#print(rootgrp_pressure.dimensions['latitude'].size)



#get some dimension sizes
nlong = rootgrp.dimensions['longitude'].size
nlat = rootgrp.dimensions['latitude'].size

#use the first day (dataset is midday for all days in February)
timeslice = 0

#extract the temperature
t = rootgrp.variables['t2m']
p = rootgrp_pressure.variables['msl']


#restrict to the selected timeslice as numpy array
t = t[timeslice, : , :]
p = p[timeslice, : , :]



#get coordinates of grid points as numpy arrays
long = rootgrp.variables['longitude'][:]
lat = rootgrp.variables['latitude'][:]

#interpolator expects grid coordinates in increasing order
#so we flip latitudes (first axis)
t = numpy.flip(t, axis=0)
p = numpy.flip(p, axis=0)
lat = numpy.flip(lat, axis=0)

#### Temperature
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

## Pressure
#make a copy to contain the antipodal values
p2 = 0.*p
#rotate by 180 degrees [longitude is second index]
nlong_half = int(nlong/2)
p2[: , :] = numpy.concatenate((p[:, nlong_half:],
                               p[:, :nlong_half]), axis=1)
#flip in the latitude direction
p2 = numpy.flip(p2, axis=0)

#construct an interpolator
fp = interpolate.RegularGridInterpolator((lat[:], long[:]), p-p2)

#ft = interpolate.RegularGridInterpolator((lat[:], long[:]), t)
#ft2 = interpolate.RegularGridInterpolator((lat[:], long[:]), t2)

#make a function for the square of the interpolator

def fsq(x):
    return (fp(x)**2)+1000*(f(x)**2)

#find a zero of f with initial guess x0
x0 = numpy.array([30.,100.])
ret = optimize.basinhopping(fsq, x0, niter=200)
print(ret.x, ret.fun,ret.message)

print(f(ret.x))
print(fp(ret.x))



