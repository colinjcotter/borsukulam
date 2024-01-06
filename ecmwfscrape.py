'''
Script to scrape ECMWF data, calculate ulam points, and create some javascript files
to be used with the Borsuk-Ulam explorer website

Typical Usage: 
python3 ecmwfscrape.py --firststep 0 --laststep 12 --date 0 --time 6 --N 720

This will get create and save ulampoints every minute in a 12 hour period of the forecast starting today at 06:00UTC

The script is capable of doing the following:

1. Scrape data from ecmwf
2. Compute ulampoints at certain intervals between timestep 'firststep' and timestep 'laststep'
3. Creates three javascript files.  One is bu-date-firststep-laststep.js that has all the ulam 
   points and the temp/pressure data at firsttime and lasttime.  The second just contains the ulam points.  The third is a pointer file bu-latest-data.js that points
   to the first file.
4. Copy these three javascript files to S3 amazon buckets

'''

#Todo: Better understand numpy timedelta
#Todo: Check how accurate this linear interpolation is compared with measured data (and check the interpolation is working)

import logging 
import configargparse
from ecmwf.opendata import Client
import xarray as xr
import findulam
import numpy
import json
import subprocess
import time
import sys
import pdb


#def my_handler(type, value, tb):
#	logger.exception("Uncaught exception: {0}",format(str(value)))
#sys.excepthook = my_handler

# # Parse User Inputs
p = configargparse.ArgParser(default_config_files=['ecmwfscrape.conf'],description=__doc__,formatter_class=configargparse.RawDescriptionHelpFormatter)
p.add('-c', '--my-config', required=False, is_config_file=True, help='config file path')

# Perhaps there should be a better default for firststep and laststep
p.add('--firststep',  type=int, help='Firststep in hours. Must be between the smallest and largest step in the grib2 file used',default=0) 
p.add('--laststep', type=int, help='Laststep in hours.  Must be between the smallest and largest step in the grib2 file used',default=6) 

p.add('--grib2',type=str,help='skip downloading from ecmwf and use this grib2 file instead')
p.add('--grib2_filename',default='data.grib2',type=str,help='grib filename to use when scraping from ecmwf')

p.add('--date',type=int, help='date of the ecmwf scrape (ignored if --grib2 is specified)',default =0)
p.add('--time', type=int, help='time of the ecmwf scrape (ignored if --grib2 is specified)',default =0)
p.add('--step',default='',type=str,nargs='+',help='step(s) of the ecmwf scrape as an array  (ignored if --grib2 is specified)')

p.add('--N', type=int,default=360,help='Number of ulampoints to compute (default 360 which is 1 per minute if firststep and laststep differ by 6 hours')
p.add('--tolerance',type=float,default = 1e-10,help='Tolerance for the ulam points (all that do not meet this are rejected)') 

p.add('--bu_local_directory',default = "", type=str,help='local directory to store bu data files produced from this script')
p.add('--bufile_s3bucket',type=str,help='S3 bucket that bufile will be copied to')
p.add('--bufile_url',type=str,help='Url corresponding to --bufile_s3bucket')
p.add('--bupointer_s3bucket',type=str,help='S3 bucket that the pointer file will be copied to')

p.add('--logfile',type=str, default = 'ecmwfscrape.log',help='logfile to use')
p.add('--s3dryrun',type=int, default=0, help='if nonzero then do not copy files to s3 buckets (for testing only)') 
p.add('--verbose',type=int, default=0)
args= p.parse_args()

