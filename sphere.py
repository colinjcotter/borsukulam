import plotly.plotly as py
import numpy as np           
from scipy.io import netcdf  
from mpl_toolkits.basemap import Basemap
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    with netcdf.netcdf_file('test.nc', 'r') as f:
#        print(f.history)
#        print(f.dimensions)
#        print(f.variables)
        lon = f.variables['lon'][::]       # copy longitude as list
        lat = f.variables['lat'][::-1]     # invert the latitude vector -> South to North

        #olr = f.variables['plev'][0,::-1,:] # olr= outgoing longwave radiation
        olr = f.variables['plev'][::] # olr= outgoing longwave radiation
    f.fp
    
# Shift 'lon' from [0,360] to [-180,180]
tmp_lon = np.array([lon[n]-360 if l>=180 else lon[n] 
                   for n,l in enumerate(lon)])  # => [0,180]U[-180,2.5]

i_east, = np.where(tmp_lon>=0)  # indices of east lon
i_west, = np.where(tmp_lon<0)   # indices of west lon
lon = np.hstack((tmp_lon[i_west], tmp_lon[i_east]))  # stack the 2 halves

# Correspondingly, shift the olr array
#olr_ground = np.array(olr)
#olr = np.hstack((olr_ground[:,i_west], olr_ground[:,i_east]))

from numpy import pi, sin, cos

def degree2radians(degree):
    #convert degrees to radians
    return degree*pi/180

def mapping_map_to_sphere(lon, lat, radius=1):
    #this function maps the points of coords (lon, lat) to points onto the  sphere of radius radius
    
    lon=np.array(lon, dtype=np.float64)
    lat=np.array(lat, dtype=np.float64)
    lon=degree2radians(lon)
    lat=degree2radians(lat)
    xs=radius*cos(lon)*cos(lat)
    ys=radius*sin(lon)*cos(lat)
    zs=radius*sin(lat)
    return xs, ys, zs


# Make shortcut to Basemap object, 
# not specifying projection type for this example
m = Basemap() 


# Functions converting coastline/country polygons to lon/lat traces
def polygons_to_traces(poly_paths, N_poly):
    ''' 
    pos arg 1. (poly_paths): paths to polygons
    pos arg 2. (N_poly): number of polygon to convert
    '''
    # init. plotting list
    lons=[]
    lats=[]

    for i_poly in range(N_poly):
        poly_path = poly_paths[i_poly]
        
        # get the Basemap coordinates of each segment
        coords_cc = np.array(
            [(vertex[0],vertex[1]) 
             for (vertex,code) in poly_path.iter_segments(simplify=False)]
        )
        
        # convert coordinates to lon/lat by 'inverting' the Basemap projection
        lon_cc, lat_cc = m(coords_cc[:,0],coords_cc[:,1], inverse=True)
    
        
        lats.extend(lat_cc.tolist()+[None]) 
        lons.extend(lon_cc.tolist()+[None])
        
       
    return lons, lats

# Function generating coastline lon/lat 
def get_coastline_traces():
    poly_paths = m.drawcoastlines().get_paths() # coastline polygon paths
    N_poly = 91  # use only the 91st biggest coastlines (i.e. no rivers)
    cc_lons, cc_lats= polygons_to_traces(poly_paths, N_poly)
    return cc_lons, cc_lats

# Function generating country lon/lat 
def get_country_traces():
    poly_paths = m.drawcountries().get_paths() # country polygon paths
    N_poly = len(poly_paths)  # use all countries
    country_lons, country_lats= polygons_to_traces(poly_paths, N_poly)
    return country_lons, country_lats


# Get list of of coastline, country, and state lon/lat 

cc_lons, cc_lats=get_coastline_traces()
country_lons, country_lats=get_country_traces()

#concatenate the lon/lat for coastlines and country boundaries:
lons=cc_lons+[None]+country_lons
lats=cc_lats+[None]+country_lats

xs, ys, zs=mapping_map_to_sphere(lons, lats, radius=1.01)# here the radius is slightly greater than 1 
                                                         #to ensure lines visibility; otherwise (with radius=1)
                                                         # some lines are hidden by contours colors



colorscale=[[0.0, '#313695'],
 [0.07692307692307693, '#3a67af'],
 [0.15384615384615385, '#5994c5'],
 [0.23076923076923078, '#84bbd8'],
 [0.3076923076923077, '#afdbea'],
 [0.38461538461538464, '#d8eff5'],
 [0.46153846153846156, '#d6ffe1'],
 [0.5384615384615384, '#fef4ac'],
 [0.6153846153846154, '#fed987'],
 [0.6923076923076923, '#fdb264'],
 [0.7692307692307693, '#f78249'],
 [0.8461538461538461, '#e75435'],
 [0.9230769230769231, '#cc2727'],
 [1.0, '#a50026']]


clons=np.array(lon.tolist()+[180], dtype=np.float64)
clats=np.array(lat, dtype=np.float64)
clons, clats=np.meshgrid(clons, clats)

XS, YS, ZS=mapping_map_to_sphere(clons, clats)

nrows, ncolumns=clons.shape
OLR=np.zeros(clons.shape, dtype=np.float64)
OLR[:, :ncolumns-1]=np.copy(np.array(olr,  dtype=np.float64))
OLR[:, ncolumns-1]=np.copy(olr[:, 0])

text=[['lon: '+'{:.2f}'.format(clons[i,j])+'<br>lat: '+'{:.2f}'.format(clats[i, j])+
        '<br>W: '+'{:.2f}'.format(OLR[i][j]) for j in range(ncolumns)] for i in range(nrows)]

sphere=dict(type='surface',
            x=XS, 
            y=YS, 
            z=ZS,
            colorscale=colorscale,
            surfacecolor=OLR,
            cmin=-20, 
            cmax=20,
            colorbar=dict(thickness=20, len=0.75, ticklen=4, title="test"),
            text=text,
            hoverinfo='text')

noaxis=dict(showbackground=False,
            showgrid=False,
            showline=False,
            showticklabels=False,
            ticks='',
            title='',
            zeroline=False)

layout3d=dict(title='Outgoing Longwave Radiation Anomalies<br>Dec 2017-Jan 2018',
              font=dict(family='Balto', size=14),
              width=800, 
              height=800,
              scene=dict(xaxis=noaxis, 
                         yaxis=noaxis, 
                         zaxis=noaxis,
                         aspectratio=dict(x=1,
                                          y=1,
                                          z=1),
                         camera=dict(eye=dict(x=1.15, 
                                     y=1.15, 
                                     z=1.15)
                                    )
            ),
            paper_bgcolor='rgba(235,235,235, 0.9)'  
           )
             
fig=dict(data=[sphere, boundaries], layout=layout3d)
py.sign_in('empet', 'api_key')
py.iplot(fig, filename='radiation-map2sphere')
