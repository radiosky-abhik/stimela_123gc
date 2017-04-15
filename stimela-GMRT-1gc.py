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
OUTPUT = "output_1gc"
MSDIR  = "msdir"

msname = "26_019_12MAY2014.LTA_RRLL.RRLLFITS.MS"
PREFIX = msname[:-3]

SPW_phase_cal = "0:50~206" # centre band freqs
SPW_delay_cal = "0:21~225" # clip start and end of the band


# Calibration tables
PHASECAL_TABLE = PREFIX + '.G0:output'
AMPCAL_TABLE = PREFIX + '.G1:output'
FLUXCAL_TABLE = PREFIX + '.fluxscale:output'
BPASSCAL_TABLE = PREFIX + '.B0:output'
DELAYCAL_TABLE = PREFIX + '.K0:output'

LABEL = "LH_1gc_reduction"

rfi_mask_file = "rfi_mask.pickle"
strategy_file = "first_pass_meerkat_ar1.rfis"
bandpass_cal = "3C286"
amp_cal = "J1035+5628" 
phase_cal = "2" # J1035+5628
flux_cal = "0" # 3C286
target = "3" # LH_NORTH
cal_model = "3C48_C.im"
gain_cal = "2" # J1035+5628
refant = "7"
BADANT = '30,W06' # (W06: Antenna 30)

# Image parameters

npixno = 7168
trimno = 5120
cellarcsec = 1.5

############################################################################

# So that we can access GLOBALS pass through to the run command
stimela.register_globals()

recipe = stimela.Recipe("GMRT LH reduction script", ms_dir=MSDIR)

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
            "spw"       :   '0:0~09',
            "autocorr"  :   True,
        },
    	input=INPUT, output=OUTPUT,
        label="flag_bandstart:: Flag start of band")

recipe.add("cab/casa_flagdata", "flag_bad_end_channels",
        {
            "msname"    :   msname,
            "mode"      :   "manual",
            "field"     :   '',
            "spw"       :   '0:247~256',
            "autocorr"  :   True,
        },
    	input=INPUT, output=OUTPUT,
        label="flag_bandend:: Flag end of band")


# Autoflagging (With Aoflagger) - This is supposed to flag RFI in the
# data - good to flag prior to starting the calibration process.

recipe.add('cab/autoflagger', 'aoflag_data', 
           {
               "msname"    :   msname,
               "column"    :   "DATA",
               "strategy"  :  "325_rfi1.rfis",  
           },    
    input=INPUT,
    output=OUTPUT,    
    label='aoflag_data:: Flag DATA column')


recipe.add("cab/rfimasker", "mask_stuff",
    {
        "msname" : msname,
        "mask"   : rfi_mask_file,
    },
    input=INPUT, output=OUTPUT,
    label="mask::maskms")

#######################################

# Plot overview of the observation

