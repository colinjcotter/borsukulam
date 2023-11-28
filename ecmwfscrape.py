#
# This does the following
# 1. Scrape most recent data from ecmwf at steps 0h and 6
# 2. Compute ulampoints at 5 minute intervals
# 3. Store these ulampoints to be used as an initial guess for the next time this file is run
# 4. Creates a javascript file that contains (a) some of the data from the ulampoints that are found within tolerance
# (b) The temperature and pressure data at step 0h and at step 6h
# 5. Copy this javascript file to my Amazon S3 bucket
#
# It is designed to be run every 3 hours about so that the website always loads with a few hours of ulampoints as data
#
import logging 

logging.basicConfig(filename = 'ecmwfscrape.log',format='%(asctime)s %(levelname)s  %(message)s',datefmt='%Y-%m-%d %H:%M:%S')


from ecmwf.opendata import Client
import xarray as xr
import findulam
import numpy
import json
import pickle
import subprocess
import time






logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# The following should be adapted for the local filesystem structure
ulamlistsfolder = 'ulamlists/' 
latest_ulamlist_filename = ulamlistsfolder + 'latest_ulamlist.pickle'
latest_bu_filename = 'website/bu.js'
steps=[numpy.timedelta64(0,'h'), numpy.timedelta64(6,'h')]

###
### Note: To actually have the script do the scraping the following block must be uncommented
###
###

logger.info("ECMWFscrape starting...")


# logger.info('Retrieving data from ECMWF')
# client = Client()
# result  = client.retrieve(
#     step=[0,6],
#     type="cf",
#     param = ["2t","msl"],
#     target="data.grib2",
# )

logger.info("Opening data from ECMWF")
ds = xr.open_dataset('data.grib2',engine='cfgrib')

# Todo: Convert the data to float to save space

# The following tries to load data from the last time this file was run
# and attempts to find an ulampoint close to the start time at step 0h
# to feed as the initial guess of the numerical algorithm


# The following is hardcoded just for testing
#initialguess = [9.51287637483811, 50.63705018119461]

initialguess = [0,0]

logger.info('Trying to get initial guess from previously stored data')
try: 
	ulamlist_initial = pickle.load(open(latest_ulamlist_filename, "rb"))
	ulamlist__initial_cropped = [ulam for ulam in ulamlist_initial if ((ulam['fun']< 1e-12) and (ulam['ulamtime']<ds.time.data))]
	if len(ulamlist__initial_cropped)>0:
		initialguess = ulamlist_initial_cropped[len(-1)]['ulampoint']
		logger.info('Got initial guess ulampoint:'+str(ulamlist_initial_cropped[len(-1)]['ulampoint'])+'at ulamtime:'+str(ulamlist_initial_cropped[len(-1)]['ulamtime']))
	else: 
		logger.warning('Unable to find any useful initial guess from previously stored data')
except:
	logger.warning('Unable to get load data from previous stored data')

#
# This is where the computation is made
#
logger.info('Finding ulampoints')
start = time.time()
ulamlist = findulam.compute_ulampoints_between_timesteps(ds,steps=steps,N=12,initialguess=initialguess,tolerance=1e-10)
logger.info('Finding ulampoints completed in '+str(time.time()-start)+'s')
#
# Write the ulam points to a file for the next time this script is run
#
logger.info('Writing pickle')
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

logger.info('ulamlist length: '+ str(len(ulamlist))+ ' of which '+ str(len(ulamlist_cropped))+ ' were found within tolerance')

## Todo: Only write the bu file if there is at least one ulam point found within the first hour of the ds.date (we expect this should always happen
## so it is a safeguard as we are updating the bu.js file An hour after UTC.  This will prevent a bu.js file that only has ulam points in the future

ds0=ds.sel(step=steps[0])
ds1=ds.sel(step=steps[1])

bu = {
'ds_datetime':  numpy.datetime_as_string(numpy.datetime64(ds.time.data, 'ms')), 
'ulamlist': ulamlist_cropped,
'final_timestep': numpy.timedelta64(ds1.step.data, 's').astype(float),
't_initial': numpy.array(ds0['t2m'].data).tolist(),
'p_initial': numpy.array(ds0['msl'].data).tolist(),
't_final': numpy.array(ds1['t2m'].data).tolist(),
'p_final': numpy.array(ds1['msl'].data).tolist()
}
f = open(latest_bu_filename , 'w' )
logging.info('Writing bu.js file')
f.write('const bu=' + json.dumps(bu)+'\n')
f.close

logger.info('Moving bu.js file to S3 bucket')
subprocess.Popen(["aws", "s3", "cp", latest_bu_filename, "s3://ponderonward-website/bu_latest.js"], shell=True)
