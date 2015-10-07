import logging
import numpy as np

import image_lib
import nirspec_lib
import wavelength_utils
import Line
#import Order

logger = logging.getLogger('obj')

def reduce_order(order):
            
    # normalize flat
    order.normalizedFlatImg, order.flatMean =  image_lib.normalize(
            order.flatCutout, order.onOrderMask, order.offOrderMask)
    order.flatNormalized = True
    logger.info('flat normalized, flat mean = ' + str(round(order.flatMean, 1)))
        
    # flatten obj but keep original for noise calc
    order.flattenedObjImg = np.array(order.objCutout / order.normalizedFlatImg)
    order.flattened = True
    order.objImg = np.array(order.objCutout) # should probably use objImg instead of objCutout to begin with
    order.flatImg = np.array(order.flatCutout)
    logger.info('order has been flat fielded')
    
    # smooth spatial trace
    # this should probably be done where the trace is first found
    
#     import pylab as pl
#     pl.figure()
#     pl.cla()
#     pl.plot(order.avgTrace)
#     pl.show()
    
    order.smoothedTrace, order.traceMask = nirspec_lib.smooth_spatial_trace(order.avgTrace)
    logger.info('spatial trace smoothed, ' + str(order.objImg.shape[1] - np.count_nonzero(order.traceMask)) + 
            ' points ignored')
    
    
    if float(order.botMeas) > float(order.padding):
        order.smoothedTrace = order.smoothedTrace - order.botMeas + order.padding
        order.avgTrace = order.avgTrace - order.botMeas + order.padding
    
#     import pylab as pl
#     pl.figure('', facecolor='white', figsize=(8, 6))
#     pl.cla()    
#     f = pl.imshow(order.objImg, vmin=0, vmax=256, aspect='auto', cmap="gist_heat_r")
#     f.axes.get_xaxis().set_visible(False)
#     f.axes.get_yaxis().set_visible(False)
#     pl.show()
    
    # rectify flat, normalized flat, obj and flattened obj in spatial dimension
    order.flatImg = image_lib.rectify_spatial(order.flatImg, order.smoothedTrace)
    order.normalizedFlatImg = image_lib.rectify_spatial(order.normalizedFlatImg, order.smoothedTrace)
    order.objImg = image_lib.rectify_spatial(order.objImg, order.smoothedTrace)
    order.flattenedObjImg = image_lib.rectify_spatial(order.flattenedObjImg, order.smoothedTrace)

    order.spatialRectified = True
    
    # find spatial profile and peak
    order.spatialProfile = order.flattenedObjImg.mean(axis=1)
    order.peakLocation = np.argmax(order.spatialProfile)
    
    # find and smooth spectral trace
    try:
        order.spectral_trace = nirspec_lib.smooth_spectral_trace(
                nirspec_lib.find_spectral_trace(
                        order.flattenedObjImg, order.padding), order.flattenedObjImg.shape[0])
    except Exception as e:
        logger.warning('not rectifying order in spectral dimension')
 
    else:
        # rectify flat, normalized flat, obj and flattened obj in spectral dimension 
        order.flatImg = image_lib.rectify_spectral(order.flatImg, order.spectral_trace)
        order.normalizedFlatImg = image_lib.rectify_spectral(order.normalizedFlatImg, order.spectral_trace)
        order.objImg = image_lib.rectify_spectral(order.objImg, order.spectral_trace)
        order.objImgFlattened = image_lib.rectify_spectral(order.flattenedObjImg, order.spectral_trace)
        order.spectralRectified = True
        
#     import pylab as pl
#     pl.figure('', facecolor='white', figsize=(8, 6))
#     pl.cla()    
#     f = pl.imshow(order.objImg, vmin=0, vmax=256, aspect='auto', cmap="gist_heat_r")
#     f.axes.get_xaxis().set_visible(False)
#     f.axes.get_yaxis().set_visible(False)
#     pl.show()
     
    # compute noise image
    order.noiseImg = nirspec_lib.calc_noise_img(
            order.objImg, order.normalizedFlatImg, order.integrationTime)
      
    # find spatial profile and peak
    order.spatialProfile = order.flattenedObjImg.mean(axis=1)
    order.peakLocation = np.argmax(order.spatialProfile)
    
    # extract spectra
    order.objWindow, order.topSkyWindow, order.botSkyWindow = \
        image_lib.get_extraction_ranges(order.objImg.shape[0], order.peakLocation)
        
    order.objSpec, order.skySpec, order.noiseSpec = image_lib.extract_spectra(
            order.flattenedObjImg, order.noiseImg, order.peakLocation,
            order.objWindow, order.topSkyWindow, order.botSkyWindow)
    
    # find and identify sky lines   
    line_pairs = None # line_pairs are (column number, accepted wavelength
    try:
        oh_wavelengths, oh_intensities = wavelength_utils.get_oh_lines()
        
        order.synthesizedSkySpec = wavelength_utils.synthesize_sky(
                oh_wavelengths, oh_intensities, order.wavelengthScaleCalc)
         
        line_pairs = wavelength_utils.line_id(order, oh_wavelengths, oh_intensities)
        
    except (IOError, ValueError) as e:
        logger.warning('sky line matching failed: ' + str(e))
        
    if line_pairs is not None:
        
        logger.info(str(len(line_pairs)) + ' matched sky lines found in order')

        # add line pairs to Order object as Line objects
        for line_pair in line_pairs:
            line = Line.Line()
            line.col, line.acceptedWavelength = line_pair
            line.peak = order.skySpec[line.col]
            order.lines.append(line)
        
    else:
        logger.warning('no matched sky lines in order ' + str(order.orderNum))
                    
    #raw_input('waiting')
    
    return
         
    
    

    

    
    

    