recipe.add('cab/casa_plotms', 'plot_aflag_obsoverview', 
           {
               "msname"           :   msname,
               "selectdata"    : True,
               "correlation"    : 'RR,LL',
               "averagedata"   : True,
               "avgchannel"    : '16',
               "coloraxis"     : 'field',
               "plotfile"      :   PREFIX+'after_manual_flags.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_aflag_obsoverview:: Plot amplitude vs time')

# Plot amplitude vs uv distance

recipe.add('cab/casa_plotms', 'plot_amp_uvdist', 
           {
               "vis"           :   msname,
               "plotfile"      :   PREFIX + 'initial_amp_uvdist.png',
               "xaxis"         :   "uvdist",
               "yaxis"         :   "amp",
               "selectdata"    :    True,
               "correlation"   :   'RR,LL',
               "averagedata"   :   True,
               "avgchannel"    :   '16',
               "coloraxis"     :   'field',
               "overwrite"     :   True,
           },
    input = INPUT,
    output = OUTPUT,
    label = 'plot_amp_uvdist:: Plot amplitude vs distance')


# One final useful plot we will make is a datastream plot of the
# antenna2 in a baseline for the data versus refant. This shows,
# assuming that refant is in the entire observation, when various
# antennas drop out.

# Plot antenna dropout

recipe.add('cab/casa_plotms', 'antenna_dropout', 
           {
               "vis"       :   msname,
               "plotfile"  :   msname + '-antenna_dropout.png',
               "xaxis"     :   'time',
               "yaxis"     :   'antenna2',
               "spw"       :   SPW_delay_cal,
               "antenna"   :   refant,
               "selectdata":   True,
               "coloraxis" :   'field',
               "overwrite" :   True,
           },
    input = INPUT,
    output = OUTPUT,
    label = "antenna_dropout:: Plot antenna dropout")


#############################################################

## 1GC Calibration

recipe.add('cab/casa_setjy', 'set_flux_scaling', 
           {
               "msname"           :   msname,
               "field"         :   bandpass_cal,
               "standard"      :   'Perley-Butler 2013',
               #        "model"         :   '3C48_C.im',
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
        "uvrange"       : '1~25klambda',  # Not using short baselines
        "caltable"      :   PHASECAL_TABLE,
        "field"         :   bandpass_cal,
        "refant"        :   refant,
        "gaintype"      :   'G',
        "calmode"       :   'p',
        "solint"        :   '65s',
        "minsnr"        :   3,
    },
    input=INPUT, output=OUTPUT,
    label="phase0:: Initial phase calibration")

########################################

# Plot phase_cal(PHASECAL_TABLE) in time Vs amp & phase

recipe.add('cab/casa_plotms', 'plot_phasecal_amp_R', 
           {
               "vis"  :   PHASECAL_TABLE,
               "correlation" :   'R',
               "xaxis"     :   'time',
               "yaxis"     :   'GainAmp',
               "field"     :   phase_cal,
               "figfile"   :   PREFIX+'amp-time-R.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_phasecal_amp_R:: Plot gaincal table. AMP, R')

recipe.add('cab/casa_plotms', 'plot_phasecal_amp_L', 
           {
               "vis"  :   PHASECAL_TABLE,
               "correlation" :   'L',
               "xaxis"     :   'time',
               "yaxis"     :   'GainAmp',
               "field"     :   phase_cal,
               "figfile"   :   PREFIX+'amp-time-L.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_phasecal_amp_L:: Plot gaincal table. AMP, L')

recipe.add('cab/casa_plotms', 'plot_phasecal_phase_R', 
           {
               "vis"  :   PHASECAL_TABLE,
               "correlation" :   'R',
               "xaxis"     :   'time',
               "yaxis"     :   'GainPhase',
               "field"     :   phase_cal,
               "figfile"   :   PREFIX+'phase-time-R.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_phasecal_phase_R:: Plot gaincal table. PHASE, R')

recipe.add('cab/casa_plotms', 'plot_phasecal_phase_L', 
           {
               "vis"  :   PHASECAL_TABLE,
               "correlation" :   'L',
               "xaxis"     :   'time',
               "yaxis"     :   'GainPhase',
               "field"     :   phase_cal,
               "figfile"   :   PREFIX+'phase-time-L.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_phasecal_phase_L:: Plot gaincal table. PHASE, L')

###############################################


# The first stage of bandpass calibration involves solving for the antenna-based delays which put a phase ramp versus
# frequency channel in each spectral window. The K gain type in gaincal solves for the relative delays of each
# antenna relative to the reference antenna (parameter refant), so be sure you pick one that is there for this entire scan
# and good. This is not a full global delay, but gives one value per spw per polarization. Channel range chosen to exclude 
#20 channels on either end of the band. Changing the field from GCAL to BPCAL, check if this makes sense. Apply both antenna position
#correction and initial phase correction.

recipe.add('cab/casa_gaincal', 'delay_cal', 
           {
               "msname"       :   msname,
               "uvrange"       : '1~25klambda',       
               "caltable"  :   DELAYCAL_TABLE,
               "field"     :   bandpass_cal,
               "refant"    :   refant,
               "spw"       :   SPW_delay_cal,
               "gaintype"  :   'K',
               "solint"    :   'inf',
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
        "uvrange"       : '1~25klambda', 
        "caltable"      :   BPASSCAL_TABLE,
        "field"         :   bandpass_cal,
        "spw"           :   SPW_delay_cal,
        "refant"        :   refant,
        "combine"       :   'scan',
        "solint"        :   '5min', #inf
        "bandtype"      :   'B',
        "minblperant"   :   1,
        "minsnr"        :   3, 
        #"gaintable"     :   [PHASECAL_TABLE, DELAYCAL_TABLE],
        "gaintable"     :   [PHASECAL_TABLE],
    },
    input=INPUT, output=OUTPUT,
    label="bandpass:: First bandpass calibration")

###############################################################

# Plot bandpass_cal(BPASSCAL_TABLE) chan vs amp/phase 

recipe.add('cab/casa_plotms', 'plot_bandpass_amp_R', 
           {
               "vis"  :   BPASSCAL_TABLE,
               "correlation" :   'R',
               "xaxis"     :   'chan',
               "yaxis"     :   'GainAmp',
               "field"     :   bandpass_cal,
               "figfile"   :   PREFIX+'-B0-R-amp.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_bandpass_amp_R:: Plot bandpass table. AMP, R')

recipe.add('cab/casa_plotms', 'plot_bandpass_amp_L', 
           {
               "vis"  :   BPASSCAL_TABLE,
               "correlation" :   'L',
               "xaxis"     :   'chan',
               "yaxis"     :   'GainAmp',
               "field"     :   bandpass_cal,
               "figfile"   :   PREFIX+'-B0-L-amp.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_bandpass_amp_L:: Plot bandpass table. AMP, L')


recipe.add('cab/casa_plotms', 'plot_bandpass_phase_R', 
           {
               "vis"  :   BPASSCAL_TABLE,
               "correlation" :   'R',
               "xaxis"     :   'chan',
               "yaxis"     :   'GainPhase',
               "field"     :   bandpass_cal,
               "figfile"   :   PREFIX+'-B0-R-phase.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_bandpass_phase_R:: Plot bandpass table. PHASE, R')

recipe.add('cab/casa_plotms', 'plot_bandpass_phase_L', 
           {
               "vis"  :   BPASSCAL_TABLE,
               "correlation" :   'L',
               "xaxis"     :   'chan',
               "yaxis"     :   'GainPhase',
               "field"     :   bandpass_cal,
               "figfile"   :   PREFIX+'-B0-L-phase.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_bandpass_phase_L:: Plot bandpass table. PHASE, L')

###############################################################


recipe.add("cab/casa_gaincal", "main_gain_calibration",
    {
        "msname"        :   msname,
        "uvrange"       : '1~25klambda', 
        "caltable"      :   AMPCAL_TABLE,
        "field"        :   "%s,%s"%(bandpass_cal, amp_cal),
        "spw"          :   SPW_delay_cal,
        "solint"       :   'inf',
        "refant"       :   refant,
        "gaintype"     :   'G',
        "calmode"      :   'ap',
        "solnorm"      :   False,
        "gaintable"    :   [PHASECAL_TABLE,
                            BPASSCAL_TABLE],
        "interp"       :   ['linear','linear','nearest'],
    },
    input=INPUT, output=OUTPUT,
    label="gaincal:: Gain calibration")


########################################

# Plot phase_cal(AMPCAL_TABLE) in time vs amp/phase

recipe.add('cab/casa_plotms', 'plot_gaincal_amp_R', 
           {
               "vis"  :   AMPCAL_TABLE,
               "correlation" :   'R',
               "xaxis"     :   'time',
               "yaxis"     :   'GainAmp',
               "field"     :   phase_cal,
               "figfile"   :   PREFIX+'-G1-amp-R.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_gaincal_amp_R:: Plot gaincal table. AMP, R')

recipe.add('cab/casa_plotms', 'plot_gaincal_amp_L', 
           {
               "vis"  :   AMPCAL_TABLE,
               "correlation" :   'L',
               "xaxis"     :   'time',
               "yaxis"     :   'GainAmp',
               "field"     :   phase_cal,
               "figfile"   :   PREFIX+'-G1-amp-L.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_gaincal_amp_L:: Plot gaincal table. AMP, L')

recipe.add('cab/casa_plotms', 'plot_gaincal_phase_R', 
           {
               "vis"  :   AMPCAL_TABLE,
               "correlation" :   'R',
               "xaxis"     :   'time',
               "yaxis"     :   'GainPhase',
               "field"     :   phase_cal,
               "figfile"   :   PREFIX+'-G1-phase-R.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_gaincal_phase_R:: Plot gaincal table. PHASE, R')

recipe.add('cab/casa_plotms', 'plot_gaincal_phase_L', 
           {
               "vis"  :   AMPCAL_TABLE,
               "correlation" :   'L',
               "xaxis"     :   'time',
               "yaxis"     :   'GainPhase',
               "field"     :   phase_cal,
               "figfile"   :   PREFIX+'-G1-phase-L.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_gaincal_phase_L:: Plot gaincal table. PHASE, L')

###############################################


recipe.add("cab/casa_fluxscale", "casa_fluxscale",
    {
        "msname"        :   msname,
        "caltable"      :   AMPCAL_TABLE,
        "fluxtable"     :   FLUXCAL_TABLE,
        "reference"     :   [bandpass_cal],
        "transfer"      :   [amp_cal],
        "incremental"   :   False,
    },
        input=INPUT, output=OUTPUT,
        label="fluxscale:: Setting Fluxscale")

###########################

# Plot fluxscale results
# Plot amp_cal(FLUXSCALE_TABLE) in time vs amp

##########################

recipe.add('cab/casa_plotms', 'plot_fluxscale_amp_R', 
           {
               "vis"  :   FLUXSCALE_TABLE,
               "correlation" :   'R',
               "xaxis"     :   'time',
               "yaxis"     :   'GainAmp',
               "field"     :   amp_cal,
               "figfile"   :   PREFIX+'-FS-AMP-R.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_fluxscale_amp_R:: Plot fluxscale AMP, R')


recipe.add('cab/casa_plotms', 'plot_fluxscale_amp_L', 
           {
               "vis"  :   FLUXSCALE_TABLE,
               "correlation" :   'L',
               "xaxis"     :   'time',
               "yaxis"     :   'GainAmp',
               "field"     :   amp_cal,
               "figfile"   :   PREFIX+'-FS-AMP-L.png',
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_fluxscale_amp_L:: Plot fluxscale AMP, L')


###########################

recipe.add("cab/casa_applycal", "apply_calibration", 
    {
        "msname"        :   msname,
        "field"         :   target,
        "gaintable"     :   [PHASECAL_TABLE, BPASSCAL_TABLE, FLUXCAL_TABLE],
        "gainfield"     :   [bandpass_cal, bandpass_cal, amp_cal],
        "spwmap"        :   [[], [], []],
        "parang"        :   True,
    },
    input=INPUT, output=OUTPUT,
    label="applycal:: Apply calibration solutions to target")

# Flag outliers in time & Freq

recipe.add('cab/casa_flagdata', 'threshold_flagging_timefreq', 
           {
               "msname"           :   msname, 
               "mode"             :   'rflag',    
               "correlation"      :   'RR,LL',
               "spw"              :   '',    
               "datacolumn"       :  'corrected',   
               "timedevscale"     :   10, 
               "freqdevscale"     :   10,  
               "action"           :   'apply'      
           },
    input = INPUT,
    output = OUTPUT,
    label = 'threshold_flagging_timefreq:: Flagging above a local rms')

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
               "coloraxis"     :   'corr',
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
               "coloraxis"     :   'corr',
               "plotfile"      :   PREFIX+'-fld1-corrected-ampvsphase-LL.png',
               "overwrite"     :   True,
           },
    input=INPUT,
    output=OUTPUT,
    label='plot_amp_phase_LL:: Plot amplitude vs phase')

# To see the First Image after 1gc

recipe.add('cab/wsclean', 'image_target_field', 
           {
               "msname"        :   msname,
               "field"         :   target,
               "channelrange"  :   [25,220],
               "weight"        :   "briggs 0",               # Use Briggs weighting to weigh visibilities for imaging
               "npix"          :   npixno,                   # Image size in pixels
               "trim"          :   trimno,                    # To avoid aliasing
               "cellsize"      :   cellarcsec,                      # Size of each square pixel
               "stokes"    : "I",
               "nwlayers"  : 128,
               "minuvw-m"  : 100.0,
               "maxuvw-m"  : 15000.0,
               "clean_iterations"  :   100000,
               "gain"          : 0.05,
               "mgain"         : 0.9, 
               "auto-threshold"     : 10,
               #"threshold"     : 0.0001, #Jy
               "prefix"        : LABEL,
               "no-update-model-required" : True,
           },
    input=INPUT,
    output=OUTPUT,
    label="image_target_field:: Image target field After 1gc")


recipe.add("cab/casa_split", "split_calibrated_target_data",
    {
        "msname"        :   msname,
        "outputvis" :   msname[:-3]+"_LHNORTH.MS",
        "field"         :   target,
    },
    input=INPUT, output=OUTPUT,
    label="split_target:: Split calibrated target data")


'''
try:
    recipe.run("flag_band setjy phase0 bandpass gaincal fluxscale applycal".split())
except stimela.PipelineException as e:
    print 'completed {}'.format([c.label for c in e.completed])
    print 'failed {}'.format(e.failed.label)
    print 'remaining {}'.format([c.label for c in e.remaining])
    raise
'''

t = time.time()

recipe.run([
           "quack_flagging",
           "autocorr_flagging",
#           "antenna_flagging",
           "flag_bandstart",
           "flag_bandend", 
           "aoflag_data",
           "set_flux_scaling",
           "phase0",
 #          "delay_cal",
           "bandpass",
           "gaincal",
           "fluxscale",
           "applycal",
#           "threshold_flagging_timefreq",
           "plot_amp_phase_RR",
           "plot_amp_phase_LL", 
           "image_target_field",
           "split_target",
           ])
  
print "1gc done in %.2f sec" %(time.time() - t)
