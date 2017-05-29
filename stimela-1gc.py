#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import ast
import os
import sys
import pyrap.tables as pt
import stimela
import time

INPUT = "input"
OUTPUT = "output"
MSDIR  = "msdir"

msname = "26_013_25aug2015_GMRT_16s.MS"
PREFIX = msname[:-3]

#SPW_phase_cal = "0:1100~6900" # centre band freqs
SPW_delay_cal = "0:50~435" # clip start and end of the band


# Calibration tables
PHASECAL_TABLE = PREFIX + '.G0:output'
GAINCAL_TABLE = PREFIX + '.G1:output'
FLUXCAL_TABLE = PREFIX + '.fluxscale:output'
BPASSCAL_TABLE = PREFIX + '.B0:output'
DELAYCAL_TABLE = PREFIX + '.K0:output'


LABEL = "GALSYN_1gc_reduction"

bandpass_cal = "0" # 3C48
phase_cal = "1" # 3C091
target = "2" # GALSYN

refant = "C03"
BADANT = 'W06' # Antenna 30

# Image parameters

npixno = 6144
trimno = 4096
cellarcsec = 4.5

############################################################################

# So that we can access GLOBALS pass through to the run command
stimela.register_globals()

recipe = stimela.Recipe("GMRT LH reduction script", ms_dir=MSDIR)

# Autoflagging (With Aoflagger) - This is supposed to flag RFI in the
# data - good to flag prior to starting the calibration process.

# Default AoFlagger

recipe.add('cab/autoflagger', 'aoflag_data', 
           {
               "msname"    :   msname,
               "column"    :   "DATA",
               "strategy"  :  "low_freq.rfis",
           },    
    input=INPUT,
    output=OUTPUT,    
    label='aoflag_data:: Flag DATA column')

# It is common for the array to require a small amount of time to
# settle down at the start of a scan. Consequently, it has become
# standard practice to flag the initial samples from the start of each
# scan. This is known as 'quack' flagging

recipe.add('cab/casa_flagdata', 'quack_flagging', 
           {
               "msname"           :   msname,
               "mode"         :   'quack',
               "quackinterval" :   30.0, # 0.5 min from begining
               "quackmode"     :   'beg',
           },
    input = INPUT,
    output = OUTPUT,
    label = 'quack_flagging:: Quack flagging')

# Flag the autocorrelations

recipe.add('cab/casa_flagdata', 'autocorr_flagging', 
           {
               "msname"           :   msname,
               "mode"          :   'manual',
               "autocorr"      :   True,
           },
    input = INPUT,
    output = OUTPUT,
    label = 'autocorr_flagging:: Autocorrelations flagging')

# Flag potentially pesky antennas

recipe.add('cab/casa_flagdata', 'antenna_flagging', 
           {
               "vis"           :   msname,
               "mode"          :   'manual',
               "antenna"       :   BADANT,      
           },
    input = INPUT,
    output = OUTPUT,
    label = 'antenna_flagging::Antenna flagging')

recipe.add("cab/casa_flagdata", "flag_bad_start_channels",
        {
            "msname"    :   msname,
            "mode"      :   "manual",
            "field"     :   '',
            "spw"       :   '0:0~15',
            "autocorr"  :   True,
        },
    	input=INPUT, output=OUTPUT,
        label="flag_bandstart:: Flag start of band")

recipe.add("cab/casa_flagdata", "flag_bad_end_channels",
        {
            "msname"    :   msname,
            "mode"      :   "manual",
            "field"     :   '',
            "spw"       :   '0:495~512',
            "autocorr"  :   True,
        },
    	input=INPUT, output=OUTPUT,
        label="flag_bandend:: Flag end of band")

#######################################

## 1GC Calibration

######################################

recipe.add('cab/casa_setjy', 'set_flux_scaling', 
           {
               "msname"           :   msname,
               "field"         :   bandpass_cal,
               "standard"      :   'Perley-Butler 2013',
               "usescratch"    :   False,
               "scalebychan"   :   True,
               "spw"           :   '',
            },
    input = INPUT,
    output = OUTPUT,
    label = 'set_flux_scaling:: Set flux density value for the amplitude calibrator')

