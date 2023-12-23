#
# Package to numerically find ulam points from ECMWF data
#
#
# Typical use
#
# Get the data from ECMWF
#
# from ecmwf.opendata import Client
# client = Client()
# result  = client.retrieve(step=[0,6],type="cf",param = ["2t","msl","sp"],target="data.grib2",)
# ds = xr.open_dataset('data.grib2',engine='cfgrib')
#
#
# ulampoints(ds)
#
# Alternatively you can use the data array itself
#
# ds0=ds.sel(step='0:00:00')
# t=ds0['t2m'].data 
# p=ds0['t2m'].data
# lat = ds0['latitude']
# long = ds0['longitude']
#
# findulam(t,p,lat,long)
# 


#Todo:
#Options for logging
#See about ECMWF accuracy at 0,6,12h etc
#Get head around xarray interpolation
#Think about how you want to change the ecmwfscrape.py

import netCDF4
import xarray as xr
import numpy
import scipy.interpolate as interpolate
import scipy.optimize as optimize
import json
import logging

logger = logging.getLogger(__name__)

# Functions to wrap longitude and latitude
def wraplat(t):
	return (t +90) % 180 - 90

def wraplong(t):
	return (t +180) % 360 - 180

def wraplatlong(x):
	return [wraplat(x[0]),wraplong(x[1])]


class ulampoint:
	""" Class that contains the information of a single ulampoint.   Fun means the energy at that point (so will be zero at a true ulampoint)
	"""
	def __init__(self, point,fun):
		self.point = point
		self.fun = fun
	def __str__(self):
		return f"Ulampoint -  Point: {self.point} Fun : {self.fun}"



#TODO: Allow for optional choice of numerical method to use

def findulam(t,p,lat,long,**kwargs):
	""" Numerically Computes an ulam point from to data sets (classically temperature and pressure)
	If an initialguess is given then start with the scipy.optimize.basinhopping method starting at this initialguess
	If either initialguess is not given, or the basinhopping does not give an answer within tolerance
	then use the scipy.optimize.differential_evolution method
	
	Arguments
	t - first data set as 2 dimensional array
	p - second data set as 2 dimensional array
	lat - latitude as 2 dimensional array
	long - longidude as 2 dimensional array
	initialguess (optional) - initial point as [lat,long] for the numerical method
	tolerance (optional) - the tolerance after which to stop the basinhopping method (default 1e-13)
	
	Returns OptimizeResult of the final method used
	"""
	
	# Set default arguments
	defaultKwargs = { 'tolerance': 1e-13}
	kwargs = { **defaultKwargs, **kwargs }
	
	tolerance = kwargs['tolerance']
	#get some dimension sizes
	nlong = long.size

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
	f = interpolate.RegularGridInterpolator((lat, long), t-t2,bounds_error=False)

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

	fp = interpolate.RegularGridInterpolator((lat, long), p-p2,bounds_error=False)

	#make a function for the square of the interpolator
	def fsq(x):
		return (fp(wraplatlong(x))**2)+100*(f(wraplatlong(x))**2)
		
	# This tolerancecounter is kind of dumb; it asks for a few iterations below tolerance
	# before returning False.  FIXME

	tolerancecounter = 0
	def callback_func(x, f, accepted):
		nonlocal tolerancecounter
		if (fsq(x)<tolerance):
			tolerancecounter=tolerancecounter+1
		if (tolerancecounter==2):
			return True
		else:
			return False
		
	skip_optimizing_with_differential_evolution=False
	
	if 'initialguess' in kwargs:
		xinit = numpy.array(kwargs['initialguess'])	
		ret = optimize.basinhopping(fsq, xinit,T=2,niter=100,callback=callback_func,disp=False)
		if (ret.fun<tolerance):
			skip_optimizing_with_differential_evolution = True
		else:
			logger.debug('Basinhopping failed to get within tolerance')
			logger.debug(ret)
			
	if skip_optimizing_with_differential_evolution==False:
		logger.debug('Runnning differential_evolution')
		bounds = [(-90.0,90.0),(-180.0,180.0)]	
		ret = optimize.differential_evolution(fsq, bounds)
	return(ret)





