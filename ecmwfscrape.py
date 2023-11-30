#
# Typical Usage: 
# python3 ecmwfscrape.py --firststep 0 --laststep 12 --date 0 --time 6 --N 720
#
# This will get create and save ulampoints every minute in a 12 hour period of the forecast starting today at 06:00UTC
#
# In more detail it does the following:
#
# 1. Scrape most recent data from ecmwf at given time and date
# 2. Compute ulampoints at certain intervals between timestep firststep and timestep laststep
# 3. Creates two javascript files.  One is bu-date-firststep-laststep.js that has all the ulam 
#    points and the temp/pressure data at firsttime and lasttime.  The second is bu-latest-data.js that is smaller and just
#    points to the first file.
# 5. Copy these two javascript file to my Amazon S3 bucket
#


import logging 
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

#def my_handler(type, value, tb):
#	logger.exception("Uncaught exception: {0}",format(str(value)))
#sys.excepthook = my_handler


parser = argparse.ArgumentParser()
parser.add_argument('--firststep', dest='firststep', type=int, help='Firststep',default=0)
parser.add_argument('--laststep', dest='laststep', type=int, help='Laststep',default=6)
parser.add_argument('--date', dest='date', type=int, help='date',default =0)
parser.add_argument('--time', dest='time', type=int, help='time',default =0)
parser.add_argument('--scrapedryrun', dest='scrapedryrun', type=int, default=0, help='if nonzero then do not download from ECMWF but assume data.grib2 is already there (for testing only)')
parser.add_argument('--website-directory',dest='bu_local_directory',type=str,default = "./website/",help='directory to store js files produced from this script')
parser.add_argument('--N',dest='N', type=int,default=720,help='Number of ulampoints to compute (default 720 which is 1 per minute for 12 hours')
parser.add_argument('--s3dryrun',dest='s3dryrun',type=int, default=0, help='if nonzero then do not try to move files to s3 buckets but assume data.grib2 is already there (for testing only)')
parser.add_argument('--logfile',dest='logfile',type=str, default = 'ecmwfscrape.log',help='logfile to use')
#parser.add_argument('--verbose',dest='verbose',type=int, default=0,help='if non zero then verbose logging about the numerical method')
args = parser.parse_args()

logging.basicConfig(filename = args.logfile,format='%(asctime)s %(levelname)s  %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
# Write the two filenames
#

bu_filename = 'bu-'+numpy.datetime_as_string(ds.time.data,'D')+'T'+ str(args.time)+'h:'+str(firststep)+':'+str(laststep)+'.js'
bu_local_filename = bu_local_directory+bu_filename

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
	file.write('const bulatestdatafilename="'+bu_filename+'.gz"')

#
# Move the files to the S3 buckets
#
if (args.s3dryrun==0):
	s3websitedirectory = "s3://ponderonward-website/Borsuk-Ulam/"
	logger.info('Writing bu_datafile '+str(bu_datafile)+' to S3 bucket '+str(s3websitedirectory))
	subprocessoutput=subprocess.run(["aws s3 cp "+bu_datafile+' '+s3websitedirectory+'bu-latest-data.js'], shell=True)
	logger.info(subprocessoutput)

	s3bufilesdirectory = "s3://bursk-ulam-bufiles/"

	logger.info('Compressing '+str(bu_local_filename))
	subprocessoutput=subprocess.run(['gzip -f '+bu_local_filename], shell=True)
	logger.info(subprocessoutput)
	
	logger.info('Writing bu_local_filename '+str(bu_local_filename)+' to S3 bucket '+str(s3bufilesdirectory))
	subprocessoutput=subprocess.run(["aws s3 cp "+bu_local_filename+'.gz'+' '+s3bufilesdirectory+' --content-encoding gzip'], shell=True)
	logger.info(subprocessoutput)

