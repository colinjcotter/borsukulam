#
# Usage: 
#
# This will get data at two steps from 06:00UTC today as follows:
#
# 1. Scrape most recent data from ecmwf at steps firststep and laststep
# 2. Compute ulampoints at certain intervals (hardcoded)
# 3. Creates a javascript file that contains (a) some of the data from the ulampoints that are found within tolerance
# (b) The temperature and pressure data at step firststep and at step laststep
# 5. Copy this javascript file to my Amazon S3 bucket
#
#
# Todo
# Option for scraping or run dummy
# Better location of logfiles
# bu_local_directory as option
# Option for data.grib file location


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

# The following should be adapted for the local filesystem structure
#bu_local_directory = '/home/ubuntu/borsuk-ulam/website/'
# Script tries to find ulampoints within this tolerance
tolerance = 1e-10

logger = logging.getLogger(__name__)

#def my_handler(type, value, tb):
#	logger.exception("Uncaught exception: {0}",format(str(value)))
#sys.excepthook = my_handler

logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument('--firststep', dest='firststep', type=int, help='Firststep',default=0)
parser.add_argument('--laststep', dest='laststep', type=int, help='Laststep',default=6)
parser.add_argument('--date', dest='date', type=int, help='date',default =0)
parser.add_argument('--time', dest='time', type=int, help='time',default =0)
parser.add_argument('--scrapedryrun', dest='scrapedryrun', type=int, default=0, help='if nonzero then do not download from ECMWF but assume data.grib2 is already there (for testing only)')
parser.add_argument('--website-directory',dest='bu_local_directory',type=str,default = "./website/",help='directory to store js files produced from this script')
parser.add_argument('--N',dest='N', type=int,default=720,help='Number of ulampoints to compute (default 720 which is 1 per minute for 12 hours')
parser.add_argument('--s3dryrun',dest='s3dryrun',type=int, default=0, help='if nonzero then do not try to move files to s3 buckets but assume data.grib2 is already there (for testing only)')
args = parser.parse_args()

bu_local_directory  = args.bu_local_directory

# Initialize Data
firststep = args.firststep
laststep = args.laststep
steps=[numpy.timedelta64(firststep,'h'), numpy.timedelta64(laststep,'h')]

###
### Note: To actually have the script do the scraping the following block must be uncommented
###

logger.info("ECMWFscrape starting...")


if (args.scrapedryrun==0):
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
N=args.N
start = time.time()
ulamlist = findulam.compute_ulampoints_between_timesteps(ds,steps=steps,N=N,tolerance=tolerance)
logger.info('Finding ulampoints completed in '+str(time.time()-start)+'s')



# Write the javascript file that contains the required data
# All we record here is the ulamstep (rounded to second) and the ulampoint
# Also we throw away those ulampoints not within a tolerances of 1e-8

ulamlist_cropped = [[numpy.timedelta64(ulam['ulamstep'], 's').astype(float),ulam['ulampoint']] for ulam in ulamlist if ulam['OptimizeResult'].fun<tolerance]

logger.info('ulamlist length: '+ str(len(ulamlist))+ ' of which '+ str(len(ulamlist_cropped))+ ' were found within tolerance')

#
# Define the filename
#

bu_filename = 'bu-'+numpy.datetime_as_string(ds.time.data,'D')+'-'+str(firststep)+'-'+str(laststep)+'.js'
bu_local_filename = bu_local_directory+bu_filename

## Todo:Really we should check that there is at least one ulampoint found (say within the first hour)
## else the website will fallback to much older data

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
f = open(bu_local_filename, 'w' )
logging.info('Writing bu.js file')
f.write('var bu=' + json.dumps(bu)+'\n')
f.close

bu_datafile = bu_local_directory+'bu-latest-data.js'
with open(bu_datafile, 'w') as file:
	file.write('const bulatestdatafilename="'+bu_filename+'"')


if (args.s3dryrun==0):
	s3websitedirectory = "s3://ponderonward-website/Borsuk-Ulam/"
	logger.info('Writing bu_datafile '+str(bu_datafile)+' to S3 bucket '+str(s3websitedirectory))
	subprocessoutput=subprocess.run(["aws s3 cp "+bu_datafile+' '+s3websitedirectory+'bu-latest-data.js'], shell=True)
	logger.info(subprocessoutput)

	s3bufilesdirectory = "s3://bursk-ulam-bufiles/"
	logger.info('Writing bu_local_filename '+str(bu_local_filename)+' to S3 bucket '+str(s3bufilesdirectory))

	subprocessoutput=subprocess.run(["aws s3 cp "+bu_local_filename+' '+s3bufilesdirectory], shell=True)
	logger.info(subprocessoutput)