def ulampoints(ds,**kwargs):
	""" Calculates ulampoints from an xarray datasource from ECMWF
	
	Arguments
	ds - ECMWF data source file	

	Optional Arguments
	steps -  List of timedeltas to use.  If there are not in the ds.step file then the xarray interpolate will be used (default all steps in ds file)
	variables -  List of the non-coordinate variables within the ds file to compute the ulam points  (default all variables available)
	N  - Divide the interval between subsequent elements of steps into N equally spaced timesteps, and compute the ulampoints at these times assuming linear interpolation of the data.  This is only used if the length of timesteps is at least 2.  Note that if N is larger than 2 then the ulam point for the final step will not be included (default N=1; ignored if only one step is given in steps)
	tolerance - tolerance of the numerical method (default 1e-13)
	initialguess - initial point as [lat,long] for the first run of the numerical method.  After that the result from the previous iteration is used as the initialguess.  	
	
	Returns: xarray object containing all the ulampoints found
	
	Coordinates: time
				 variable_1 is the first variable used for the ulampoint (no ulam point is given when variable_1 = variable_2)
				 variable_2 is the first variable used for the ulampoint 
				 
	Data variables: ulampoint: the data of the ulampoint (type ulampoint)
	"""

	# Setup default arguments
	defaultKwargs = {'N': 1, 'tolerance': 1e-13, 'steps': ds.step.data, 'variables': [var for var in ds.data_vars if var not in ds.coords]}
	kwargs = { **defaultKwargs, **kwargs }
	N = kwargs['N']
	steps = kwargs['steps']
	tolerance = kwargs['tolerance']
	variables = kwargs['variables']
			
	#If there is only one step given then we will return just the ulam point of that step
	if len(steps)==1:
		steps.append(steps[0])
		N=1
	

	timesteps = [ (1-i/N)*steps[j]+ (i/N)*steps[j+1] for i in range(N)  for j in range(len(steps)-1)]
	
	da = xr.DataArray(data=None,dims=['step','variable_1','variable_2'], coords = { 'step': timesteps,'variable_1': variables, 'variable_2': variables})

	#
	# Now loop over pairs of variables (v1,v2), timesteps in steps (j) and then i from 0 to N and calculate the ulampoint at (i/N) between steps[j] and steps[j+1]
	#

	for v1 in range(len(variables)):	
		for v2 in range(v1+1,len(variables)):
			print('Calculating Ulampoints for ', variables[v1],variables[v2])
			for j in range(len(steps)-1):	
				
				data0 = ds.interp(step=steps[j])
				data1 = ds.interp(step=steps[j+1])
			
				for i in range(N):	
				
					parameters = {
					'tolerance':tolerance,
					}
					if 'initialguess' in locals():
						parameters['initialguess']=initialguess
			
					t = (i/N) * data1[variables[v1]].data + (N-i)/N * data0[variables[v1]].data
					p = (i/N) * data1[variables[v2]].data + (N-i)/N * data0[variables[v2]].data

					computedulam = findulam(t,p,ds['latitude'],ds['longitude'],**parameters)
		
					## Create an ulampoint object
					u = ulampoint(point=computedulam.x,fun=computedulam.fun)

					# Add to the correct place in the xarray
					ulamstep = (1-i/N)*steps[j]+ (i/N)*steps[j+1]
					
					print('ulamstep',ulamstep,'u',u)
					da.loc[dict(step=ulamstep,variable_1=variables[v1],variable_2=variables[v2])]=u
					da.loc[dict(step=ulamstep,variable_1=variables[v2],variable_2=variables[v1])]=u
					logger.debug(u)
					initialguess = computedulam.x	
	
	# TODO I think there is a better way to include the time as a coordinate, but this will do for now
	ds1 = xr.Dataset({"ulampoint": da, "time": ds.time})
	return(ds1)
