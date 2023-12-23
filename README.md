# borsukulam

A small library to compute the location of antipodal points on the sphere that have the two of the same atmospheric data (e.g. temperature and pressure).

Used to compute the points on julius-ross.com/Borsuk-Ulam

## Prerequisites

```python
pip install scipy numpy ecmwf-opendata xarray json logging
```

## Getting data

This library has been tested on ECMWF open-data.   The following should get you a sample data file to work with

```python
from ecmwf.opendata import Client
client = Client()
result  = client.retrieve(step=[0,6],type="cf",param = ["2t","msl","sp"],target="data.grib2",)

```

## Finding Ulampoints

The following will give you the ulampoints for all pairs of parameters in the ds file and all steps (so in the above example at 0h and 6h, and each pair among '2t','msl','sp')

```python
import findulam
ds = xr.open_dataset('data.grib2',engine='cfgrib')
ulampoints = findulam.ulampoints(ds)
print(ulampoints)
```

You can select particular parameters, for instance the following gives ulampoints at step 0h and 6h for temperature and pressure

```python
ulampoints = findulam.ulampoints(ds.sel(param = ['2t','msl']))
```

You can specify the steps (and if they are not in the ds file then xarray interpolation is used).  

```python
# Return the ulampoints at step 1h and 3h
steplist = [numpy.timedelta64(1*3600000000000,'ns'), numpy.timedelta64(2*3600000000000,'ns')]
ulampoints = findulam.ulampoints(ds,step=steplist)
```

# ecmwfscrape.py

This is a script to scrape data from ECMWF and run findulam.ulampoints and create some javascript files to be used on julius-ross/Borsuk-Ulam.  It is unlikley to be useful to anybody else

# /website

If you want to have a local copy of the website julius-ross/Bosruk-Ulam the files are here.  Edit mapbox.js to include your own mapbox token.  Other things can be changed in config.js (e.g. the style)