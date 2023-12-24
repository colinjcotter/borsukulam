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


# class ulampoint:
# 	""" Class that contains the information of a single ulampoint.   Fun means the energy at that point (so will be zero at a true ulampoint)
# 	"""
# 	def __init__(self, point,fun):
# 		self.point = point
# 		self.fun = fun
# 	def __str__(self):
# 		return f"Ulampoint -  Point: {self.point} Fun : {self.fun}"
# 


#TODO: Allow for optional choice of numerical method to use

def findulam(t,p,lat,long,**kwargs):
	""" Numerically Computes an ulam point from two variables (classically temperature and pressure)
	If an initialguess is given then start with the scipy.optimize.basinhopping method starting at this initialguess
	If either initialguess is not given, or the basinhopping does not give an answer within tolerance
	then use the scipy.optimize.differential_evolution method
	
	Arguments
	t - first variable as 2 dimensional array
	p - second variable as 2 dimensional array
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
		logger.debug('Runnning basinhopping with initialguess '+str(kwargs['initialguess']))
		ret = optimize.basinhopping(fsq, xinit,T=2,niter=100,callback=callback_func,disp=False)
		if (ret.fun<tolerance):
			skip_optimizing_with_differential_evolution = True
			ret['findulam']="Computed with scipy.optimize.basinhopping"
		else:
			logger.debug('Basinhopping failed to get within tolerance')
			logger.debug('Basinhopping Optimizeresult:')
			logger.debug(ret)
			
	if skip_optimizing_with_differential_evolution==False:
		logger.debug('Runnning differential_evolution')
		bounds = [(-90.0,90.0),(-180.0,180.0)]	
		ret = optimize.differential_evolution(fsq, bounds)
		ret['findulam']="Computed with scipy.optimize.differential_evolution"
	
	return(ret)




# Todo: Option just to return those ulampoints within tolerance
# Option for scaling of variables for the numerical method
# Option as to what we return (do we return just the point or the entire output of the optimizemethod) 
#

def ulampoints(ds,**kwargs):
	""" Calculates ulampoints from an xarray datasource from ECMWF
	
	Arguments
	ds - ECMWF data source file	

	Optional Arguments
	steps -  numpy.array of timedelta64 steps at which to calculate ulampoints.  If there are not equal to those in ds.step.data then the xarray interpolate will be used (default ds.steps.data)
	tolerance - tolerance of the numerical method (default 1e-13)
	
	Returns: xarray object containing all the ulampoints found
	
	Coordinates: steps
			     non-coordinate variables of ds
				 
	Data variables: ulampoint_lat: the latitude location of the ulampoint (if numerical method succeeds within tolerance)
					ulampoint_lon: the longtitude location of the ulampoint  (if numerical method succeeds within tolerance)
					Optimizeresult: the details of the optimization result (type Optimizeresult)
	"""

	# Setup default arguments
	defaultKwargs = {'tolerance': 1e-13, 'steps': ds.step.data}
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
		
	if max(steps)> max(datasteps) or min(steps)<min(datasteps):
		raise Exception("All steps must be in the range included in the ds file")

	
	da_lat = xr.DataArray(data=None,dims=['step','variable_1','variable_2'], coords = { 'step': steps,'variable_1': variables, 'variable_2': variables})
	da_lon = xr.DataArray(data=None,dims=['step','variable_1','variable_2'], coords = { 'step': steps,'variable_1': variables, 'variable_2': variables})
	da_opt = xr.DataArray(data=numpy.empty([steps.size,len(variables),len(variables)],dtype=object),dims=['step','variable_1','variable_2'], coords = { 'step': steps,'variable_1': variables, 'variable_2': variables})

	#
	# Now loop over pairs of variables (v1,v2) and timesteps
	#
	# Todo: Fixme for the initialguess

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
				}
				
				if j>0:
					parameters['initialguess']=initialguess
		
				t = data0[variables[v1]].data
				p = data0[variables[v2]].data

				computedulam = findulam(t,p,ds['latitude'],ds['longitude'],**parameters)
				logger.info('Ulampoint for step '+str(steps[j])+' : '+str([computedulam.x[0],computedulam.x[1]]))
				
				# Add to the xarray
				da_opt.loc[dict(step=steps[j],variable_1=variables[v1],variable_2=variables[v2])]=computedulam
				da_opt.loc[dict(step=steps[j],variable_1=variables[v2],variable_2=variables[v1])]=computedulam
				if computedulam.fun<tolerance:
					da_lat.loc[dict(step=steps[j],variable_1=variables[v1],variable_2=variables[v2])]=computedulam.x[0]
					da_lat.loc[dict(step=steps[j],variable_1=variables[v2],variable_2=variables[v1])]=computedulam.x[0]
					da_lon.loc[dict(step=steps[j],variable_1=variables[v1],variable_2=variables[v2])]=computedulam.x[1]
					da_lon.loc[dict(step=steps[j],variable_1=variables[v2],variable_2=variables[v1])]=computedulam.x[1]
				logger.debug(computedulam)
				initialguess = computedulam.x
	
	# TODO I think there is a better way to include the time as a coordinate, but this will do for now
	ds1 = xr.Dataset({"ulampoint_lat": da_lat, "ulampoint_lon": da_lon, "optimizeresult": da_opt, "time": ds.time})
	return(ds1)
