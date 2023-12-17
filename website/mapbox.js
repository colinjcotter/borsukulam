


//
// Initialization of variables
//

var expanded = false
var map,map2 
var spinnerdiv = document.getElementById('spinner');  // Used for the spinner that appears when updating the time at which data is being shown


//
// Show the debug stuff if in the config
//
if (debugmode == 1){
var debugdiv = document.getElementById('debugdiv');  
debugdiv.style.display = 'block';
}


var spinnerdiv = document.getElementById('spinner');  // Used for the spinner that appears when updating the time at which data is being shown
spinnerdiv.style.display = 'inline-block';


//
// Load the bu file
//

let scriptEle0 = document.createElement("script");
scriptEle0.setAttribute("src", bu_latest_pointer);

scriptEle0.onload = function () {
let scriptEle = document.createElement("script");
scriptEle.setAttribute("src", bulatestdataurl);  
document.body.appendChild(scriptEle);
};

document.body.appendChild(scriptEle0);




//
// Event to hide arrow when user has finished scrolling
//
const scrollableDiv = document.getElementById("blurb");
var arrow = document.getElementById('arrow');
var blurb = document.getElementById('blurb');
scrollableDiv.addEventListener('scroll', function() {
if ((scrollableDiv.scrollTop+scrollableDiv.offsetHeight)>scrollableDiv.scrollHeight-10)
	{
	arrow.style.display = 'none'
	}
}
)

//
// Initialization of mapbox variables
//

const el1 = document.createElement('div');
el1.className = 'marker';
const el2 = document.createElement('div');
el2.className = 'marker2';
const el3 = document.createElement('div');
el3.className = 'marker';
const el4 = document.createElement('div');
el4.className = 'marker2';


marker1 = new mapboxgl.Marker(el1)
marker2 = new mapboxgl.Marker(el2)
marker3 = new mapboxgl.Marker(el3)
marker4 = new mapboxgl.Marker(el4)


var latitudeLine = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [-180, 0], // Replace YOUR_LATITUDE with the desired latitude
          [180, 0]
        ]
      }
    }
  ]
};

const popup = new mapboxgl.Popup({
	className: 'popup',
	closeButton: false,
	closeOnClick: false
  });
  
const popup2 = new mapboxgl.Popup({
	className: 'popup2',
	closeButton: false,
	closeOnClick: false
  });

// Other global variables
var currenttimestep, currenttimestepindex	// These need to be renamed.  Could we even remove them?
var automaticupdates = true	// Set to true in normal circumstances so data will update every minute.  
var  popup_location, popup2_location  // global variables that store the location of the two popups.  I guess with better programming these could be removed

