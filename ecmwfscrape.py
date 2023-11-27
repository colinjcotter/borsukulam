#
# This does the following
# 1. Scrape most recent data from ecmwf at steps 0h and 6
# 2. Compute ulampoints at 1 minute intervals
# 3. Store these ulampoints to be used as an initial guess for the next time this file is run
# 4. Creates a javascript file that contains (a) all the ulampoints that are found within tolerance
# (b) The temperature and pressure data at step 0h and at step 6h
#
# It is designed to be run every 3 hours about so that the website always loads with a few hours of ulampoints as data
#

from ecmwf.opendata import Client
import xarray as xr
import findulam
import numpy
import json
import pickle
import logging

logging.basicConfig(filename = 'ecmwf-scraping.log',encoding = 'utf-8',level=logging.WARN)

# The following should be adapted for the local filesystem structure
ulamlistsfolder = 'ulamlists/' 
latest_ulamlist_filename = ulamlistsfolder + 'latest_ulamlist.pickle'
latest_bu_filename = 'website/bu.js'
steps=[numpy.timedelta64(0,'h'), numpy.timedelta64(6,'h')]

# logging.info('Retrieving data from ECMWF')
# client = Client()
# result  = client.retrieve(
#     step=[0,6],
#     type="cf",
#     param = ["2t","msl"],
#     target="data.grib2",
# )

logging.info('Opening data from ECMWF')

ds = xr.open_dataset('data.grib2',engine='cfgrib')

# The following tries to load data from the last time this file was run
# and attempts to find an ulampoint close to the start time at step 0h
# to feed as the initial guess of the numerical algorithm

initialguess = [9.51287637483811, 50.63705018119461]
logging.info('Trying to get initial guess from previously stored data')
try: 
	ulamlist_initial = pickle.load(open(latest_ulamlist_filename, "rb"))
	ulamlist__initial_cropped = [ulam for ulam in ulamlist_initial if ((ulam['fun']< 1e-12) and (ulam['ulamtime']<ds.time.data))]
	if len(ulamlist__initial_cropped)>0:
		initialguess = ulamlist_initial_cropped[len(-1)]['ulampoint']
		logging.info('Got initial guess ulampoint:'+str(ulamlist_initial_cropped[len(-1)]['ulampoint'])+'at ulamtime:'+str(ulamlist_initial_cropped[len(-1)]['ulamtime']))
	else: 
		logging.warning('Unable to find any useful initial guess from previously stored data')
except:
	logging.warning('Unable to get load data from previous stored data')

#
# This is where the computation is made
#
logging.info('Finding ulampoints')
ulamlist = findulam.compute_ulampoints_between_timesteps(ds,steps=steps,N=72,initialguess=initialguess,tolerance=1e-10)

#
# Write the ulam points to a file for the next time this script is run
#
logging.info('Writing pickle')
# Write the ulamlist as pickle
ulamlist_filename = ulamlistsfolder+str(ds.time.data)+'.pickle'
with open(ulamlist_filename, 'wb') as handle:
	pickle.dump(ulamlist, handle, protocol=pickle.HIGHEST_PROTOCOL)
## copy it to latest (there is surely a better way here)
with open(latest_ulamlist_filename , 'wb') as handle:
	pickle.dump(ulamlist, handle, protocol=pickle.HIGHEST_PROTOCOL)



#
# Write the javascript file that contains the required data
# All we record here is the ulamstep (rounded to second) and the ulampoint
# Also we throw away those ulampoints not within a tolerances of 1e-8

ulamlist_cropped = [[numpy.timedelta64(ulam['ulamstep'], 's').astype(float),ulam['ulampoint']] for ulam in ulamlist if ulam['OptimizeResult_basinhopping'].fun<1e-8]

logging.info('ulamlist length: '+ str(len(ulamlist))+ ' of which '+ str(len(ulamlist))+ ' were found within tolerance')

## Todo: Only write the bu file if there is at least one ulam point found within the first hour of the ds.date (we expect this should always happen
## so it is a safeguard as we are updating the bu.js file An hour after UTC.  This will prevent a bu.js file that only has ulam points in the future

ds0=ds.sel(step=steps[0])
ds1=ds.sel(step=steps[1])

bu = {
'ds_datetime':  numpy.datetime_as_string(numpy.datetime64(ds.time.data, 'ms')), 
'ulamlist': ulamlist_cropped,
't_initial': numpy.array(ds0['t2m'].data).tolist(),
'p_initial': numpy.array(ds0['msl'].data).tolist(),
't_final': numpy.array(ds1['t2m'].data).tolist(),
'p_final': numpy.array(ds1['msl'].data).tolist()
}
f = open(latest_bu_filename , 'w' )
f.write('const bu=' + json.dumps(bu)+'\n')
f.close