recipe.add("cab/casa_gaincal", "init_phase_cal",
    {
        "msname"        :   msname,
        #"uvrange"       :  '>1klambda',  # Not using short baselines
        "caltable"      :   PHASECAL_TABLE,
        "field"         :   bandpass_cal,
        "refant"        :   refant,
        "gaintype"      :   'G',
        "calmode"       :   'p',
        "solint"        :   '85s',
        "minsnr"        :   3,
    },
    input=INPUT, output=OUTPUT,
    label="phase0:: Initial phase calibration")


recipe.add('cab/casa_gaincal', 'delay_cal', 
           {
               "msname"       :   msname,
               #"uvrange"       : '1~30klambda',       
               "caltable"  :   DELAYCAL_TABLE,
               "field"     :   bandpass_cal,
               "refant"    :   refant,
               "spw"       :   SPW_delay_cal,
               "gaintype"  :   'K',
               "solint"    :   'inf', #'5min',
               "combine"   :   'scan',
               "minsnr"    :   3, 
               "gaintable" :   [PHASECAL_TABLE],
           },

    input=INPUT,
    output=OUTPUT,
    label = 'delay_cal:: Delay calibration')


recipe.add("cab/casa_bandpass", "bandpass_cal",
    {   
        "msname"        :   msname, 
        #"uvrange"       : '1~30klambda', 
        "caltable"      :   BPASSCAL_TABLE,
        "field"         :   bandpass_cal,
        "spw"           :   '',
        "refant"        :   refant,
        "combine"       :   'scan',
        "solint"        :   'inf', #'5min'
        "bandtype"      :   'B',
        "solnorm"       :  True,
        "minblperant"   :   1,
        "minsnr"        :   3, 
        "gaintable"     :   [PHASECAL_TABLE, DELAYCAL_TABLE],
        "interp"       :   ['', ''],
    },
    input=INPUT, output=OUTPUT,
    label="bandpass:: First bandpass calibration")

###############################################################

# Plot bandpass_cal(BPASSCAL_TABLE) chan vs amp/phase 

