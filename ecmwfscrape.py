#
# Usage: python3 ecmwfscrape.py --firststep 0 --laststep 12 --date 0 --time 6
#
# This will get data at two steps from 06:00UTC today as follows:
#
# 1. Scrape most recent data from ecmwf at steps firststep and laststep
# 2. Compute ulampoints at certain intervals (hardcoded)
# 3. Creates a javascript file that contains (a) some of the data from the ulampoints that are found within tolerance
# (b) The temperature and pressure data at step firststep and at step laststep
# 5. Copy this javascript file to my Amazon S3 bucket
#

import logging 

logging.basicConfig(filename = 'ecmwfscrape.log',format='%(asctime)s %(levelname)s  %(message)s',datefmt='%Y-%m-%d %H:%M:%S')

import argparse
from ecmwf.opendata import Client
import xarray as xr
import findulam
import numpy
import json
import subprocess
import time
import sys




# Script tries to find ulampoints within this tolerance
tolerance = 1e-10

logger = logging.getLogger(__name__)

#def my_handler(type, value, tb):
#	logger.exception("Uncaught exception: {0}",format(str(value)))
#sys.excepthook = my_handler

logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument('--firststep', dest='firststep', type=int, help='Firststep')
parser.add_argument('--laststep', dest='laststep', type=int, help='Laststep')
parser.add_argument('--date', dest='date', type=int, help='date')
parser.add_argument('--time', dest='time', type=int, help='time')
args = parser.parse_args()

# The following should be adapted for the local filesystem structure
ulamlistsfolder = 'ulamlists/' 
latest_ulamlist_filename = ulamlistsfolder + 'latest_ulamlist.pickle'
latest_bu_filename = 'website/bu.js'

firststep = args.firststep
laststep = args.laststep

steps=[numpy.timedelta64(firststep,'h'), numpy.timedelta64(laststep,'h')]

###
### Note: To actually have the script do the scraping the following block must be uncommented
###
###

logger.info("ECMWFscrape starting...")


logger.info('Retrieving data from ECMWF')
client = Client()
result  = client.retrieve(
    step=[firststep,laststep],
    type="cf",
    param = ["2t","msl"],
    date = args.date,
    time = args.time,
    target="data.grib2",
)

logger.info("Opening data from ECMWF")
#Todo: Ideally we log the output of this command
ds = xr.open_dataset('data.grib2',engine='cfgrib')

#
# This is where the computation is made
#
logger.info('Finding ulampoints')
start = time.time()
ulamlist = findulam.compute_ulampoints_between_timesteps(ds,steps=steps,N=720,tolerance=tolerance)
logger.info('Finding ulampoints completed in '+str(time.time()-start)+'s')



# Write the javascript file that contains the required data
# All we record here is the ulamstep (rounded to second) and the ulampoint
# Also we throw away those ulampoints not within a tolerances of 1e-8

ulamlist_cropped = [[numpy.timedelta64(ulam['ulamstep'], 's').astype(float),ulam['ulampoint']] for ulam in ulamlist if ulam['OptimizeResult_basinhopping'].fun<tolerance]

logger.info('ulamlist length: '+ str(len(ulamlist))+ ' of which '+ str(len(ulamlist_cropped))+ ' were found within tolerance')

## Todo: Only write the bu file if there is at least one ulam point found within the first hour of the ds.date (we expect this should always happen
## so it is a safeguard as we are updating the bu.js file An hour after UTC.  This will prevent a bu.js file that only has ulam points in the future

ds0=ds.sel(step=steps[0])
ds1=ds.sel(step=steps[1])

bu = {
'ds_datetime':  numpy.datetime_as_string(numpy.datetime64(ds.time.data, 'ms')), 
'ulamlist': ulamlist_cropped,
'initial_timestep': numpy.timedelta64(ds0.step.data, 's').astype(float),
'final_timestep': numpy.timedelta64(ds1.step.data, 's').astype(float),
't_initial': numpy.array(ds0['t2m'].data).tolist(),
'p_initial': numpy.array(ds0['msl'].data).tolist(),
't_final': numpy.array(ds1['t2m'].data).tolist(),
'p_final': numpy.array(ds1['msl'].data).tolist()
}
f = open(latest_bu_filename , 'w' )
logging.info('Writing bu.js file')
f.write('var bu=' + json.dumps(bu)+'\n')
f.close

logger.info('Moving bu.js file to S3 bucket')
#Todo: Ideally we log the output of this command
subprocess=subprocess.run(["aws s3 cp "+latest_bu_filename+" s3://ponderonward-website/Borsuk-Ulam/bu.js"], shell=True)
logger.info(subprocess)