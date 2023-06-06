# StudioProject
Studio (**St**reet **U**sers **Di**rect **O**bservation) is an ongoing PhD project at Polytechnique Montréal 
developed under the supervision of [Prof. Nicolas Saunier](http://n.saunier.free.fr/saunier/) 
and [Dr. Owen Waygood](https://www.polymtl.ca/expertises/en/waygood-owen).
The aim of this project is to clean, validate, and analyze the trajectory of street users obtained from 
[TrafficIntelligence](https://trafficintelligence.confins.net) (TI), 
an open-source video analysis project developed at Polytechnique Montréal. 
TI uses video analytics to track and identify street users.

The Studio application offers a set of tools for evaluating urban streets in terms of their three primary 
functions: transit, access, and place. This evaluation is done through direct observation of street users. 
To this end, the Studio application employs a comprehensive framework, detailed in this 
[link](https://www.mdpi.com/2071-1050/14/12/7184),
as its underlying scheme to analyze the trajectories extracted through TI. Based on the framework, 
two spatial units including *screenline* and *zone* are applied in this application to capture the movement of 
street users. 

The StudioProject application is primarily designed for manipulating and analyzing the output trajectories 
of TI. However, it also offers tools for manual data collection through the review of video files.

The Studio application comprises two primary windows: a video player and an observation panel.

## Video player
The primary purpose of the video player window is to facilitate the review of collected videos for 
extracting necessary information. Additionally, this window provides various tools for tasks such as 
creating new projects, opening existing projects, and generating a mask file.

To store relevant details related to a study, such as the video's name, current time, application window 
size and position, database file name, metadata file path, and other associated information, users can 
save them in an XML file named project file with a *.prj extension. This project file allows users to 
preserve their work settings and conveniently reopen the application with the same configuration at a 
later time. 

The following image presents a snapshot of the video player window in the Studio application.

![Video player](https://github.com/Abbas-Shmz/StudioProject/blob/main/images/Studio_Video-player.jpg)

![Panel_1](https://github.com/Abbas-Shmz/StudioProject/blob/main/images/Studio_Panel_01.jpg)

![Panel_2](https://github.com/Abbas-Shmz/StudioProject/blob/main/images/Studio_Panel_02.jpg)

![Plot](https://github.com/Abbas-Shmz/StudioProject/blob/main/images/Studio_Plot.jpg)

![Table](https://github.com/Abbas-Shmz/StudioProject/blob/main/images/Studio_Table.jpg)

Icons made by <a href="https://www.flaticon.com/authors/freepik" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon"> www.flaticon.com</a>
