const budirectory = 'https://d1aipxdgb0yxq7.cloudfront.net/'  // Directory for regularly updated bu files; to be removed at a later point in time
const bu_latest_pointer = 'https://bursk-ulam-pointer.s3.us-east-2.amazonaws.com/bu-latest-data-pointer.js'
const fallbackbufile = 'https://s3.us-east-2.amazonaws.com/julius-ross.com/Borsuk-Ulam/bu-fallback.js.gz' // static fallback bu file that is known to work
const mapboxstyle = 'mapbox://styles/juliusross/clq4afnan01a801qm38y428rb'
const debugmode = 0  // Set to 1 to allow manual moving of time
const debug_skipmaps =0 // Set to 1 to skip loading the maps for speed