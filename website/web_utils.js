//
// Utility functions that concern the user interface (including some that affect the maps)
//

function fullscreenchanged(event) {
  // document.fullscreenElement will point to the element that
  // is in fullscreen mode if there is one. If there isn't one,
  // the value of the property is null.
  if (document.fullscreenElement) {
    fullscreenbutton.classList.add('shrink-button');
    fullscreenbutton.classList.remove('fullscreen-button');
  } else {
    fullscreenbutton.classList.remove('shrink-button');
    fullscreenbutton.classList.add('fullscreen-button');
  }
}



function toggleFullscreen() {
// Function to go fullscreen and back
  const element = document.documentElement;
  var fullscreenbutton = document.getElementById('fullscreenbutton');
  
  if (!document.fullscreenElement) {
    if (element.requestFullscreen) {
      element.requestFullscreen();
    } else if (element.mozRequestFullScreen) {
      element.mozRequestFullScreen();
    } else if (element.webkitRequestFullscreen) {
      element.webkitRequestFullscreen();
    } else if (element.msRequestFullscreen) {
      element.msRequestFullscreen();
    }

  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if (document.mozCancelFullScreen) {
      document.mozCancelFullScreen();
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen();
    } else if (document.msExitFullscreen) {
      document.msExitFullscreen();
    }
  }
}


function handleexpand()
// Handler for the expanding and collapsing of the explaination text
{ 
	var container = document.getElementById('container');
	var smallarrow = document.getElementById('sliderbutton');
	 // Add the class to trigger the animation
	 if (expanded==false) {
		container.classList.remove('expand-animation');
		container.classList.remove('collapse-animation');
		container.classList.add('expand-animation');
		
		//Resize maps on animation end
		function onAnimationEnd() {
			map.resize()
			map2.resize()
    	}
    	container.addEventListener('animationend', onAnimationEnd);		
		expanded = true
		smallarrow.classList.add('fliparrow');

	 	// The following runs map.resize every 10ms for 6 seconds to smooth out the animation
		counter =0

		const intervalId = setInterval(() => {
			map.resize()
			map2.resize()
			counter++;
			if (counter >= 6000 / 100) {
				clearInterval(intervalId); 
			  }
			}, 10);
	
		}
	 else
	 {	
		container.classList.remove('expand-animation');
		container.classList.remove('collapse-animation');
		container.classList.add('collapse-animation');
		expanded = false
		//Resize maps on animation end
		function onAnimationEnd() {
			map.resize()
			map2.resize()
    	}
    	container.addEventListener('animationend', onAnimationEnd);
		
		
		
		smallarrow.classList.remove('fliparrow');

	
		counter =0
		// The following runs map.resize every 10ms for 6 seconds to smooth out the animation
		const intervalId = setInterval(() => {
			  map.resize()
			  map2.resize()
			  counter++;
			  if (counter >= 6000 / 100) {
				clearInterval(intervalId); // Stop the interval after 2 seconds
			  }
			}, 10);
		}
}



function refreshupdatedtime()
	{
	//
	// Updates the html that shows when the data was last updated
	//
	  const options = {
	  dateStyle: 'full',
	  timeStyle: 'long'
	};
	// Take the ds_datetime and add to it the current timestep (in seconds)
	lastupdateddate = new Date(bu.ds_datetime+'Z')
	lastupdateddate.setSeconds(lastupdateddate.getSeconds() + currenttimestep)
	// Then round to the nearest minute
	lastupdateddate=roundToNearestMinute(lastupdateddate)
	// Now update the html
	lastupdateparagraph = document.getElementById('lastupdated');
	text = Intl.DateTimeFormat(navigator.language,options).format(lastupdateddate)
	lastupdateparagraph.innerText=text
}




function manuallyupdatetime()
	{
	//
	// Function that allows manual adjustement of the time
	// Used for testing purposes only
	//
	console.log('updating timestep manually')
	manualdate = document.getElementById('myText').value
	manualdate = Date.parse(manualdate)
	newindex = calculatetimestep(manualdate)
	if (newindex!=currenttimestepindex)
	{
	console.log('found new timestep when updating manually')
	currenttimestepindex = newindex
	currenttimestep = bu.ulamlist[currenttimestepindex][0]
	updatetimestep()
	}
	
}

