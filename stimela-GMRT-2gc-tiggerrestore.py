import stimela
import time, os, sys

#I/O
INPUT = 'input'
MSDIR = 'msdir'

MS = '26_019_12MAY2014.LTA_RRLL.RRLLFITS.MS'
PREFIX = 'GMRT_325MHZ'

# Fields
GCAL = '2'
TARGET = '3'
BPCAL = '0' # 3C286
LABEL = "LH_2gc_tigger_restore"

# Reference antenna
REFANT = '7'
SPW = '0:21~225'

# Image parameters

npixno = 5120
trimno = 4096
cellarcsec = 1.5

# Calibration tables

OUTPUT = "output_%s"%LABEL

stimela.register_globals()

######################################################################################################

recipe = stimela.Recipe('GMRT LH 2gc reduction script', ms_dir=MSDIR)

recipe.add('cab/casa_plotms', 'plot_amp_uvdist_RR', 
           {
               "vis"           :   MS,
               "field"         :   TARGET,
               "correlation"   :   'RR',
               "timerange"     :   '',
               "antenna"       :   '',
               "xaxis"         :   'uvwave',
               "xdatacolumn"   :   'corrected',
               "yaxis"         :   'amp',
               "ydatacolumn"   :   'corrected',
               "coloraxis"     :   'corr',
               "plotfile"      :   PREFIX+'-fld1-amp_vs_uvdist.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_amp_uvdist_RR:: Plot amplitude vs uvdistance for target field')

recipe.add('cab/casa_plotms', 'plot_amp_uvdist_LL', 
           {
               "vis"           :   MS,
               "field"         :   TARGET,
               "correlation"   :   'LL',
               "timerange"     :   '',
               "antenna"       :   '',
               "xaxis"         :   'uvwave',
               "xdatacolumn"   :   'corrected',
               "yaxis"         :   'amp',
               "ydatacolumn"   :   'corrected',
               "coloraxis"     :   'corr',
               "plotfile"      :   PREFIX+'-fld1-amp_vs_uvdist.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_amp_uvdist_LL:: Plot amplitude vs uvdistance for target field')


## Clean-Mask-Clean
 
imname0 = PREFIX + 'image0'

recipe.add('cab/wsclean', 'image_target_field_r0', 
           {
               "msname"        :   MS,
               "field"         :   TARGET,
               "channelrange"  :   [25,220],               #Other channels don't have any data   
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               "nwlayers"  : 128,
               "minuvw-m"  : 100.0,
               "maxuvw-m"  : 15000.0,
               "clean_iterations"  :   5000,
               #"gain"          : 0.05,
               #"threshold"     : 0.00003, #Jy
               "mgain"         :   0.9,
               "auto-threshold":   5, # Shallow clean
               "prefix"        :   '%s:output' %(imname0),
           },
    input=INPUT,
    output=OUTPUT,
    label="image_target_field_r0:: Image target field first round")

maskname0 = PREFIX + 'mask0.fits'

recipe.add('cab/cleanmask', 'mask0', 
           {
               "image"  : '%s-image.fits:output' %(imname0),
               "output" : '%s:output' %(maskname0),
               "dilate" : False,
               "sigma"  : 25,
           },
    input=INPUT,
    output=OUTPUT,
    label='mask0:: Make mask')

imname1 = PREFIX + 'image1'     

recipe.add('cab/wsclean', 'image_target_field_r1', 
           {
               "msname"        :   MS,
               "field"         :   TARGET,
               "channelrange"  :   [25,220],               #Other channels don't have any data   
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               "nwlayers"  : 128,
               "minuvw-m"  : 100.0,
               "maxuvw-m"  : 15000.0,
               "clean_iterations"  :   5000,
               #"gain"          : 0.05,
               "mgain"         :   0.9,
               #"threshold"     : 0.00003, #Jy
               "fitsmask"      :   '%s:output' %(maskname0),
               "auto-threshold":   5,  # Shallow clean
               "prefix"        :   '%s:output' %(imname1),
           },
    input=INPUT,
    output=OUTPUT,
    label="image_target_field_r1:: Image target field second round")


lsm0 = PREFIX + '-LSM0'

# Source finding for initial model
recipe.add("cab/pybdsm", "extract_init_model", 
           {
               "image"             :  '%s-image.fits:output' %(imname1),
               "outfile"           :  '%s:output'%(lsm0),
               "thresh_pix"        :  25,
               "thresh_isl"        :  15,
               "port2tigger"       :  True,
           },
           input=INPUT, output=OUTPUT,
           label="extract_init_model:: Make initial model from pre-selfcal image")


############################################################################

# Copy CORRECTED_DATA to DATA, ****   so we can start selfcal

########################################################################


recipe.add("cab/msutils", "move_corrdata_to_data", 
           {
               "command"           : "copycol",
               "msname"            : MS,
               "fromcol"           : "CORRECTED_DATA",
               "tocol"             : "DATA",
           },
        input=INPUT, output=OUTPUT,
        label="move_corrdata_to_data::msutils")

# Add bitflag column. To keep track of flagsets.
 
recipe.add("cab/msutils", "msutils", 
           {
               'command'    : 'prep',
               'msname'     : MS,
           },
    input=INPUT, output=OUTPUT,
    label="prepms::Adds flagsets")

# Not used currently.

recipe.add("cab/flagms", "backup_initial_flags", 
           {
               "msname"        : MS,
               "flagged-any"   : "legacy+L",
               "flag"          : "legacy",
           },
        input=INPUT, output=OUTPUT,
        label="backup_initial_flags:: Backup selfcal flags")

# First selfcal round

recipe.add("cab/calibrator", "calibrator_Gjones_subtract_lsm0", 
           {
               "skymodel"           : "%s.lsm.html:output"%(lsm0),
               "msname"             : MS,
               "threads"            : 16,
               "column"             : "DATA",
               "output-data"        : "CORR_RES", # Corr_Data (gain applied) - Model in CORRECTED_DATA column
               "Gjones"             : True,
               "Gjones-solution-intervals" : [18,10], # Ad-hoc right now, subject to change (18 time slot ~ 5 min, 10 channel)
               "correlations"       :  '2x2, diagonal terms only', # Added  
               "Gjones-matrix-type" : "GainDiagPhase", # Support class to handle a set of subtiled gains in the form of diagonal G matrices with phase-only solutions
               "make-plots"         : False,
               "DDjones-smoothing-intervals" : 1,
               "Gjones-ampl-clipping"  :   True,
               "Gjones-ampl-clipping-low"  :   0.15,
               "Gjones-ampl-clipping-high"  :   3.5,
               "Gjones-thresh-sigma" :  5,
               "Gjones-chisq-clipping" : False,
               "tile-size"          : 512,
               "field-id"           : int(TARGET),
               "save-config"        : "selfcal_1st_round",
           },
           input=INPUT, output=OUTPUT,
           label="calibrator_Gjones_subtract_lsm0:: Calibrate and subtract LSM0")

imname2 = PREFIX + "image2"

recipe.add('cab/wsclean', 'image_target_field_r2', 
           {
               "msname"        :   MS,
               "field"         :   TARGET,
               "channelrange"  :   [25,220],       
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               "nwlayers"  : 128,
               "minuvw-m"  : 100.0,
               "maxuvw-m"  : 15000.0,       
               "clean_iterations"  :   5000,
               #"gain"          : 0.05,
               "mgain"         :   0.9,
               #"threshold"     : 0.00003, #Jy       
               "auto-threshold"     : 5,
               "prefix"        : "%s:output"%(imname2),
           },
        input=INPUT, output=OUTPUT,
        label="image_target_field2::Image the target field after 1st phase selfcal")

# Get a better image by cleaning with masks, two rounds. 

maskname1 = PREFIX + "mask1.fits"

recipe.add('cab/cleanmask', 'mask1', 
           {
               #    "image"  : "pre-self-cal--image.fits:output",
               "image"  : '%s-image.fits:output' %(imname2),
               "output" : '%s:output' %(maskname1),
               "dilate" : False,
               "sigma"  : 20,
           },
    input=INPUT,
    output=OUTPUT,
    label='mask1:: Make mask on selfcal image')


imname3 = PREFIX + "-image3"

recipe.add('cab/wsclean', 'image_target_field3', 
           {
               "msname"        :   MS,
               "field"         :   TARGET,
               "channelrange"  :   [25,220],
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               "nwlayers"  : 128,
               "minuvw-m"  : 100.0,
               "maxuvw-m"  : 15000.0, 
               "clean_iterations"  :   5000,
               #"gain"          : 0.05,
               "mgain"         :   0.9,
               "auto-threshold"     : 5,
               "prefix"        : '%s:output' %(imname3),
               "fitsmask"      : '%s:output' %(maskname1),
           },
        input=INPUT, output=OUTPUT,
        label="image_target_field3::Image the target field after 1st p selfcal with masks")

lsm1 = PREFIX + '-LSM1'

# Run pybdsm on the new image. Do 2nd phase selfcal. 

recipe.add("cab/pybdsm", "extract_pselfcal_model", 
           {
               "image"             :  '%s-image.fits:output' %(imname3),
               "outfile"           :  '%s:output'%(lsm1),
               "thresh_pix"        :  20,
               "thresh_isl"        :  10,
               "port2tigger"       :  True,
               "clobber"           : True,
           },
           input=INPUT, output=OUTPUT,
           label="extract_pselfcal1_model:: Make new model from 1st selfcal image")


recipe.add("cab/flagms", "unflag_pselfcalflags", 
           {
               "msname"             : MS,
               "unflag"             : "FLAG0",
           },
          input=INPUT, output=OUTPUT,
          label="unflag_pselfcalflags:: Unflag phase selfcal flags")


# Stitch LSM 0 & 1 together

lsm2 = PREFIX + '-LSM2'

recipe.add("cab/tigger_convert", "stitch_lsms1", 
           {
               "input-skymodel" :   "%s.lsm.html:output" % lsm0,
               "output-skymodel" :   "%s.lsm.html:output" % lsm2,
               "append" :   "%s.lsm.html:output" % lsm1,
           },
        input=INPUT, output=OUTPUT,
        label="stitch_lsm01::Create master lsm file")

####################################################

# Second phase selfcal round

######################################################

recipe.add("cab/msutils", "move_corrdata_to_data", 
           {
               "command"           : "copycol",
               "msname"            : MS,
               "fromcol"           : "CORRECTED_DATA",
               "tocol"             : "DATA",
           },
        input=INPUT, output=OUTPUT,
        label="move_corrdata_to_data::msutils")


recipe.add("cab/calibrator", "calibrator_Gjones_subtract_lsm1", 
           {
               "skymodel"           : "%s.lsm.html:output"%(lsm1),
               "msname"             : MS,
               "threads"            : 16,
               "column"             : "DATA",
               "output-data"        : "CORR_RES", # Corr_Data (gain applied) - Model
               "Gjones"             : True,
               "Gjones-solution-intervals" : [12,10], # Ad-hoc right now, subject to change (12 time slot ~ 3 min, 10 channel)
               "correlations"       :  '2x2, diagonal terms only', # Added  
               "Gjones-matrix-type" : "GainDiagPhase",
               "make-plots"         : False,
               "DDjones-smoothing-intervals" : 1,
               "Gjones-ampl-clipping"  :   True,
               "Gjones-ampl-clipping-low"  :   0.15,
               "Gjones-ampl-clipping-high"  :   3.5,
               "Gjones-thresh-sigma" :  5,
               "Gjones-chisq-clipping" : False,
               "tile-size"          : 512,
               "field-id"           : int(TARGET),
               "save-config"        : "selfcal_2nd_round",
           },
           input=INPUT, output=OUTPUT,
           label="calibrator_Gjones_subtract_lsm1:: Calibrate and subtract LSM1")

imname4 = PREFIX + "image4"

recipe.add('cab/wsclean', 'image_target_field_r4', 
           {
               "msname"        :   MS,
               "field"         :   TARGET,
               "channelrange"  :   [25,220],       
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               "nwlayers"  : 128,
               "minuvw-m"  : 100.0,
               "maxuvw-m"  : 15000.0,       
               "clean_iterations"  :   5000,
               #"gain"          : 0.05,
               "mgain"         :   0.9,
               #"threshold"     : 0.00003, #Jy       
               "auto-threshold"     : 5,
               "prefix"        : "%s:output"%(imname4),
           },
        input=INPUT, output=OUTPUT,
        label="image_target_field4::Image the target field after 2nd phase selfcal")

# Get a better image by cleaning with masks, two rounds of selfcal. 

maskname2 = PREFIX + "mask2.fits"

recipe.add('cab/cleanmask', 'mask2', 
           {
               #    "image"  : "pre-self-cal--image.fits:output",
               "image"  : '%s-image.fits:output' %(imname4),
               "output" : '%s:output' %(maskname2),
               "dilate" : False,
               "sigma"  : 15,
           },
    input=INPUT,
    output=OUTPUT,
    label='mask2:: Make mask on 2nd selfcal image')


imname5 = PREFIX + "-image5"

recipe.add('cab/wsclean', 'image_target_field5', 
           {
               "msname"        :   MS,
               "field"         :   TARGET,
               "channelrange"  :   [25,220],
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               "nwlayers"  : 128,
               "minuvw-m"  : 100.0,
               "maxuvw-m"  : 15000.0, 
               "clean_iterations"  :   5000,
               #"gain"          : 0.05,
               "mgain"         :   0.9,
               "auto-threshold"     : 5,
               "prefix"        : '%s:output' %(imname5),
               "fitsmask"      : '%s:output' %(maskname2),
           },
        input=INPUT, output=OUTPUT,
        label="image_target_field5::Image the target field after 2nd p selfcal with masks")

lsm3 = PREFIX + '-LSM3'

# Run pybdsm on the new image. Do amp & phase selfcal. 

recipe.add("cab/pybdsm", "extract_pselfcal_model", 
           {
               "image"             :  '%s-image.fits:output' %(imname5),
               "outfile"           :  '%s:output'%(lsm3),
               "thresh_pix"        :  10,
               "thresh_isl"        :  5,
               "port2tigger"       :  True,
               "clobber"           : True,
           },
           input=INPUT, output=OUTPUT,
           label="extract_pselfcal2_model:: Make new model from 2nd selfcal image")


recipe.add("cab/flagms", "unflag_pselfcalflags", 
           {
               "msname"             : MS,
               "unflag"             : "FLAG0",
           },
          input=INPUT, output=OUTPUT,
          label="unflag_pselfcalflags:: Unflag phase selfcal flags")


# Stitch LSM 2 & 3 together

lsm4 = PREFIX + '-LSM4'

recipe.add("cab/tigger_convert", "stitch_lsms1", 
           {
               "input-skymodel" :   "%s.lsm.html:output" % lsm2,
               "output-skymodel" :   "%s.lsm.html:output" % lsm4,
               "append" :   "%s.lsm.html:output" % lsm3,
           },
        input=INPUT, output=OUTPUT,
        label="stitch_lsm23::Create master lsm file")


#############################################################

# Third selfcal round with amp & phase on the residual data

############################################################

recipe.add("cab/msutils", "move_corrdata_to_data", 
           {
               "command"           : "copycol",
               "msname"            : MS,
               "fromcol"           : "CORRECTED_DATA",
               "tocol"             : "DATA",
           },
        input=INPUT, output=OUTPUT,
        label="move_corrdata_to_data::msutils")

recipe.add("cab/calibrator", "calibrator_Gjones_subtract_lsm3", 
           {
               "skymodel"           : "%s.lsm.html:output"%(lsm3),
               "msname"             : MS,
               "threads"            : 16,
               "column"             : "DATA",
               "output-data"        : "CORR_RES", # Final residual data
               "Gjones"             : True,
               "Gjones-solution-intervals" : [20,20], # Ad-hoc right now, subject to change (20 time slot ~ 5.33 min, 20 channel)
               #"correlations"       :  '2x2, diagonal terms only', # Added  
               "Gjones-matrix-type" : "Gain2x2", # amp & phase. 
               "make-plots"         : False,
               "DDjones-smoothing-intervals" : 1,
               "Gjones-ampl-clipping"  :   True, # True
               "Gjones-ampl-clipping-low"  :   0.15,
               "Gjones-ampl-clipping-high"  :   3.5,
               "Gjones-thresh-sigma" :  10, # 5
               "Gjones-chisq-clipping" : False,
               "tile-size"          : 512,
               "field-id"           : int(TARGET),
               "save-config"        : "selfcal_3rd_round",
           },
           input=INPUT, output=OUTPUT,
           label="calibrator_Gjones_subtract_lsm3:: Calibrate and subtract LSM3")


####################################################

# Check the Residual visibility by Imaging

####################################################

imname6 = PREFIX + "resimage"

recipe.add('cab/wsclean', 'image_restarget_field_r6', 
           {
               "msname"        :   MS,
               "field"         :   TARGET,
               "channelrange"  :   [25,220],        
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               "nwlayers"  : 128,
               "minuvw-m"  : 100.0,
               "maxuvw-m"  : 15000.0,        
               "clean_iterations"  :   5000,
               #"gain"          : 0.05,
               "mgain"         :   0.9,
               #"threshold"     : 0.00003, #Jy        
               "auto-threshold"     : 5,
               "prefix"        : "%s:output"%(imname6),
           },
        input=INPUT, output=OUTPUT,
        label="image_restarget_field6::Image the residual visibility after amp & phase selfcal")

################################################################################################
# Use tigger restore to pruce the final image

imname7 = PREFIX + "final"

recipe.add("cab/tigger_restore", "restore_image", 
           {
               "input-image"   :  '%s-image.fits:output' %(imname6), # res img
               "input-skymodel"   : lsm4,
               "output-image"   :  '%s-image.fits:output' %(imname7),
               
           },
          input=INPUT, output=OUTPUT,
          label="restore_image:: Restore model sky to residual image")


####################################################################################################

tstart = time.time()

'''
t = time.time()

recipe.run([
    "plot_amp_uvdist_RR",
    "plot_amp_uvdist_LL",
    "image_target_field_r0",
    "mask0", 
    "image_target_field_r1",
    "extract_init_model",
    "prepms",
    "backup_initial_flags",
    "move_corrdata_to_data",
    "prepms",
    "backup_initial_flags",
    "calibrator_Gjones_subtract_lsm0",
])

t1 = time.time() - t   

print "\n2gc self-cal1 done in %.2f sec\n" %(t1)
'''


#######################################################################################
# Copy MS after 1st round of self-cal

MS_SELF1 = MS[:-3] + '.SELFCAL1.MS' 

os.system("cp -r %s/%s %s/%s" %(MSDIR, MS, MSDIR, MS_SELF1))

#####################################################################################

t = time.time()

recipe.run([
    "image_target_field2",
    "mask1",
    "image_target_field3",
    "extract_pselfcal1_model",
    "unflag_pselfcalflags",
    "stitch_lsm01",
    "move_corrdata_to_data",
    "calibrator_Gjones_subtract_lsm1",
])

t2 = time.time() - t   

print "\n2gc self-cal2 done in %.2f sec\n" %(t2)

#######################################################################################
# Copy MS after 2nd round of self-cal

MS_SELF2 = MS[:-3] + '.SELFCAL2.MS' 

os.system("cp -r %s/%s %s/%s" %(MSDIR, MS, MSDIR, MS_SELF2))

sys.exit()
#####################################################################################

t = time.time()

recipe.run([
    "image_target_field4",
    "mask2",
    "image_target_field5",
    "extract_pselfcal2_model",
    "unflag_pselfcalflags",
    "stitch_lsm23",
    "move_corrdata_to_data",
    "calibrator_Gjones_subtract_lsm3",
    "image_restarget_field6",
    "restore_image",
])

t3 = time.time() - t  

print "\n2gc self-cal3 done in %.2f sec\n" %(t3)

#######################################################################################
# Copy MS after 3rd round of self-cal. It has the residual data

MS_SELF3 = MS[:-3] + '.SELFCAL3.MS' 

os.system("cp -r %s/%s %s/%s" %(MSDIR, MS, MSDIR, MS_SELF3))

#####################################################################################




