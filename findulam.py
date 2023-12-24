import netCDF4
import xarray as xr
import numpy
import scipy.interpolate as interpolate
import scipy.optimize as optimize
import json
import logging
import pdb

logger = logging.getLogger(__name__)

# Functions to wrap longitude and latitude
def wraplat(t):
	return (t +90) % 180 - 90

def wraplong(t):
	return (t +180) % 360 - 180

def wraplatlong(x):
	return [wraplat(x[0]),wraplong(x[1])]


def findulam(t,p,lat,long,**kwargs):
	""" Numerically Computes an ulam point from two variables (classically temperature and pressure)
	
	This is achieved by minimizing the energy functional defined to be (t(x)-t(-x))^2 + c^2 (p(x)-p(-x))^2 
	where c is a constant and t and p are interpolated linearly in the lat and long directions.
	
	Method: If an initialguess is given then start with the scipy.optimize.basinhopping method starting at this initialguess.
	If either initialguess is not given, or the basinhopping does not give an answer within tolerance
	then use the scipy.optimize.differential_evolution method
	
	Arguments
	t - first variable as 2 dimensional array
	p - second variable as 2 dimensional array
	lat - latitude as 2 dimensional array
	long - longidude as 2 dimensional array
	disp (optional) - display steps of basinhoppin method (default false)
	initialguess (optional) - initial point as [lat,long] for the numerical method
	tolerance (optional) - the tolerance after which to stop the basinhopping method (default 1e-13)
	c (optional) - minimise the following function (t(x)-t(-x))^2 + c (p(x)-p(-x))^2 where c=factor.  (default c=1)
	
	Returns OptimizeResult of the final method used that includes the following
	findulam: Description of which numerical method was used
	x: numparray of lat/lon of ulampoint
	fun:  (t(x)-t(-x))^2 + c (p(x)-p(-x))^2 at ulampoint
	fun_without_factor: value of (t(x)-t(-x))^2 + c^2 (p(x)-p(-x))^2 at ulampoint
	"""
	
	# Set default arguments
	defaultKwargs = { 'tolerance': 1e-10,'c': 1, 'disp': False}
	kwargs = { **defaultKwargs, **kwargs }
	tolerance = kwargs['tolerance']
	c = kwargs['c']
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
	
	# Todo: Fixme set default value of c
	#if c==None:
	#	c = numpy.mean((t.flatten()-t2.flatten())**2) / numpy.mean((p.flatten()-p2.flatten())**2)
	
	#make a function for the square of the interpolator
	def fsq(x):
		return c*(fp(wraplatlong(x))**2)+(f(wraplatlong(x))**2)
	
	def fsq_withoutfactor(x):
		return (fp(wraplatlong(x))**2)+(f(wraplatlong(x))**2)

# This was kind of dumb, but the below seems to be working fine
# 	tolerancecounter = 0
# 	def callback_func(x, f, accepted):
# 		tolerance2 = 1e-10
# 		nonlocal tolerancecounter
# 		if (f<tolerance2):
# 			tolerancecounter=tolerancecounter+1
# 		if (tolerancecounter==2):
# 			return True
# 		else:
# 			return False
			
			
	def callback_func(x, f, accepted):
		if f<tolerance:
			return True
		else:
			return False
		
		
	skip_optimizing_with_differential_evolution=False
	
	if 'initialguess' in kwargs:
		xinit = numpy.array(kwargs['initialguess'])	
		logger.debug('Runnning basinhopping with initialguess '+str(kwargs['initialguess']))
		
		# I do not know what the best value of T is here.  Perhaps one should run a neural net on this to optimize for real data?
		ret = optimize.basinhopping(fsq, xinit,T=2,niter=100,callback=callback_func,disp=kwargs['disp']).lowest_optimization_result
		if (ret.fun<tolerance):
			skip_optimizing_with_differential_evolution = True
			ret['findulam']="Computed with scipy.optimize.basinhopping"
			ret['fun_without_factor'] = fsq_withoutfactor(ret.x)
		else:
			logger.debug('Basinhopping failed to get within tolerance')
			logger.debug('Basinhopping Optimizeresult:')
			logger.debug(ret)
			
	if skip_optimizing_with_differential_evolution==False:
		logger.debug('Runnning differential_evolution')
		bounds = [(-90.0,90.0),(-180.0,180.0)]	
		if 'initialguess' in kwargs:
			xinit = numpy.array(kwargs['initialguess'])	
		else:
			xinit = [0,0]
		ret = optimize.differential_evolution(fsq,bounds)
		ret['findulam']="Computed with scipy.optimize.differential_evolution"
		ret['fun_without_factor'] = fsq_withoutfactor(ret.x)
	
	return(ret)