function updatetime()
	{
	//
	// Function that is run periodically to use the most recent time data available
	//
	if(automaticupdates==true){
		now = new Date()
		now = Date.parse(now)
		newindex = calculatetimestep(now)
		if (newindex!=currenttimestepindex)
		{
		currenttimestepindex = newindex
		currenttimestep = bu.ulamlist[currenttimestepindex][0]
		updatetimestep()
	}
	}
	
}

function updatetimestep()
	{ 
	//
	// Show the spinner div, update markers and popuplabels.  Usually called when time is updated
	//
  	spinnerdiv.style.display = 'inline-block';
  	
  	setTimeout(movemarkers, 2000);
	
	function movemarkers(){
		var counter=0
		var timestep=20
		var startLngLat,endLngLat

		function animateMarker() {
			/* 
			Update the data to a new position 
			based on the animation timestamp. 
			The divisor in the expression `timestamp / 1000` 
			controls the animation speed.
			*/
			a = counter/timestep
			b = 1-a
			var llA = new mapboxgl.LngLat(a*ulam1.lng+b*startLngLatA.lng, a*ulam1.lat+b*startLngLatA.lat);
			marker1.setLngLat(llA.wrap());
			marker3.setLngLat(llA.wrap());
		
			//marker1.setLngLat([a*ulam1.lng+b*startLngLatA.lng, a*ulam1.lat+b*startLngLatA.lat]);
			//marker3.setLngLat([a*ulam1.lng+b*startLngLatA.lng, a*ulam1.lat+b*startLngLatA.lat]);
		
			marker2.setLngLat([a*ulam2.lng+b*startLngLatB.lng, a*ulam2.lat+b*startLngLatB.lat]);
			marker4.setLngLat([a*ulam2.lng+b*startLngLatB.lng, a*ulam2.lat+b*startLngLatB.lat]);
			counter = counter +1
			// Request the next frame of the animation.
			if (counter<timestep+1)
				{requestAnimationFrame(animateMarker);}
			}
 

	
		 ulam1  = new mapboxgl.LngLat(bu.ulamlist[currenttimestepindex][1][1],bu.ulamlist[currenttimestepindex][1][0])
		 ulam2  = get_antipodal(ulam1)
		 startLngLatA = marker1.getLngLat()
		 startLngLatB = marker2.getLngLat()
 
		 requestAnimationFrame(animateMarker)
		 updatepopuptexts()
		 
		refreshupdatedtime()
  		spinnerdiv.style.display = "none";
		} 
		}
		


function updatepopuptexts()
	{
	// 
	// Update the text in the two popups based on their location on the map
	//
	
	var popup_climate = getclimatevariables(popup_location)
	var popup2_climate = getclimatevariables(popup2_location)

	popup.setHTML(popup_climate.popuplabel);
	popup2.setHTML(popup2_climate.popuplabel);


	//Highlight all popups if cursor is over ulam point
	const elements = document.querySelectorAll('.mapboxgl-popup-content');
	if ((popup_climate.temp  == popup2_climate.temp) && (popup_climate.pressure == popup2_climate.pressure))
	{
	elements.forEach((element)=>element.classList.remove("highlight_pressure"));
	elements.forEach((element)=>element.classList.remove("highlight_temp"));
	elements.forEach((element)=>element.classList.add("highlight"));
	}
	else if ((popup_climate.temp  == popup2_climate.temp))
	{
		elements.forEach((element)=>element.classList.remove("highlight"));
	elements.forEach((element)=>element.classList.remove("highlight_pressure"));
	elements.forEach((element)=>element.classList.add("highlight_temp"));
	}
	else if ((popup_climate.pressure  == popup2_climate.pressure))
	{
	elements.forEach((element)=>element.classList.remove("highlight"));
	elements.forEach((element)=>element.classList.remove("highlight_temp"));
	elements.forEach((element)=>element.classList.add("highlight_pressure"));
	}
	else
	{
	elements.forEach((element)=>element.classList.remove("highlight"));
	elements.forEach((element)=>element.classList.remove("highlight_pressure"));
	elements.forEach((element)=>element.classList.remove("highlight_temp"));
	}
		
}

