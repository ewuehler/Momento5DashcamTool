# Momento 5 Dashcam Tool

I have found the Momento 5 Dashcam app - for both Mac or Windows - essentially useless for me...  All I want is to pull some video clips and it takes an *eternity* to launch the app and find the file I want to export.  Since I generally know about the time I want to extract, I wanted a simple command line tool to pull out the bits...  This got me headed down the rabbit hole that is AVI file formats.  So I figured I could build a tool to pull out the contents I want for a time range I want and pull the video bits together without launching any app - AVI is a standard format, right?


**WORK IN PROGRESS**

The [parse_video.py](parse_video.py) tool  parses out the AVI into the associated bits. 


### In the interim...

If you have `ffmpeg` installed and are using either Linux or Mac, you can use [convert2mp4.sh](convert2mp4.sh) to take a single file and export a video (with the picture-in-picture) for front and rear cameras.  Depending if you record with the rear camera reversed or not, it may need a little tweaking.  I found this much more efficient that trying to load the videos from the custom app that you can download.
