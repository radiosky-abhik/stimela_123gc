# stimela_123gc

Flagging, calibration and imaging using stimela.

The current scripts are used to flag, calibrate & image GMRT data. The
scripts use a mixture of software like AoFlagger, CASA, MeqTrees,
WSClean to analyse the data sets.

The aim is to use 1gc (Direction Independent), 2gc (self-calibration) and 3gc (Direction Dependent) calibrations all together to improve the dynamic range or quality of the images. 

We are working on the 3gc part where the differential gain part is going through tests. The bigger aim is to incorporate
or model the effects ionosphere and the primary beam of the telescope as a part of direction dependent calibration.
