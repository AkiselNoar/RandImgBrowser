requires PyQt5

browse images in one or multiple folders
hotkeys :
- right arrow : next image
- left arrow : previous image
- space : pause / unpause slideshow
- delete : delete current image
- 's' : move image
- 'n' : rename image

arguments:
- list of image path
- list of folder path (allimage in folders will be added to the slideshow)
- text files (to search image listed)

options :
- -txxx set slideshow timesplit  to xxx milliseconds (default: 10_000)
- -i infinite mode to reload at the end of the slideshow
- -p start paused
- -r recursive on listed folders
- default sorting is accordigly to the positionnal argument order
-- -s to sort images before slideshow
-- -m to shuffle images before slideshow

right click to crop