window.onload = function () { mapBoxInit(); }




		

    

	   
function mapBoxInit() 
	{    
	//
	// Initialization of the maps; this is run once when window is opened
	//
	
	
	// Show the spinner for 2 seconds.  Not really needed but I think good UI as it may appear later
	spinnerdiv.style.display = 'inline-block';
	setTimeout( ()=> {spinnerdiv.style.display = 'none';} , 500);


	//
	// Check if the mapboxaccesstoken is set, else show an error
	// Todo: should probably quit after this
	//
	
	if (typeof mapboxaccesstoken === typeof undefined)
	{
	console.log('loading disable message')
	var disableddiv = document.getElementById('disabledmessage');
	disableddiv.style.visibility = 'visible'
	}
  
  	//
	// set mapbox access token
	//
	
	mapboxgl.accessToken = mapboxaccesstoken;

	
	//
	// define the maps
	//
	
	if (debug_skipmaps ==0)
	{
		map = new mapboxgl.Map({
		container: 'map',
		maxZoom: 12, 
		minZoom: 0,
		zoom: 0,
		center: [260, 0],
		style: mapboxstyle,
		projection: 'globe',
		attributionControl: false
		});
  
		// define the second map
		map2 = new mapboxgl.Map({
		container: 'map2',
		maxZoom: 12, 
		minZoom: 0,
		zoom: 0,
		center: [80, 0],
		style: mapboxstyle,
		projection: 'globe',
		hash: false,
		attributionControl: false
		});
	}
	
		const v1 = new mapboxgl.LngLatBounds(
	new mapboxgl.LngLat(0, 0),
	new mapboxgl.LngLat(180, 0),
	new mapboxgl.LngLat(90, 0),
	new mapboxgl.LngLat(270, 0),    
	);
	map.fitBounds(v1, {maxZoom: 0.8})
	map2.fitBounds(v1, {maxZoom: 0.8})
	 	
	//
	// Add localization of the maps
	//

	const language = new MapboxLanguage();
	map.addControl(language);
	const language2 = new MapboxLanguage();
	map2.addControl(language2);

   	// 
	// these two global variables are being used to keep track of the popup locations
	// they should not really be used in this way but it is fine for now
	//
	
	popup_location= {'lat': 50, 'lng':-80}
	popup2_location = get_antipodal(popup_location)
	
	//
	// initialize the correct timestep to use from the data we have
	//
	ulamlist = bu.ulamlist
	currenttimestepindex = calculatetimestep(new Date())
	currenttimestep = bu.ulamlist[currenttimestepindex][0]
	refreshupdatedtime()

	//
	// set timer to run every minute to update the timestep as needed
	//
	setInterval(updatetime, 60*1000);

	//
	// calculate the ulam points for the first time
	//
	
	ulam1  = new mapboxgl.LngLat(bu.ulamlist[currenttimestepindex][1][1],bu.ulamlist[currenttimestepindex][1][0])
	ulam2  = get_antipodal(ulam1)

	 map.on('load', () => {

	 	
	 	// Add equator line	
		 map.addSource('latitude-line', {
		  'type': 'geojson',
		  'data': latitudeLine
		});
	
			map.addLayer({
		  'id': 'latitude-line',
		  'type': 'line',
		  'source': 'latitude-line',
		  'layout': {
			'line-join': 'round',
			'line-cap': 'round'
		  },
		  'paint': {
			'line-color': 'black', // Change the color as desired
			'line-width': 0.25,
			'line-dasharray': [1, 4],
		  }
		});
	 	
	 	


	
	 	// Add the markers
		 marker1.setLngLat(ulam1).addTo(map);	
		 marker2.setLngLat(ulam2).addTo(map);
		 
		// Update the popups
		popup.setLngLat([popup_location.lng,popup_location.lat]).addTo(map);
	 	updatepopuptexts()
		 
		 spinnerdiv.style.display = 'none';
		 })
   
   	// Now do exactly the same for map2
	map2.on('load', () => {
	
	
	 // Add the equator
		map2.addSource('latitude-line', {
	  'type': 'geojson',
	  'data': latitudeLine
	});
	
		map2.addLayer({
	  'id': 'latitude-line',
	  'type': 'line',
	  'source': 'latitude-line',
	  'layout': {
		'line-join': 'round',
		'line-cap': 'round'
	  },
	  'paint': {
		'line-color': 'black', // Change the color as desired
		'line-width': 0.25,
		'line-dasharray': [1, 4],
	  }
	});
	



		 	// Add the markers

	 marker3.setLngLat(ulam1).addTo(map2);	
	 marker4.setLngLat(ulam2).addTo(map2);	  
	 spinnerdiv.style.display = 'none';   		
	 
	 // Update the popups
	 popup2.setLngLat([popup2_location.lng,popup2_location.lat]).addTo(map2);
	 updatepopuptexts()
	})

	// Add zoom and rotation controls to the maps.
	map.addControl(new mapboxgl.NavigationControl({showCompass: false}),'top-left');

// map.addControl(new MapboxInspect({
//     
//    showInspectButton: true,
// showMapPopup: true,
//   backgroundColor: '#000',
//       renderPopup: function(features) {
//           console.log(JSON.stringify(features), undefined, 2);
//             console.log(features);
//     //return '<h1> test 1:'+features[0].properties.Name + '</h1>';
//           return '<pre>'+JSON.stringify(features[0].properties, undefined, 2) + '</pre>';
//   }
//   }
// ));



	//
	// Setup the fullscreen and slider buttons
	//

	class MapboxGLButtonControl {
	  constructor({
		className = "",
		title = "",
		id = "",
		eventHandler = evtHndlr
	  }) {
		this._id = id;
		this._className = className;
		this._title = title;
		this._eventHandler = eventHandler;
	  }

	  onAdd(map) {
		this._btn = document.createElement("button");
		this._btn.className = "mapboxgl-ctrl-icon" + " " + this._className;
		this._btn.type = "button";
		this._btn.id = this._id;
		this._btn.title = this._title;
		this._btn.onclick = this._eventHandler;

		this._container = document.createElement("div");
		this._container.className = "mapboxgl-ctrl-group mapboxgl-ctrl";
		this._container.appendChild(this._btn);

		return this._container;
	  }

	  onRemove() {
		this._container.parentNode.removeChild(this._container);
		this._map = undefined;
	  }
	}


		const expander = new MapboxGLButtonControl({
		id: "sliderbutton",
	  title: "Toggle sidebar",
	  className: "expander-button",
	  eventHandler: handleexpand
	});

		const fullscreen = new MapboxGLButtonControl({
		id: "fullscreenbutton",
		className: "fullscreen-button",
	  title: "Toggle full screen",
	  eventHandler: toggleFullscreen
	});

	// Better to just not have this on safari
	if (
	  document.fullscreenEnabled || /* Standard syntax */
	  document.webkitFullscreenEnabled || /* Safari */
	  document.msFullscreenEnabled/* IE11 */
	) {
	map2.addControl(fullscreen, "top-right");
	document.addEventListener("fullscreenchange", fullscreenchanged);
	}

	map2.addControl(expander, "top-right");



		map.addControl(new mapboxgl.AttributionControl(), 'top-right');
		
		//
		// coordination between the position and scroll of the two maps and updating of the text of the popups
		//
		var disable = false;
		
		map.on("move", function () {
		if (!disable) {
		  var center = map.getCenter();
		  var zoom = map.getZoom();
		  var pitch = map.getPitch();
		  var bearing = map.getBearing();
		  disable = true;
		  var antipodal = get_antipodal(center)

		  map2.setCenter(antipodal); 
		  map2.setPitch(pitch);
		  map2.setZoom(zoom);
		  map2.setBearing(bearing);
		  disable = false;
		  updatepopuptexts()
		}
		})


	map2.on("move", function () {
	if (!disable) {
	  var center = map2.getCenter();
	  var zoom = map2.getZoom();
	  var pitch = map2.getPitch();
	  var bearing = map2.getBearing();
	  disable = true;

	  var antipodal = get_antipodal(center)
	  map.setCenter(antipodal); 
	  map.setZoom(zoom);
	  map.setPitch(pitch);
	  map.setBearing(bearing);
	  disable = false;
	  updatepopuptexts()
	}
	})
  
  
  	//
	// Show the popups when the cursor moves over each of the maps
	//
	
	map.on('mousemove', (e) => {
		popup_location=e.lngLat; 		  	
		popup2_location=get_antipodal(e.lngLat);
		popup.setLngLat(popup_location)
		popup2.setLngLat(popup2_location)
		updatepopuptexts()	
		});
		
		map.on('touchstart', (e) => {
		popup_location=e.lngLat; 		  	
		popup2_location=get_antipodal(e.lngLat);
		popup.setLngLat(popup_location)
		popup2.setLngLat(popup2_location)
		updatepopuptexts()	
		});


	map2.on('mousemove', (e) => {	
		popup2_location=e.lngLat; 		  	
		popup_location=get_antipodal(popup2_location);
		popup.setLngLat(popup_location)
		popup2.setLngLat(popup2_location)
		updatepopuptexts()	
		});


	map2.on('touchstart', (e) => {	
		popup2_location=e.lngLat; 		  	
		popup_location=get_antipodal(popup2_location);
		popup.setLngLat(popup_location)
		popup2.setLngLat(popup2_location)
		updatepopuptexts()	
		});

}
    

