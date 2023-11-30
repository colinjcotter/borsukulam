import netCDF4
import xarray as xr
import numpy
import scipy.interpolate as interpolate
import scipy.optimize as optimize
import json
import logging
from shgo import shgo

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Functions to wrap longitude and latitude
def wraplat(t):
	return (t +90) % 180 - 90

def wraplong(t):
	return (t +180) % 360 - 180

def wraplatlong(x):
	return [wraplat(x[0]),wraplong(x[1])]

#Todo:
#Define an ulampoint class
#Optional tolerances
#Allow for optional data from the ds source; else the first two data sources should be used


def findulam(t,p,lat,long,**kwargs):
	#  Fix the tolerance	
	


	""" Numerically Computes an ulam point from temperature and pressure data
	
	Arguments
	t - temperature as 2 dimensional array
	p - pressure as 2 dimensional array
	lat - latitude as 2 dimensional array
	long - longidude as 2 dimensional array
	initialguess (optional) - initial point as [lat,long] for the numerical method (default [-32,10])
	tolerance (optional) - the tolerance after which to stop the basinhopping method (default 1e-11)
	basinhoppingdisplay (optional) - if true then print steps in the basinhopping method
	
	Returns array consisting of
	'ulampoint' - [lat,lng] of the ulampoint found
	'fun' - (difference of temperature)^2 + difference of pressure)^2 at the ulampoint and its antipodal
	'OptimizeResult_basinhopping' - OptimizeResult of the basinhopping method
	"""
	
	# Set default arguments
	defaultKwargs = { 'initialguess': [-32.0,10.0], 'tolerance': 1e-13, 'basinhoppingdisplay': False}
	kwargs = { **defaultKwargs, **kwargs }
	
	initialguess = kwargs['initialguess']
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

	ft = interpolate.RegularGridInterpolator((lat, long), t)
	ft2 = interpolate.RegularGridInterpolator((lat, long), t2)

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
	
	#Try basinhopping to get a zero with an initial guess
	xinit = numpy.array(initialguess)	
	ret = optimize.basinhopping(fsq, xinit,T=2,niter=100,callback=callback_func,disp=kwargs['basinhoppingdisplay'])

	
	

	if (ret.fun>tolerance):
		logger.info('Basinhopping failed.  Runnning differential_evolution instead')
		logger.info(ret)
		bounds = [(-90.0,90.0),(-180.0,180.0)]	
		ret = optimize.differential_evolution(fsq, bounds)
		
	output = {'OptimizeResult_basinhopping': ret,
			  'fun' : ret.fun,
			  'ulampoint' : [ret.x[0],ret.x[1]]
	}

	return(output)

# The following gets Ulam point within a ds file
# If the ds contains a single step then it returns the ulam data of that step
# If the ds contains two or more steps then it returns N ulam data between each timestep
# def process_ds_all_steps(N,initialguess,ds):
# 	if (ds.step.data.size==0):
# 		t = ds['t2m'].data	
# 		p =ds['msl'].data
# 		ulam = findulam(t,p,ds0['latitude'],ds0['longitude'],initialguess)
# 		print('i,j,ulamtime',ulamtime,'ulampoint: ',ulam['ret'].x,'fun: ',ulam['ret'].fun,'nit: ',ulam['ret'].nit)
# 	else:
# 		for j in range(ds.step.data.size-1):
# 			for i in range(N):
# 				ulam = compute_ulampoint(ds,j,j+1,i,N,initialguess)
# 				initialguess = [ulam['ret'].x[0],ulam['ret'].x[1]]


