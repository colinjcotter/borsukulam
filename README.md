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
ds = xr.open_dataset('data.grib2',engine='cfgrib')
```

## Finding Ulampoints

The following will give you the ulampoints for temperature and pressure at all the steps (so in the above example at 0h and 6h)

```python
import findulam
ds0= ds.sel(param = ['2t','msl'])
ulampoints = findulam.ulampoints(ds0)
print(ulampoints)
```

Alternatively you can find the ulam points for all pairs of parameters

```python
ulampoints = findulam.ulampoints(ds)
print(ulampoints)
```

Finally you can specify the steps (and if they are not in the file then xarray interpolation is used).  

```python
# Return the ulampoints at step 1h and 3h
steplist = [numpy.timedelta64(1*3600000000000,'ns'), numpy.timedelta64(2*3600000000000,'ns')]
ulampoints = findulam.ulampoints(ds,step=steplist)
```