def ulampoints(ds,**kwargs):
	""" Calculates ulampoints from an xarray datasource (e.g. from ECMWF)
	
	Arguments
	ds - data source file with 3 indexed coordinates named step, longtitude and latitude

	Optional Arguments
	steps -  numpy.array of timedelta64 steps at which to calculate ulampoints.  If these contain elements not in ds.step.data then the xarray interpolate will be used (default ds.steps.data)
	tolerance - tolerance of the numerical method (default 1e-13)
	
	Returns: xarray object containing all the ulampoints found within tolerance, for all distinct pairs of variables in the ds file
	
	Coordinates: steps
			     non-coordinate variables of ds
				 
	Data variables: ulampoint_lat: the latitude location of the ulampoint (if numerical method succeeds within tolerance else None)
					ulampoint_lon: the longtitude location of the ulampoint  (if numerical method succeeds within tolerance else None)
					Optimizeresult: details of the optimization result (type Optimizeresult; included irrespective of success of numerical method)
	"""

	# Setup default arguments
	defaultKwargs = {'tolerance': 1e-10, 'steps': ds.step.data}
	kwargs = { **defaultKwargs, **kwargs }
	steps = kwargs['steps']
	tolerance = kwargs['tolerance']
	# Take all the variables in the ds files that are not coordinates
	variables = [var for var in ds.data_vars if var not in ds.coords]
	

	# If there is only one step given then make it into an array	
	if steps.size ==1:
		steps = numpy.reshape(steps,[1])
	
	datasteps = ds.step.data
	if datasteps.size ==1:
		datasteps = numpy.reshape(datasteps,[1])
	
	# Check that all the steps given are within the ds file
	if max(steps)> max(datasteps) or min(steps)<min(datasteps):
		raise Exception("All steps must be in the range included in the ds file")

	# Setup the DataArrays
	da_lat = xr.DataArray(data=None,dims=['step','variable_1','variable_2'], coords = { 'step': steps,'variable_1': variables, 'variable_2': variables})
	da_lon = xr.DataArray(data=None,dims=['step','variable_1','variable_2'], coords = { 'step': steps,'variable_1': variables, 'variable_2': variables})
	da_opt = xr.DataArray(data=numpy.empty([steps.size,len(variables),len(variables)],dtype=object),dims=['step','variable_1','variable_2'], coords = { 'step': steps,'variable_1': variables, 'variable_2': variables})

	#
	# Loop over pairs of variables (v1,v2) and steos
	#

	for v1 in range(len(variables)):	
		for v2 in range(v1+1,len(variables)):
			logger.info('Calculating Ulampoints for variables: '+variables[v1]+' and '+variables[v2])
			

			for j in range(steps.size):	
			
				if steps.size ==1:
					data0 = ds
				else:
					data0 = ds.interp(step=steps[j])	
				
							
				parameters = {
				'tolerance':tolerance,
				'c': 1,
				}
				
				if j>0:
					parameters['initialguess']=initialguess
		
				t = data0[variables[v1]].data
				p = data0[variables[v2]].data

				computedulam = findulam(t,p,ds['latitude'],ds['longitude'],**parameters)
				logger.info('Ulampoint for step '+str(steps[j])+' : '+str([computedulam.x[0],computedulam.x[1]])+' fun: '+str(computedulam.fun)+' fun_without_factor: '+str(computedulam.fun_without_factor)+' findulammethod: '+ str(computedulam.findulam))
				
				# Add to the xarray
				da_opt.loc[dict(step=steps[j],variable_1=variables[v1],variable_2=variables[v2])]=computedulam
				da_opt.loc[dict(step=steps[j],variable_1=variables[v2],variable_2=variables[v1])]=computedulam
				if computedulam.fun<tolerance:
					da_lat.loc[dict(step=steps[j],variable_1=variables[v1],variable_2=variables[v2])]=computedulam.x[0]
					da_lat.loc[dict(step=steps[j],variable_1=variables[v2],variable_2=variables[v1])]=computedulam.x[0]
					da_lon.loc[dict(step=steps[j],variable_1=variables[v1],variable_2=variables[v2])]=computedulam.x[1]
					da_lon.loc[dict(step=steps[j],variable_1=variables[v2],variable_2=variables[v1])]=computedulam.x[1]
				initialguess = computedulam.x
	
	# TODO I think there is a better way to include the time as a coordinate, but this will do for now
	ds1 = xr.Dataset({"ulampoint_lat": da_lat, "ulampoint_lon": da_lon, "optimizeresult": da_opt, "time": ds.time})
	return(ds1)