recipe.add('cab/casa_plotcal', 'plot_bandpass_amp_R', 
           {
               "caltable"  :   BPASSCAL_TABLE,
               "poln"      :   'R',
               "xaxis"     :   'chan',
               "yaxis"     :   'amp',
               "subplot"   :  655,
               "iteration" : 'antenna',
               "showgui"   : False,
               "figfile"   :   PREFIX+'-B0-R-amp.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_bandpass_amp_R:: Plot bandpass table. AMP, R')

recipe.add('cab/casa_plotcal', 'plot_bandpass_amp_L', 
           {
               "caltable"  :   BPASSCAL_TABLE,
               "poln"      :   'L',
               "xaxis"     :   'chan',
               "yaxis"     :   'amp',
               "subplot"   :  655,
               "iteration" : 'antenna',
               "showgui"   : False,
               "figfile"   :   PREFIX+'-B0-L-amp.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_bandpass_amp_L:: Plot bandpass table. AMP, L')


recipe.add('cab/casa_plotcal', 'plot_bandpass_phase_R', 
           {
               "caltable"  :   BPASSCAL_TABLE,
               "poln"      :   'R',
               "xaxis"     :   'chan',
               "yaxis"     :   'phase',
               "subplot"   :  655,
               "iteration" : 'antenna',
               "showgui"   : False,
               "figfile"   :   PREFIX+'-B0-R-phase.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_bandpass_phase_R:: Plot bandpass table. PHASE, R')

recipe.add('cab/casa_plotcal', 'plot_bandpass_phase_L', 
           {
               "caltable"  :   BPASSCAL_TABLE,
               "poln"      :   'L',
               "xaxis"     :   'chan',
               "yaxis"     :   'phase',
               "subplot"   :  655,
               "iteration" : 'antenna',
               "showgui"   : False,
               "figfile"   :   PREFIX+'-B0-L-phase.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_bandpass_phase_L:: Plot bandpass table. PHASE, L')

###############################################################

recipe.add("cab/casa_gaincal", "main_gain_calibration",
    {
        "msname"        :   msname,
        #"uvrange"       : '1~30klambda', 
        "caltable"      :   GAINCAL_TABLE,
        "field"        :   "%s,%s"%(phase_cal, bandpass_cal),
        "spw"          :   '',
        "solint"       :   'inf',
        "refant"       :   refant,
        "gaintype"     :   'G',
        "calmode"      :   'ap',
        "solnorm"      :   False,
        "gaintable"    :   [DELAYCAL_TABLE,
                            BPASSCAL_TABLE],
        "interp"       :   ['', ''],
    },
    input=INPUT, output=OUTPUT,
    label="gaincal:: Gain calibration")

#############################################################

# Plot phasecal time vs phase

recipe.add('cab/casa_plotcal', 'plot_phasecal_phase_R', 
           {
               "caltable"  :   GAINCAL_TABLE,
               "poln"      :   'R',
               "xaxis"     :   'time',
               "yaxis"     :   'phase',
               "subplot"   :  655,
               "iteration" : 'antenna',
               "showgui"   : False,
               "figfile"   :   PREFIX+'-G1-R-phase.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_phasecal_phase_R:: Plot phasecal table. PHASE, R')


recipe.add('cab/casa_plotcal', 'plot_phasecal_phase_L', 
           {
               "caltable"  :   GAINCAL_TABLE,
               "poln"      :   'L',
               "xaxis"     :   'time',
               "yaxis"     :   'phase',
               "subplot"   :  655,
               "iteration" : 'antenna',
               "showgui"   : False,
               "figfile"   :   PREFIX+'-G1-L-phase.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_phasecal_phase_L:: Plot phasecal table. PHASE, L')

########################################

recipe.add("cab/casa_fluxscale", "casa_fluxscale",
    {
        "msname"        :   msname,
        "caltable"      :   GAINCAL_TABLE,
        "fluxtable"     :   FLUXCAL_TABLE,
        "reference"     :   [bandpass_cal],
        "transfer"      :   [phase_cal],
        "incremental"   :   False,
    },
    input=INPUT, output=OUTPUT,
    label="fluxscale:: Setting Fluxscale")

# Plot fluxcal table time vs phase

recipe.add('cab/casa_plotcal', 'plot_fluxcal_phase_R', 
           {
               "caltable"  :   FLUXCAL_TABLE,
               "poln"      :   'R',
               "xaxis"     :   'time',
               "yaxis"     :   'phase',
               "subplot"   :  655,
               "iteration" : 'antenna',
               "showgui"   : False,
               "figfile"   :   PREFIX+'-F1-R-phase.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_fluxcal_phase_R:: Plot fluxcal table. PHASE, R')


recipe.add('cab/casa_plotcal', 'plot_fluxcal_phase_L', 
           {
               "caltable"  :   FLUXCAL_TABLE,
               "poln"      :   'L',
               "xaxis"     :   'time',
               "yaxis"     :   'phase',
               "subplot"   :  655,
               "iteration" : 'antenna',
               "showgui"   : False,
               "figfile"   :   PREFIX+'-F1-L-phase.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_fluxcal_phase_L:: Plot fluxcal table. PHASE, L')

###########################

# Apply calibration to BPCAL

recipe.add('cab/casa_applycal', 'applycal_bp', 
    {
        "msname"      :    msname,
        "field"     :   bandpass_cal,
        "gaintable" :   [FLUXCAL_TABLE, DELAYCAL_TABLE, BPASSCAL_TABLE],
        "gainfield" :   ['','',bandpass_cal],
        "interp"    :   ['','','linear'],
        "spw"       :   '',
        #"applymode" : 'calonly', # does not take the flagging of gain snr into account
        "calwt"     :   [False],
        "parang"    :   False,
    },
    input=INPUT, output=OUTPUT,
    label='applycal_bp:: Apply calibration to Bandpass Calibrator')

# Apply calibration to GCAL

recipe.add('cab/casa_applycal', 'applycal_gcal', 
    {
        "msname"      :    msname,
        "field"     :   phase_cal,
        "gaintable" :   [FLUXCAL_TABLE, DELAYCAL_TABLE, BPASSCAL_TABLE],
        "gainfield" :   ['phase_cal','',''],
        "interp"    :   ['nearest','',''],
        "spw"       :   '',
        #"applymode" : 'calonly',
        "calwt"     :   [False],
        "parang"    :   False,
    },
    input=INPUT, output=OUTPUT,
    label='applycal_gcal:: Apply calibration to phase Calibrator')

# Apply calibration to TARGET

recipe.add('cab/casa_applycal', 'applycal_tar', 
    {
        "msname"      :    msname,
        "field"     :   target,
        "gaintable" :   [FLUXCAL_TABLE, DELAYCAL_TABLE, BPASSCAL_TABLE],
        "gainfield" :   ['phase_cal','',''],
        "interp"    :   ['nearest','',''],
        "spw"       :   '',
        #"applymode" : 'calonly',
        "calwt"     :   [False],
        "parang"    :   False,
    },
    input=INPUT, output=OUTPUT,
    label='applycal_tar:: Apply calibration to Target')

# Run AoFlagger on CORRECTED data

# Default AoFlagger

recipe.add('cab/autoflagger', 'aoflag_corrdata', 
           {
               "msname"    :   msname,
               "column"    :   "CORRECTED_DATA",
           },    
    input=INPUT,
    output=OUTPUT,    
    label='aoflag_corrdata:: Flag CORRECTED_DATA column')

# Plot bandpass_cal amp Vs phase

recipe.add('cab/casa_plotms', 'plot_amp_phase', 
           {
               "msname"           :   msname,
               "field"         :   bandpass_cal,
               "spw"           :   SPW_delay_cal,
               "correlation"   :   'RR',
               "timerange"     :   '',
               "antenna"       :   '',
               "xaxis"         :   'phase',
               "xdatacolumn"   :   'corrected',
               "yaxis"         :   'amp',
               "ydatacolumn"   :   'corrected',
               #"coloraxis"     :   'corr', # RR / LL
               "plotfile"      :   PREFIX+'-fld1-corrected-ampvsphase-RR.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_amp_phase_RR:: Plot amplitude vs phase')


recipe.add('cab/casa_plotms', 'plot_amp_phase', 
           {
               "msname"           :   msname,
               "field"         :   bandpass_cal,
               "spw"           :   SPW_delay_cal,
               "correlation"   :   'LL',
               "timerange"     :   '',
               "antenna"       :   '',
               "xaxis"         :   'phase',
               "xdatacolumn"   :   'corrected',
               "yaxis"         :   'amp',
               "ydatacolumn"   :   'corrected',
               #"coloraxis"     :   'corr', # RR / LL
               "plotfile"      :   PREFIX+'-fld1-corrected-ampvsphase-LL.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_amp_phase_LL:: Plot amplitude vs phase')

##########################################################################

# To inspect the target source data

# freq vs amp

recipe.add('cab/casa_plotms', 'plot_target_freq_amp_RR', 
           {
               "msname"           :   msname,
               "field"         :   target,
               "correlation"   :   'RR',
               "avgtime"       :  '1000', # sec
               "xaxis"         :   'freq',
               "xdatacolumn"   :   'corrected',
               "yaxis"         :   'amp',
               "ydatacolumn"   :   'corrected',
               "coloraxis"     :   'baseline', 
               "plotfile"      :   PREFIX+'-tar-freq-amp-RR.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_target_freq_amp_RR:: Plot target freq vs amp')


recipe.add('cab/casa_plotms', 'plot_target_freq_amp_LL', 
           {
               "msname"           :   msname,
               "field"         :   target,
               "correlation"   :   'LL',
               "avgtime"       :  '1000', # sec
               "xaxis"         :   'freq',
               "xdatacolumn"   :   'corrected',
               "yaxis"         :   'amp',
               "ydatacolumn"   :   'corrected',
               "coloraxis"     :   'baseline', 
               "plotfile"      :   PREFIX+'-tar-freq-amp-LL.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_target_freq_amp_LL:: Plot target freq vs amp')

# time vs amp

recipe.add('cab/casa_plotms', 'plot_target_time_amp_RR', 
           {
               "msname"           :   msname,
               "field"         :   target,
               "correlation"   :   'RR',
               "avgchannel"    :  '100', 
               "xaxis"         :   'time',
               "xdatacolumn"   :   'corrected',
               "yaxis"         :   'amp',
               "ydatacolumn"   :   'corrected',
               "coloraxis"     :   'baseline', 
               "plotfile"      :   PREFIX+'-tar-time-amp-RR.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_target_time_amp_RR:: Plot target time vs amp')


recipe.add('cab/casa_plotms', 'plot_target_time_amp_LL', 
           {
               "msname"           :   msname,
               "field"         :   target,
               "correlation"   :   'LL',
               "avgchannel"    :  '100',
               "xaxis"         :   'time',
               "xdatacolumn"   :   'corrected',
               "yaxis"         :   'amp',
               "ydatacolumn"   :   'corrected',
               "coloraxis"     :   'baseline', 
               "plotfile"      :   PREFIX+'-tar-time-amp-LL.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_target_time_amp_LL:: Plot target time vs amp')


############################################################################

# To see the First Image after 1gc

###########################################################################

recipe.add('cab/wsclean', 'image_target_field', 
           {
               "msname"        :   msname,
               "column"       : 'CORRECTED_DATA',
               "field"         :   target,
               "channelrange"  :   [15,495],
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               #"nwlayers"  : 128,
               #"minuvw-m"  : 100.0,
               #"maxuvw-m"  : 15000.0,
               "clean_iterations"  :   100000,
               "gain"          : 0.05,
               "mgain"         : 0.9, 
               #"joinchannels"  : True, # MFS
               #"channelsout"    : 3,
               #"fit-spectral-pol" : 4,
               #"multiscale"   : True, # MS
               #"taper-gaussian" : '2.3asec',
               "auto-threshold"     : 5,
               "prefix"        : LABEL+'-target',
               "no-update-model-required" : True,
           },
    input=INPUT,
    output=OUTPUT,
    label="image_target_field:: Image target field After 1gc")

# Diagnostic only: image bandpass

recipe.add('cab/wsclean', 'image_bandpass_field', 
           {
               "msname"        :   msname,
               "column"       : 'CORRECTED_DATA',
               "field"         : bandpass_cal,
               "channelrange"  :   [15,495],
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   2048,                   # Image size in pixels
               "trim"          :   1024,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               #"nwlayers"  : 128,
               #"minuvw-m"  : 100.0,
               #"maxuvw-m"  : 15000.0,
               "clean_iterations"  :   100000,
               "gain"          : 0.05,
               "mgain"         : 0.9, 
               #"joinchannels"  : True,
               #"channelsout"    : 3,
               #"multiscale"   : True,
               #"fit-spectral-pol" : 4,
               #"taper-gaussian" : '2.3asec',
               "auto-threshold"     : 5,
               "prefix"        : LABEL+'-bandpass',
               "no-update-model-required" : True,
           },
    input=INPUT,
    output=OUTPUT,
    label="image_bandpass_field:: Image bandpass After 1gc")

# Diagnostic only: image phase_cal

recipe.add('cab/wsclean', 'image_phasecal_field', 
           {
               "msname"        :   msname,
               "column"       : 'CORRECTED_DATA',
               "field"         :   phase_cal,
               "channelrange"  :   [15,495],
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   2048,                   # Image size in pixels
               "trim"          :   1024,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               #"nwlayers"  : 128,
               #"minuvw-m"  : 100.0,
               #"maxuvw-m"  : 15000.0,
               "clean_iterations"  :   100000,
               "gain"          : 0.05,
               "mgain"         : 0.9, 
               #"joinchannels" : True,# Combining multi-scale with multi-frequency 
               #"channelsout"  : 3,
               #"multiscale"   : True,
               #"fit-spectral-pol" : 4,
               #"taper-gaussian" : '2.3asec',
               "auto-threshold"     : 5,
               "prefix"        : LABEL+'-phasecal',
               "no-update-model-required" : True,
           },
    input=INPUT,
    output=OUTPUT,
    label="image_phasecal_field:: Image phasecal After 1gc")


t = time.time()

# w plots

recipe.run([
    "aoflag_data",
    "quack_flagging",
    "autocorr_flagging",
    "antenna_flagging",
    "flag_bandstart",
    "flag_bandend", 
    "set_flux_scaling", # setJy
    "phase0",
    "delay_cal",
    "bandpass", # bandpass
    "plot_bandpass_amp_R",
    "plot_bandpass_amp_L",
    "plot_bandpass_phase_R",
    "plot_bandpass_phase_L",
    "gaincal", # gaincal
    "plot_phasecal_phase_R",
    "plot_phasecal_phase_L",
    "fluxscale",
    "plot_fluxcal_phase_R",
    "plot_fluxcal_phase_L",
    "applycal_bp",
    "applycal_gcal",
    "applycal_tar",
    #"aoflag_corrdata",
    "plot_amp_phase_RR",
    "plot_amp_phase_LL", 
    "plot_target_freq_amp_RR",
    "plot_target_freq_amp_LL",
    "plot_target_time_amp_RR",
    "plot_target_time_amp_LL",
    "image_target_field",
    "image_bandpass_field",
    "image_phasecal_field",
])

print "1gc w plots done in %.2f sec" %(time.time() - t)

