# borsukulam

A small library to compute the location of antipodal points on the sphere that have the two of the same atmospheric data (e.g. temperature and pressure).

Example use can be found at http://julius-ross.com/Borsuk-Ulam

## Prerequisites

```python
pip install scipy numpy ecmwf-opendata xarray logging cfgrib
```

## Getting data

This library has been tested on ECMWF open-data.   The following should get you a sample data file to work with

```python
from ecmwf.opendata import Client
client = Client()
result  = client.retrieve(step=[0,6],type="cf",param = ["2t","msl","sp"],target="data.grib2")

```


## Loading the data source

```python
import findulam
import xarray as xr
ds = xr.open_dataset('data.grib2',engine='cfgrib')

<xarray.Dataset>
Dimensions:            (step: 2, latitude: 451, longitude: 900)
Coordinates:
    number             int64 ...
    time               datetime64[ns] ...
  * step               (step) timedelta64[ns] 00:00:00 06:00:00
    heightAboveGround  float64 ...
  * latitude           (latitude) float64 90.0 89.6 89.2 ... -89.2 -89.6 -90.0
  * longitude          (longitude) float64 -180.0 -179.6 -179.2 ... 179.2 179.6
    valid_time         (step) datetime64[ns] ...
    meanSea            float64 ...
    surface            float64 ...
Data variables:
    t2m                (step, latitude, longitude) float32 ...
    msl                (step, latitude, longitude) float32 ...
    sp                 (step, latitude, longitude) float32 ...
Attributes:
    GRIB_edition:            2
    GRIB_centre:             ecmf
    GRIB_centreDescription:  European Centre for Medium-Range Weather Forecasts
    GRIB_subCentre:          0
    Conventions:             CF-1.7
    institution:             European Centre for Medium-Range Weather Forecasts
    history:                 2023-12-23T20:38 GRIB to CDM+CF via cfgrib-0.9.1...
```

The library is expecting only 3 indexed coordinates named step, longtitude and latitude.  If more are present in the datasource file then select along those coordinates using ds.sel(...)

## Finding Ulampoints

The following will find the ulampoints for all pairs of parameters in the ds file and all steps (so in the above example at 0h and 6h, and each pair among '2t','msl','sp')


```python
ula mpoints = findulam.ulampoints(ds)
print(ulampoints)

<xarray.Dataset>
Dimensions:            (step: 2, variable_1: 3, variable_2: 3)
Coordinates:
  * step               (step) timedelta64[ns] 00:00:00 06:00:00
  * variable_1         (variable_1) <U3 't2m' 'msl' 'sp'
  * variable_2         (variable_2) <U3 't2m' 'msl' 'sp'
    number             int64 ...
    heightAboveGround  float64 ...
    meanSea            float64 ...
    surface            float64 ...
Data variables:
    ulampoint_lat      (step, variable_1, variable_2) object None ... None
    ulampoint_lon      (step, variable_1, variable_2) object None ... None
    optimizeresult     (step, variable_1, variable_2) object None ... None
    time               datetime64[ns] ...
    
# Select the data corresponding to the variables temperature and pressure
ulampoints = ulampoints.sel(variable_1='msl',variable_2='t2m')

## The actual time of the first computed ulampoint
ulampoints.time.data + ulampoints.step.data[0]
numpy.datetime64('2023-12-23T12:00:00.000000000')

## The location time of the first computed ulampoint
[ulampoints.ulampoint_lat.data[0],ulampoints.ulampoint_lon.data[0]]  # sample output; will be None if numerical method is not succesful within tolerance
[-9.632231990420905, 13.866959712623363]  #  sample output

## The optimization results of the computation for the first ulampoint (sample output)
 ulampoints.optimizeresult.data[0]

 message: Optimization terminated successfully.
 success: True
     fun: 6.535813980708355e-26
       x: [-9.632e+00  1.387e+01]
     nit: 150
    nfev: 4569


```

If you want to compute just for particular parameters select using xarray first:

```python
ds0 = ds[['msl','t2m']]
ulampoints = findulam.ulampoints(ds0)
```

You can also specify the steps (and if they are not in the ds file then xarray interpolation is used).  

```python
## Return the ulampoints at step 1h and 3h
import numpy
steplist = [numpy.timedelta64(1*3600000000000,'ns'), numpy.timedelta64(2*3600000000000,'ns')]
ulampoints = findulam.ulampoints(ds,steps=steplist)
print(ulampoints)

<xarray.Dataset>
Dimensions:            (step: 2, variable_1: 3, variable_2: 3)
Coordinates:
  * step               (step) timedelta64[ns] 01:00:00 02:00:00
  * variable_1         (variable_1) <U3 't2m' 'msl' 'sp'
  * variable_2         (variable_2) <U3 't2m' 'msl' 'sp'
    number             int64 ...
    heightAboveGround  float64 ...
    meanSea            float64 ...
    surface            float64 ...
Data variables:
    ulampoint_lat      (step, variable_1, variable_2) object None ... None
    ulampoint_lon      (step, variable_1, variable_2) object None ... None
    optimizeresult     (step, variable_1, variable_2) object None ... None
    time               datetime64[ns] ...

```
## Verbosity

If using the python interpretor you can see the logging produced by findulam with the following (change INFO to DEBUG for even more)

```
import logging
import sys
log = logging.getLogger()
log.setLevel(logging.INFO)
stream = logging.StreamHandler(sys.stdout)
stream.setLevel(logging.INFO)
log.addHandler(stream)
```

# ecmwfscrape.py

This is a script to scrape data from ECMWF and run findulam.ulampoints and create some javascript files to be used on julius-ross.com/Borsuk-Ulam.  It is unlikley to be useful to anybody else

# /website

If you want to have a local copy of the website julius-ross.com/Bosruk-Ulam the files are here.  Edit mapbox.js to include your own mapbox token.  Other things can be changed in config.js (e.g. the mapbox style)