#
# Setup logger (need to make it an option to output to console; has it stopped logging to the file?)
#
logging.basicConfig(filename = args.logfile,format='%(asctime)s %(levelname)s  %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
#ConsoleOutputHandler = logging.StreamHandler()
#ConsoleOutputHandler.setLevel(logging.DEBUG)
#logger.addHandler(ConsoleOutputHandler)
logger.setLevel(logging.DEBUG)

# Initialize Data
bu_local_directory  = args.bu_local_directory

## TODO: How do you convert this to nanoseconds?
firststep = numpy.timedelta64(args.firststep*3600000000000,'ns')
laststep = numpy.timedelta64(args.laststep*3600000000000,'ns')

#
# Get data from ECMWF
#

logger.info("ECMWFscrape starting...")

#This must be a wrong way to test if this field is blank
if (args.grib2 ==None): 
	logger.info('Scraping data from ECMWF')
	client = Client()
	result  = client.retrieve(
		step = list(args.step),
		type="cf",
		param = ["2t","msl"],
		date = args.date,
		time = args.time,
		target=args.grib2_filename,
	)
	grib2file = args.grib2_filename
else:
	grib2file = args.grib2


logger.info("Opening grib2 file")
ds = xr.open_dataset(grib2file,engine='cfgrib')

#
# Find the ulam points
#


#
# Fixme: First we want to interpolate to create a new xarray with precisely two steps
# Then we feed an array of timedelta64 into findulam.ulampoints
#

logger.info('Finding ulampoints')
N=args.N
steparray = numpy.array([(1-i/N)*firststep +(i/N)*laststep for i in range(N)])

# Add the interpolated values back to the original array
ds_interp=ds.interp(step=[firststep,laststep])

start = time.time()
ulamarray = findulam.ulampoints(ds_interp,steps=steparray,tolerance=args.tolerance)
logger.info('Finding ulampoints completed in '+str(time.time()-start)+'s')


# Create a javascript file that contains the required data
# All we record here is the ulamstep (rounded to second) and the ulampoint
# Also we throw away those ulampoints not within a tolerances of 1e-8




ulamarray = ulamarray.sel(variable_1='t2m',variable_2='msl')
# Make an appropriate list of all the ulampoints that (ignoring those that are 'None')
ulamlist_cropped = [[numpy.timedelta64(ulamarray.step.data[i], 's').astype(float),[ulamarray.ulampoint_lat.data[i],ulamarray.ulampoint_lon.data[i]]] for i in range(len(ulamarray.step.data)) if ulamarray.ulampoint_lat.data[i]!=None]


logger.info('timstep length'+ str(len(ulamarray.step.data))+ ' of which '+ str(len(ulamlist_cropped))+ ' ulampoints were found within tolerance')

bu_filename = 'bu-'+numpy.datetime_as_string(ds.time.data,'D')+'T'+ str(args.time)+'h:'+str(args.firststep)+':'+str(args.laststep)+'.js'
bu_ulampoints_filename = 'bu-ulampoints-'+numpy.datetime_as_string(ds.time.data,'D')+'T'+ str(args.time)+'h:'+str(args.firststep)+':'+str(args.laststep)+'.js'


bu_local_filename = bu_local_directory+bu_filename
bu_ulampoints_local_filename = bu_local_directory+bu_ulampoints_filename


ds0=ds.interp(step=firststep) 
ds1=ds.interp(step=laststep) 


bu = {
'ds_datetime':  numpy.datetime_as_string(numpy.datetime64(ds.time.data, 'ms')), 
'ulamlist': ulamlist_cropped,											
'initial_timestep': numpy.timedelta64(firststep, 's').astype(float), 
'final_timestep': numpy.timedelta64(laststep, 's').astype(float),   
't_initial': numpy.array(ds0['t2m'].data).tolist(),						
'p_initial': numpy.array(ds0['msl'].data).tolist(),
't_final': numpy.array(ds1['t2m'].data).tolist(),
'p_final': numpy.array(ds1['msl'].data).tolist()
}
f = open(bu_local_filename, 'w' )
logging.info('Writing bu.js file')
f.write('var bu=' + json.dumps(bu)+'\n')
f.close



bu_ulampoints = {
'ds_datetime':  numpy.datetime_as_string(numpy.datetime64(ds.time.data, 'ms')), 
'ulamlist': ulamlist_cropped,
'initial_timestep': numpy.timedelta64(firststep, 's').astype(float),
'final_timestep': numpy.timedelta64(laststep, 's').astype(float),
}
f = open(bu_ulampoints_local_filename, 'w' )
logging.info('Writing bu.js file')
f.write('var bu=' + json.dumps(bu_ulampoints)+'\n')
f.close


#
# Create a smaller javascript file that points to the larger bu data file
#

bu_datafile_url = bu_local_directory+'bu-latest-data-pointer.js'
with open(bu_datafile_url, 'w') as file:
	file.write('var bulatestdataurl="'+args.bufile_url+bu_filename+'.gz"')
	
#
# Move the files to the S3 buckets
#
if (args.s3dryrun==0):
	# Copy the bu pointer file to S3 bucket
	logger.info('Writing bu_datafile full url '+str(bu_datafile_url)+' to S3 bucket '+str(args.bupointer_s3bucket))
	subprocessoutput=subprocess.run(["aws s3 cp "+bu_datafile_url+' '+args.bupointer_s3bucket+'bu-latest-data-pointer.js'], shell=True)
	logger.info(subprocessoutput)

	# Compress the bu data file
	logger.info('Compressing '+str(bu_local_filename))
	subprocessoutput=subprocess.run(['gzip -f '+bu_local_filename], shell=True)
	logger.info(subprocessoutput)
	
	# Copy the gzipped javascript data file to bu datafiles S3 bucket
	logger.info('Copying zipped bu file '+str(bu_local_filename)+' to S3 bucket '+str(args.bufile_s3bucket))
	subprocessoutput=subprocess.run(["aws s3 cp "+bu_local_filename+'.gz'+' '+args.bufile_s3bucket+bu_filename+'.gz --content-encoding gzip'], shell=True)
	logger.info(subprocessoutput)
	
	# Copy the ulampoints file to the bu datafiles S3 bucket
	logger.info('Copying bu-ulampoints file '+str(bu_ulampoints_local_filename)+' to S3 bucket '+str(args.bufile_s3bucket))
	subprocessoutput=subprocess.run(["aws s3 cp "+bu_ulampoints_local_filename+' '+args.bufile_s3bucket+bu_ulampoints_filename], shell=True)
	logger.info(subprocessoutput)

logger.info('ECMWF script finished')