def compute_ulampoint_between_timesteps(ds,timestep_start,timestep_end,i,N,**kwargs):
	""" Returns an ulamdata at a specified time
		
	Arguments
	ds - ECMWF data source file
	timestep_start - Initial time step to use within ds source file
	timestep_end - Final time step to use within ds source file
	i,N - Return ulampoint from temperature and pressure data linearly interpolated at time (1-i/N)*timestep_start + (i/N)*timestep_end
		(requires i between 0 and N)
	initialguess (optional) - initial point as [lat,long] for the numerical method (default [-32,10])
	
	Returns array consisting of
	'ulampoint' - [lat,lng] of the ulampoint found
	'ulamtime'  - the specific time used to compute the ulampoint
	'fun' - (difference of temperature)^2 + difference of pressure)^2 at the ulampoint and its antipodal
	'OptimizeResult_basinhopping' - OptimizeResult of the basinhopping method	
	"""
	# Todo: Return error if i is not between 0 and N
	
	
	defaultKwargs = { 'initialguess': [-32.0,10.0], 'tolerance': 1e-13}
	kwargs = { **defaultKwargs, **kwargs }

	
	ds0=ds.sel(step=timestep_start)
	ds1=ds.sel(step=timestep_end)
	
	
	ulamstep = (1-i/N)*ds0.step.data+ (i/N)*ds1.step.data
	ulamtime = ds.time.data + ulamstep
	t = (i/N) * ds1['t2m'].data + (N-i)/N * ds0['t2m'].data	
	p = (i/N) * ds1['msl'].data + (N-i)/N * ds0['msl'].data
	
	ulam = findulam(t,p,ds0['latitude'],ds0['longitude'],initialguess=kwargs['initialguess'],tolerance = kwargs['tolerance'])
	
	#Note: This output should be the same as that in the case of N=1 of compute_ulampoints_between_timesteps (better to use a class)
	output = {
	'ulampoint': ulam['ulampoint'],
	'fun' : ulam['fun'],
	'ulamstep': ulamstep,
	'ulamtime':ulamtime,
	'OptimizeResult_basinhopping': ulam['OptimizeResult_basinhopping']
	}
	
	return(output)

def compute_ulampoints_between_timesteps(ds,**kwargs):
	""" Returns an array of ulamdata objects.  
	If the ds file contains more than one timestep then an ulampoint for each of the timesteps is returned
	
	Arguments
	ds - ECMWF data source file
	steps (optional) - an array of timesteps valid within ds that will be used. (default to all timesteps available)
	N (optional) - Divide the interval between consecutive timesteps into N equally spaced timesteps, and compute the ulampoints at these times assuming linear interpolation of the data.  This is only used if the length of timesteps is at least 2.  Note that if N is larger than 2 then the ulam point for the final step will not be included (default N=1)
	
	
	
	initialguess (optional) - initial point as [lat,long] for the first run of the numerical method.  After that the result from the previous iteration is used as the initialguess.  Default [-32,10]
	
	"""

	defaultKwargs = { 'initialguess': [-32.0,10.0],'N': 1, 'steps': ds.step.data, 'tolerance': 1e-13}
	kwargs = { **defaultKwargs, **kwargs }
	
	N = kwargs['N']
	steps = kwargs['steps']
	initialguess = kwargs['initialguess']
	tolerance = kwargs['tolerance']
	ulamlist = []
	
	if (len(steps)==1):	
		N = 1
		steps.append(steps[0])
	
	for j in range(len(steps)-1):
		for i in range(N):
			computedulam = compute_ulampoint_between_timesteps(ds,steps[j],steps[j+1],i,N,tolerance=tolerance,initialguess=initialguess)
			ulamlist.append(computedulam)
			text=computedulam['ulampoint'], computedulam['ulamtime'],computedulam['ulamstep'],computedulam['OptimizeResult_basinhopping'].fun,computedulam['OptimizeResult_basinhopping'].nit
			logger.info(text)
			initialguess = computedulam['ulampoint']
	return(ulamlist)
	




# This is just to make debugging quicker
#open the datasource
# ds = xr.open_dataset('data.grib2',engine='cfgrib')
# N=12
# ds0=ds.sel(step='12:00:00')
# t=ds0['t2m'].data 
# p=ds0['t2m'].data
# lat = ds0['latitude']
# long = ds0['longitude']
# ulam = findulam(t,p,lat,long)

