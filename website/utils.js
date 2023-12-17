//
// Utility functions that do not involve the user interface
//


function get_antipodal(p)
	{
	//
	// Returns anitpodal point of a point p
	//
	var antilat = -p.lat
	if (p.lng > 0){
		var antilng = (180 - p.lng)*-1}
	else 
	  {var antilng = (-180 - p.lng)*-1	
	}
	return {lat: antilat, lng: antilng}	
	}
	

	
function getclimatevariables(p)
	{	
	// 
	// Gets the temperature and pressure at a point p
	// Assumes the correct currenttimestep for the time
	// Also returns a textlabel in html to use in the popup
	// Note this is hardcoded for a grid size of 0.4
	//
	lat = p.lat
	lng = p.lng



	//
	// Adjust the lat and long to reflect the lat/lng grid structure
	//
	var x = (-lat+90)%180    
	var y =(lng+180)%360	
	if (y<0){ y=y+360}
	if (x<0){x=x+180}


	// get the ll grid coordinate (i,j) wrapping correctly
	var i = Math.floor(y/0.4)
	if (i==900){ i=0 } 

	var j = Math.floor(x/0.4)
	if (j==450){ j=0}  

	// get the ur grid coordinate (ip,jp) wrapping correctly
	var ip = i+1
	var jp = j+1	
	if (ip==900){ ip=0 } 
	if (jp==450){ jp=0 } 



	// get the distance to the grid coordinate
	var a = x/0.4-j
	var b = y/0.4-i


	// temperature and pressure
	//var t = bu.t_initial
	//var p = bu.p_initial



	// decide on the number of decimal places to round to
	zoom = map.getZoom();

	var temp_decimals
	var pressure_decimals
	var coordinate_decimals
	if (zoom<2)
		{temp_decimals=1;pressure_decimals=2;coordinate_decimals=1 }
	else if (zoom<3)
		{temp_decimals=2;pressure_decimals=2;coordinate_decimals=2 }
	else if (zoom<4)
		{temp_decimals=3;pressure_decimals=3;coordinate_decimals=3}
	else if (zoom<5)
		{temp_decimals=3; pressure_decimals=3;coordinate_decimals=4 }
	else
		{temp_decimals=3; pressure_decimals=3;coordinate_decimals=5 }


	var temp_initial,temp_final
	var t = bu.t_initial
	var p = bu.p_initial
	// calculate the temperature at initial time in data source
	var temp_initial = (1-b)*((1-a)*t[j][i] + a*t[jp][i])  + b*((1-a)*t[j][ip] + a*t[jp][ip])
	var pressure_initial = (1-b)*((1-a)*p[j][i] + a*p[jp][i])  + b*((1-a)*p[j][ip] + a*p[jp][ip])

	var pressure_initial,pressure_final
	t = bu.t_final
	p = bu.p_final
	// calculate the pressure at final time in data source
	var temp_final = (1-b)*((1-a)*t[j][i] + a*t[jp][i])  + b*((1-a)*t[j][ip] + a*t[jp][ip])
	var pressure_final = (1-b)*((1-a)*p[j][i] + a*p[jp][i])  + b*((1-a)*p[j][ip] + a*p[jp][ip])

	// interpolate the temperature and pressure at the right time between the initial and final times
	var temp,pressure
	var delta = (currenttimestep-bu.initial_timestep)/(bu.final_timestep-bu.initial_timestep)
	temp = delta * temp_final + (1- delta)* temp_initial
	pressure = delta * pressure_final + (1- delta)* pressure_initial


	// convert to desired units
	temp=temp-273.15 // convert to centigrade			
	pressure = pressure/1000

	// get the textlabel to display as html	
	//popuplabel =  'temperature: ' + String(temp.toFixed(temp_decimals))+'\u{00B0}C<br> pressure: ' + String(pressure.toFixed(pressure_decimals)) +'kPa'
	
	popuplabel =  '<localized-text key="temperature"></localized-text>: ' + String(temp.toFixed(temp_decimals))+'\u{00B0}C<br> <localized-text key="pressure"></localized-text>: ' + String(pressure.toFixed(pressure_decimals)) +'kPa'
	
	popuplabel =  popuplabel +'<br>'+'<localized-text key="latitude"></localized-text>: ' + String(lat.toFixed(coordinate_decimals)) + '\u{00B0}'+'<br>'+ '<localized-text key="longitude"></localized-text>: ' +String(lng.toFixed(coordinate_decimals))+'\u{00B0}'

	return {temp: temp.toFixed(temp_decimals), pressure: pressure.toFixed(pressure_decimals),popuplabel: popuplabel}
	
	}  



function calculatetimestep(now)
	{
	//
	// Work out the best timestep to use from the data we have available based on time now
	// If there are none then it falls back to older stored data, and stops automatic time updates
	//
	
	ds_date = new Date(bu.ds_datetime+'Z')
	difference = (now - ds_date)/1000 // measured in seconds
	
	filtered_ulamlist = ulamlist.filter((u)=>
	{
	return u[0]<=difference
	}
	)


	if (filtered_ulamlist.length==0)
		{
		// load fall back file and take the earliest time in that file.  This has not been tested
		console.log('cannot find any relevant times in the bufile; falling back')
		fallback()
		}
	else
	
		newindex = filtered_ulamlist.length-1
			
	return newindex	
}

function roundToNearestMinute(date) 
{
	//
	// Rounds a date to the nearest minute
	//
    var coeff = 1000 * 60 * 1; // <-- Replace {5} with interval
    return new Date(Math.round(date.getTime() / coeff) * coeff);
};


function fallback(){
	console.log('falling back to older data; this should not happen; is the system clock wrong?')
	automaticupdates = false
	
	let scriptEle2 = document.createElement("script");
	scriptEle2.setAttribute("src",fallbackbufile);
	document.head.appendChild(scriptEle2);
	newindex =0
	console.log('newindex',newindex)
}


