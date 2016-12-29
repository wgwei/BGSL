# -*- coding: utf-8 -*-
"""
Created on Tue Oct 09 09:58:09 2012
model to map background noise level
created in 2011,
modified on June, October
new features: 
    1, optimize the input shape files of building, sources and receivers
    2, use objects of sources, recievers and buildings instead of querying by
        dictionary
    3, open the posibility to extend attributes of source and receiver objects. 
    4, including the absolute height of the sources, receivers and buildings
    5, put the results in a separate shape folder
    6, divid the source zone by memory operation
    7, combine the divided zone linked to the original file
@author: Wei
"""
import os
import shutil
import numpy as np
import time
import dbflib
import shapelib
import lass
import math, sys
import pickle
sys.path.append(r"S:\projecten\QSIDE\simulations\Project_scripts\PieceEquation")
from MDF_01 import  AbarRoof
import mexi_gdal_grid as egrid
antw_dtm = egrid.ReadAIGGrid('dtm_gent', '.\\dtm_gent')

    
class Buildings():
    def __init__(self, relativeHeight, absoluteHeight, intersection):
        self.relativeHeight = relativeHeight
        self.absoluteHeight = absoluteHeight
        self.intersection = intersection
        
class Receivers():    
    def __init__(self, vertix, identify, absoluteHeight):
        self.vertix = vertix
        self.absoluteHeight = absoluteHeight
        self.identify = identify  # unique id to identify the receiver
        
class Sources():    
    def __init__(self, vertix, immissonSpectrum, absoluteHeight):
        self.vertix = vertix
        self.immissonSpectrum = immissonSpectrum
        self.absoluteHeight = absoluteHeight        
        
def calculateCentriod(polygon):
    """ polygon = [[x1, y1], [x2, y2], [x3, y3],...]
    """
    xsum = 0.0
    ysum = 0.0
    c = 0.0
    for p in polygon:
        xsum += p[0]
        ysum += p[1]
        c += 1
    return [xsum/c, ysum/c]    

class SimplePolygon2D:
    def __init__(self, iVertices):
        self.vertices = iVertices
        if not self._isCounterClockwise():
            self.vertices.reverse()
        self.dim2 = range(2)
    def aabb(self):
        aabbMin = tuple([min([p[k] for p in self.vertices]) for k in self.dim2])
        aabbMax = tuple([max([p[k] for p in self.vertices]) for k in self.dim2])
        return (aabbMin, aabbMax)   
    def contains(self, point):
        c = False
        x = point[0]
        y = point[1]
        for i in range(len(self.vertices)):
            a = self.vertices[i]
            b = self.vertices[i - 1]
            if ((a[1] <= y and y < b[1]) or (b[1] <= y and y < a[1])) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
                c = not c
        return c
    def cross2D(self, a, b):
        return a[0] * b[1] - a[1] * b[0]  
    def _isCounterClockwise(self):
        return sum([self.cross2D(self.vertices[k - 1], self.vertices[k]) for k in xrange(len(self.vertices))]) >= 0
        
def readPolygonFile(iFilename, ID_field):
        print 'reading simple polygon file', iFilename
        relativeHeihgtField = 'REL_HEIGHT'
        shp = shapelib.ShapeFile(iFilename)
        dbf = dbflib.open(iFilename)
        polygons = []
        for i in xrange(shp.info()[0]):
            if len(shp.read_object(i).vertices())>0:
                vs = shp.read_object(i).vertices()[0]
                vs = [(v[0] , v[1] ) for v in vs[1:]]
                vs.reverse()
                polygon = SimplePolygon2D(vs) # polygon.vertices return the vertices of the  
                polygon.relativeHeight = dbf.read_record(i)[relativeHeihgtField]
                polygon.pid = dbf.read_record(i)[ID_field]
                polygons.append(polygon)
        shp.close()
        dbf.close()
        return polygons        

class KDTreeManualPolygon:
    def __init__(self, listPolygonObject):
        '''listPolygonObject: list of polygon objects generated by SimplePolygon2D'''
        self.polygonTree= lass.AabbTree2D(listPolygonObject)
        print len(listPolygonObject), 'added to KDTree'

    def findPolygonsInside(self, point):
        ''' return polygonObj
            polygonObj can be used to query info defined in 'readPolygonFile'
            if len(polyonObj)==0, indicates the point is not inside the polygon
        '''
        objectSequence = self.polygonTree.find(point)
        return objectSequence   # objectSequence = [polygonObject1, polygonObject2, ...] polygonObj can be used to query info defined in 'readPolygonFile'

    def pointInside(self, point):
        polygonObj = self.polygonTree.find(point)
        if len(polygonObj)>0:
            return True
        else:
            return False

def vertice2polygonObj(vertices):
    """ convert vertices list [[x1, y1], ...[xn, yn]] to
        polygon object used in KDTree
    """
    return SimplePolygon2D(vertices)
    
def packBuildingToPKL(buildingShapeFile, ID='ID'):
    listPolygonObjects = readPolygonFile(buildingShapeFile, ID)
    return listPolygonObjects # [obj1, ...objn] obj.vertices = [[x,y], ..[xn,yn]]
    
def packSourceToPKL(sourceShapeFile):
    shp = shapelib.open(sourceShapeFile)
    dbf = dbflib.open(sourceShapeFile)
    specField = ['L_63', 'L_125', 'L_250', 'L_500', 'L_1000', 'L_2000', 'L_4000', 'L_8000']
    sourceObjects = []
    for r in xrange(shp.info()[0]):
            shpObj = shp.read_object(r)
            p_source = shpObj.vertices()[0]  # (x, y)    
            rec = dbf.read_record(r)
            specD = [rec[f] for f in specField]
            spec = [specD]
            absoluteHeight = antw_dtm.read_vtx(p_source)
            sObj = Sources(p_source, spec, absoluteHeight)
            sourceObjects.append(sObj)
    shp.close()
    dbf.close()    
    return sourceObjects  # list of soruce object. values defined in "Sources" can be queried

def packReceiverToPKL(receiverShapeFile, IDFieldName):
    shp = shapelib.open(receiverShapeFile)
    dbf = dbflib.open(receiverShapeFile)    
    receiverObjects = []    
    for r in xrange(shp.info()[0]):
        print "receiver: ", r
        shpObj = shp.read_object(r)
        vtx = shpObj.vertices()[0]
        absoluteHeight = antw_dtm.read_vtx(vtx)
        identify = dbf.read_record(r)[IDFieldName]
        rObj = Receivers(vtx, identify, absoluteHeight)
        receiverObjects.append(rObj)  
    shp.close()
    dbf.close()
    return receiverObjects

def shrinkBuildingZone(polygonsObj, smallerZone):
    listPolygonObjects = []
    zoneObj = SimplePolygon2D(smallerZone)
    zoneKDT = KDTreeManualPolygon([zoneObj])        
    for po in polygonsObj:
        centriod = calculateCentriod(po.vertices)  #use centriod to detect the polyin inside the smaller zone or not
        if zoneKDT.pointInside(centriod):
            listPolygonObjects.append(po)
    return listPolygonObjects # [obj1, ...objn] obj.vertices = [[x,y], ..[xn,yn]]
    
def shrinkSourceZone(sourceObjects, smallerZone):
    smSourceObjects = []
    zoneObj = SimplePolygon2D(smallerZone)
    zoneKDT = KDTreeManualPolygon([zoneObj])    
    for sObj in sourceObjects:
        p_source = sObj.vertix
        if zoneKDT.pointInside(p_source):
            smSourceObjects.append(sObj)
    return smSourceObjects  # list of soruce object. values defined in "Sources" can be queried

def shrinkReceiverZone(receiverObjects, smallerZone):
    smReceiverObjects = []
    zoneObj = SimplePolygon2D(smallerZone)
    zoneKDT = KDTreeManualPolygon([zoneObj])    
    for rObj in receiverObjects:
        vtx = rObj.vertix
        if zoneKDT.pointInside(vtx):            
            smReceiverObjects.append(rObj)      
    return smReceiverObjects
    
def intersection(p1, p2, p3, p4):
    ''' calcualte the intersection of two lines defined by piont1 ->p1, 
        point 2, point 3 and point4. 
        p1 and p2 stand for line 1
        p3 and p4 stand for line 2
    '''
    if p2[1]!=p4[1]:   # if the two canyon are not the same height
        p2[1] = (p2[1]+p4[1])/2
        p4[1] = (p2[1]+p4[1])/2
    x1 = p1[0]
    y1 = p1[1]
    x2 = p2[0]
    y2 = p2[1]
    x3 = p3[0]
    y3 = p3[1]
    x4 = p4[0]
    y4 = p4[1]
    x = ((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))
    y = ((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))
    return [x, y]
    
def cal_ds_dr_h(v1, v2, v3, phis, phir, sht, rht):
    ''' calculate ds and dr in Jens's scattering model
        v1 is point 1 (x, y) usually is source position
        v2 is the intersection (x, y)
        v3 is the receiver position (x,y)
        phis and phir are angles defined in pierce defraction equation
    '''    
    distV1V2 = np.sqrt((v2[1]-v1[1])**2+(v2[0]-v1[0])**2)
    distV2V3 = np.sqrt((v3[1]-v2[1])**2+(v3[0]-v2[0])**2)
    distV1V3 = np.sqrt((v3[1]-v1[1])**2+(v3[0]-v1[0])**2)
    angle1 = math.atan((v2[1]-v1[1])/(v2[0]-v1[0]))
    angle2 = math.atan(abs((v3[1]-v2[1]))/(v3[0]-v2[0]))
    angle123 = angle1+angle2
    h = distV1V2*distV2V3*np.sin(angle123)/distV1V3    
    dr = np.sqrt(abs(distV2V3**2-h**2))
    ds = np.sqrt(abs(distV1V2**2-h**2))
    if h<=0 or h!=h or ds<=0 or ds!=ds or dr<=0 or dr!=dr:
        assert(False)
    return [ds, dr, h]   


def cal_buildingNum(barrierWidth):
    return np.floor(0.0114*barrierWidth)+1

def cal_refraction(srDist):
    return np.min([srDist/100.0, 15])
    
    
def fitModel_scatter(Cvsq, Ctsq, sht, rht, fr,srDist, p_source, N1point, p_receiver, N2point,\
         phis, phir, Ws, Wr, height):
    ''' test Jens' scattering model    
    '''
    H0 = 10.0
    d0 = 10.0
    f0 = 1000.0
    epslon = 0.000004
    tb1 = -49.6+10*np.log10(Ctsq)
    tb2 = 11.5
    tb3 = -13.1
    vb1 = -52.8+10*np.log10(Cvsq)
    vb2 = 11.3
    vb3 = -17.1    
    V2 = intersection(p_source, N1point, p_receiver, N2point)
    [ds, dr, h] = cal_ds_dr_h(p_source, V2, p_receiver, phis, phir, sht, rht)    
    if type(fr)==list:
        fr = np.array(fr)
    AscatBarCt = tb1 + tb2*np.log10(h/d0) + tb3*np.log10((h**2)/(dr*ds)+(h**2)*epslon) + 3.33*np.log10(fr/f0)      
    AscatBarCv = vb1 + vb2*np.log10(h/d0) + vb3*np.log10((h**2)/(dr*ds)+(h**2)*epslon) + 3.33*np.log10(fr/f0)
    AscatBar = 10*np.log10(10**(0.1*AscatBarCt) + 10**(0.1*AscatBarCv))   
    if height==0:
        print 'height: ', height
        assert(False)        
    if Ws==False and Wr==False:
        AscatCanyon = 0
    elif Ws==False and Wr!=False:
        gema2 = 2.0*height/Wr
        AscatCanyon = 7.0 + gema2*np.log10(height/H0)
    elif Ws!=False and Wr==False:
        gema2 = 2.0*height/Ws
        AscatCanyon = 7.0 + gema2*np.log10(height/H0)
    elif Ws!=False and Wr!=False:
        # should be careful: when both Ws and Wr are small, but height is big. then the
        # canyon term can become very big!!! That could be the main reason why this model
        # could overestimate the level when implimment it in the GIS system
        gema2 = 2.0*height*(1.0/Ws+1.0/Wr)
        AscatCanyon = 14.0 + gema2*np.log10(height/H0)        
    Ascat = AscatBar+AscatCanyon     
    mixAttenuation =  Ascat    
    return mixAttenuation
  
def fitModel(h1, h2, Hs, Hr, Wi, waveLength, sHi, rHi, fr, distSR,\
             N1point, N2point, Ws, Wr, rs, rr, spos, rpos, phis, phir):
    """fitModel(h1, h2, Hs, Hr, barrierWidth, waveLength, sHi, rHi, fr, distSR,\
             N1point, N2point, Ws, Wr, rs, rr, spos, rpos)
        h1 = Hi-sHi
        h2 = Hi-rHi
        sHi = source height
        rHi = receiver height
        fr is central frequency [63 125 250 500 1000 2000 4000 8000]Hz
        srDist is the distance between source and receiver
        N1point is building vertix in source canyon (x, y)
        N2point is building vertex in receiver canyon (x, y)
    """        
    # modified on Feb 1st 2012, June 25h
    if sHi==0:
        sHi = 0.01
    if rHi==0:
        rHi = 0.01
    if type(fr)==list:
        fr = np.array(fr) 
    if N1point[1]!=N2point[1]:
        N1point[1] = (N1point[1]+N2point[1])/2.0
        N2point[1] = (N1point[1]+N2point[1])/2.0
    THKbar = AbarRoof([0, sHi], rpos, N1point, N2point, phis, phir,fr)
    [Abar, d] = THKbar._flatRoofLevelGround()
    Hi = N1point[1]
    AcanE = 1.22*10*np.log10(1.56*(Hs+Hr+1)/Hi * (0.4/(0.87*(h1+h2)/np.sqrt(waveLength*(rs+rr))+0.4))**2 * (0.4/(np.sqrt(1.5*Wi/waveLength)*np.abs(2*Hi-Hs-Hr)/(Ws+Wr)+0.4)))
    AroofNocan = 0.27*Abar+2.9
#    AroofCan = 15.5*np.log10(fr/160.0)  # save as withHeightFDTD-v8.2.2-1
    AroofCan = 5.  # save as save as withHeightFDTD-v8.2.2-2
    if Hs==0:
        if Hr!=0:
            Aroof = AroofCan/2
        else:
            Aroof = AroofNocan
    else:
        if Hr==0:
            Aroof = AroofCan/2
        else:
            Aroof = AroofCan
        
    Ainter = distSR/100.0
    if Ainter>5.0:
        Ainter = 5.0
    mixAttenuation = - Ainter + Aroof
    return [Abar, AcanE, mixAttenuation] 

class SmallerZones():
    def __init__(self, receiverShape, sizeReceiverZone=2000.0, dist2outerBuilding=1500.0):
        self.dRZone = sizeReceiverZone
        self.d2B = dist2outerBuilding
        self.Rshp = shapelib.open(receiverShape)
        self.RB = [self.Rshp.info()[2], self.Rshp.info()[3]]  # [(x_min, y_min, z_min, m_min), (x_max, y_max, z_max, m_max)]
        self.Rshp.close()
    def _generateGridVertices(self):
        # get grid vertixs of the zone       
        px = self.RB[0][0]
        pxList = []
        while px<self.RB[1][0]:
            pxList.append(px)
            px += self.dRZone
        pxList.append(self.RB[1][0])
        py = self.RB[1][1]
        pyList = []
        while py>self.RB[0][1]:
            pyList.append(py)
            py -= self.dRZone
        pyList.append(self.RB[0][1])
        return [pxList, pyList]
    
    def _verticesToZones(self, pxList, pyList):
        # get the zones
        rZonesList = []
        sbZoneList = []
        for n in xrange(len(pyList)-1):
            for m in xrange(len(pxList)-1):
                rZone = [[pxList[m], pyList[n]], [pxList[m], pyList[n+1]], [pxList[m+1], pyList[n+1]], [pxList[m+1], pyList[n]], [pxList[m], pyList[n]]]
                sbZone = [[rZone[0][0]-self.d2B, rZone[0][1]+self.d2B], \
                          [rZone[1][0]-self.d2B, rZone[1][1]-self.d2B], \
                          [rZone[2][0]+self.d2B, rZone[2][1]-self.d2B], \
                          [rZone[3][0]+self.d2B, rZone[3][1]+self.d2B], \
                          [rZone[0][0]-self.d2B, rZone[0][1]+self.d2B]]
                rZonesList.append(rZone)
                sbZoneList.append(sbZone)
        return [rZonesList, sbZoneList]
   
class Model():
    def __init__(self,Cvsq, Ctsq, buildingFile, receiverFile, sourceFile, resultOutFile,\
        rZoneSize=2000.0, r2sDist=1500.0, flags=['D', 'E', 'N'], modelType='scattering'):
        ''' buildingFile, receiverFile, sourceFile and resultOutFile 
            are shape file names
            resultOutFile is also the new folder
            receiverZone is the vertix of the smaller receiver region
            SBzone is the corresponding zone of the receivers
            flags -> 'D', 'E', 'N' represent for day, evening and Night
        '''
        self.Cvsq = Cvsq
        self.Ctsq = Ctsq
        self.i = 0   # acounter to write results out
        print 'initialing...'   
        # common constants
        self.fr = [63, 125, 250, 500, 1000, 2000, 4000, 8000]
        self.waveLength = 340.0/np.array(self.fr)
        self.Aweight =  np.array([-26.2, -16.1,-8.6, -3.2, 0, 1.2, 1, -1.1])   # {63:-26.2, 125:-16.1, 250:-8.6, 500:-3.2, 1000:0, 2000:1.2, 4000:1, 8000:-1.1}
        self.sHi = 0.0   # source Height♠
        self.rHi = 4.5   # receiver height
        self.modelType = modelType        
        # preparing to write results out
        print "preparing to write to file: ", resultOutFile
        if not os.path.exists(resultOutFile):
            os.mkdir(resultOutFile)
        shutil.copy(receiverFile+'.shp', resultOutFile)
        shutil.copy(receiverFile+'.shx', resultOutFile)
        self.DBFOut = dbflib.create(resultOutFile+'\\'+resultOutFile)
        self.DBFOut.add_field("GENTID", dbflib.FTInteger, 7, 0)  # add the idential ID
        self.fieldName = ['L_63', 'L_125', 'L_250', 'L_500', 'L_1000', 'L_2000', 'L_4000', 'L_8000', 'LA']        
        for fg in flags:
            for f in self.fieldName: # add new field
                self.DBFOut.add_field(f+fg, dbflib.FTDouble, 9, 1)
        
        # write log
        print 'Create log'
        yr = time.gmtime()[0]
        mon = time.gmtime()[1]
        day = time.gmtime()[2]
        hour = time.gmtime()[3]
        minu = time.gmtime()[4]
        label = str(yr)+str(mon)+str(day)+str(hour)+str(minu)
        logw = open(resultOutFile+'\\'+'log_' + label +'.txt', 'w')
        logw.write(time.ctime()+'\r\n')
        logw.write('buildingFile: '+buildingFile+'\r\n'+'receiverFile: '+receiverFile+'\r\n')
        logw.write('sourceFiel: '+sourceFile+'\r\n')
        logw.write('Dimension of receiver zone: '+str(rZoneSize)+'*'+str(rZoneSize)+'\r\n')
        logw.write('Maximum distance from source to receiver: '+str(r2sDist)+'\r\n')
        logw.write('Source type: ' + str(flags)+'\r\n')
        logw.write('Model type: ' + modelType + '\r\n\r\n')
        tic = time.clock()
        
        print 'Prepare source, receiver and buildings'  
#        try: 
        if not os.path.exists('pkData'):
            os.mkdir('pkData')        
        if not os.path.exists('pkData\\PKLsourceOBJ.pkl'):
            sourceObjects = packSourceToPKL(sourceFile)
            sw = open('pkData\\PKLsourceOBJ.pkl', 'wb')
            pickle.dump(sourceObjects, sw, 2)  # protocal 2 for verion 2.x, 3for 3.x
            sw.close()
        else:
            sr = open('pkData\\PKLsourceOBJ.pkl', 'rb')
            sourceObjects = pickle.load(sr)
            sr.close()
        if not os.path.exists('pkData\\PKLreceiverOBJ.pkl'):
            receiverObjects = packReceiverToPKL(receiverFile, 'GID')
            rw = open('pkData\\PKLreceiverOBJ.pkl', 'wb')
            pickle.dump(receiverObjects, rw, 2)
            rw.close()
        else:
            rr = open('pkData\\PKLreceiverOBJ.pkl', 'rb')
            receiverObjects = pickle.load(rr)
            rr.close()
        if not os.path.exists('pkData\\PKLbuildingOBJ.pkl'):
            polygonObjects = packBuildingToPKL(buildingFile)
            bw = open('pkData\\PKLbuildingOBJ.pkl', 'wb')
            pickle.dump(polygonObjects, bw, 2)
            bw.close()
        else:
            br = open('pkData\\PKLbuildingOBJ.pkl', 'rb')
            polygonObjects = pickle.load(br)
            br.close()     
            
        toc1 = time.clock()
        logw.write('Initializing takes '+str(toc1-tic)+' seconds\r\n')
        
        print 'calculating...'
        # test the zones        
        rSHP = shapelib.open(receiverFile)
        if rSHP.info()[3][0]-rSHP.info()[2][0]>9999999999 or rSHP.info()[3][1]-rSHP.info()[2][1]>999999999:
            smObj = SmallerZones(receiverFile, rZoneSize, r2sDist)
            [pxList, pyList] = smObj._generateGridVertices()
            [rZones, sbZones] = smObj._verticesToZones(pxList, pyList) 
            print 'Divid to ', len(rZones), ' zones'
            for n in xrange(len(rZones)):
                print 'Calculating zone ', n
                rz = rZones[n]
                sbz = sbZones[n]
                # shrinking region or load shape
                self.receiverObjects = shrinkReceiverZone(receiverObjects,rz)
                if len(self.receiverObjects)>0:
                    listPolygonObjects = shrinkBuildingZone(polygonObjects, sbz)
                    self.buildings = KDTreeManualPolygon(listPolygonObjects)
                    self.sourceObjects = shrinkSourceZone(sourceObjects, sbz)                        
                    self.runModel()
        else:
            self.buildings = KDTreeManualPolygon(polygonObjects)
            self.sourceObjects = sourceObjects
            self.receiverObjects = receiverObjects    
            self.runModel()
#        except: 
#            logw.write('\r\n\r\nAborted unexpectedly!!! \r\n\r\n')
        toc2 = time.clock()
        logw.write('Calculating takes '+str(toc2-tic)+' seconds\r\n')
        logw.close()
        
    def stepOut(self, pStart, dx, dy, maxStep):
        rp_eval = 1
        px1 = pStart[0]
        py1 = pStart[1]
        rp = (px1 + rp_eval*dx, py1 + rp_eval*dy)
        buildingObjSequence = self.buildings.findPolygonsInside(rp)
        while rp_eval<maxStep and len(buildingObjSequence)<1:
            rp = (px1 + (rp_eval+1)*dx, py1 + (rp_eval+1)*dy)   # step is 1 meter
            buildingObjSequence = self.buildings.findPolygonsInside(rp)
            rp_eval += 1            
        if len(buildingObjSequence)<1:
            BObj = False
        else:
            buildingObj = buildingObjSequence[0]
            relativeHeight = buildingObj.relativeHeight            
            if relativeHeight < 4.6:
                relativeHeight = 4.6
            absoluteHeight = antw_dtm.read_vtx(rp)
            BObj = Buildings(relativeHeight, absoluteHeight, rp)            
        return [rp_eval-0.5, BObj] # since the step is 1, here remove half of the step. this method is good for receivers offset facade a large distance.
    
    def stepoutDistHeight(self, source, receiver, N1234):
        """ (source, p2) p1 the first point step to the second point p2
            p1 is q list[x1, y1]; p2 is q list [x2, y2]. Return the distance
            between p1 and the first building and the building height as [dist, rp_eval, height]
            buildings is the object of the KDTree, passed to judge whether inside a polygon
        """
        px1 = source[0]
        py1 = source[1]
        px2 = receiver[0]
        py2 = receiver[1]    
        dist = np.sqrt((px2-px1)**2 + (py2-py1)**2) # distance    
        assert (dist!=0)
        if N1234=="N1":
            dx = (px2-px1)/dist
            dy = (py2-py1)/dist
            [rp_eval, BObj] = self.stepOut(source, dx, dy, int(dist)+1)
            return [dist, rp_eval, BObj]
        elif N1234=="N2":      
            dx = (px1-px2)/dist
            dy = (py1-py2)/dist
            [rp_eval, BObj] = self.stepOut(receiver, dx, dy, int(dist)+1)
            return [dist, rp_eval, BObj]
        elif N1234=="N3":
            dx = (px1-px2)/dist
            dy = (py1-py2)/dist
            [rp_eval, BObj] = self.stepOut(source, dx, dy, 150)
            return [dist, rp_eval, BObj]
        elif N1234=="N4":
            dx = (px2-px1)/dist
            dy = (py2-py1)/dist
            [rp_eval, BObj] = self.stepOut(receiver, dx, dy, 150)
            return [dist, rp_eval, BObj]
        else:
            assert (N1234 in "N1 N2 N3 N4")        
            return False
        
    def _writeResultOut(self, r, identify, LD, LweightedD):
        """ r is record number; LD is day level; LweightedD is total level of LDay
            LE is evening level; LWeigangE
        """
        # mix data
        rec = [identify]+list(LD)+[LweightedD]
        for f in xrange(len(rec)):            
            self.DBFOut.write_attribute(r, f, rec[f])       
        
    def _getL_DEN(self, LD, LE, LN):
        L_DEN = 10.0*np.log10(12.0/24.0*10.0**(0.1*LD) + \
                            4.0/24.0*10.0**(0.1*(LE+5.0)) + \
                            8.0/24.0*10.0**(0.1*(LN+10.0)))
        return L_DEN    
        
    def runModel(self):   
        if len(self.receiverObjects)>0:
            for i, receiverObj in enumerate(self.receiverObjects):
                print i, ' receiver'
                p_receiver = receiverObj.vertix   # (x, y) 
                IDay = np.array([0.0] * 8)
                for j, sourceObj in enumerate(self.sourceObjects):   # loop for all sources
                    # contribution of a source
                    p_source = sourceObj.vertix
                    dst = np.sqrt((p_receiver[0]-p_source[0])**2 + (p_receiver[1]-p_source[1])**2)
                    if dst<=1500:
                        # calculating N1 N2 N3 and N4
                        [distSR, step1, BObj] = self.stepoutDistHeight(p_source, p_receiver, "N1")        
                        # modified on Jan31, 3rd, oct, weigang
                        if BObj!=False:
                            N1point = [step1, BObj.relativeHeight] # which could be a value < 4.5 we set it to 5 to keep scattering input valid
                            if N1point[1]<5.0:
                                N1point[1] = 5.0
                            spos = [0.0,self.sHi]                
                            if (step1<(distSR-1)):   # judge whether there is any building between source and receiver                                     
#                                N1 = np.sqrt((N1point[1]-self.sHi)**2+step1**2) - step1 
                                # N2
                                [dist, step2, BObj2] = self.stepoutDistHeight(p_source, p_receiver, "N2") 
                                if BObj2!=False:
                                    # modified Jan31 weigang Jun25th, 2nd oct
                                    N2point = [distSR-step2, BObj2.relativeHeight]
                                    barrierWidth = distSR-step1-step2
                                    rpos = [distSR, self.rHi]
                                    if barrierWidth>2.5:  # 29June, 2nd oct
                                        rs = np.sqrt((N1point[1]-self.sHi)**2+step1**2) # modified Jan31 weigang  
                                        rr = np.sqrt((N2point[1]-self.rHi)**2+step2**2)
                                        h1 = N1point[1]-self.sHi
                                        h2 = N2point[1]-self.rHi
                                        phis = math.asin(step1/rs)
                                        phir = math.asin(step2/rr) 
                                        [dist, step3, BObj3] = self.stepoutDistHeight(p_source, p_receiver, "N3")                                        
                                        if BObj3 == False or step3>150:
                                            Hs = 0.0
                                            Ws = 1000.
                                        else:
                                            Ws = (step1 + step3)*1.0
                                            Hs = BObj3.relativeHeight
                                            if Ws<=3.0:
                                                Ws = 3.0                                        
                                        [dist, step4, BObj4] = self.stepoutDistHeight(p_source, p_receiver, "N4")     
                                        if BObj4 == False or step4>150:
                                            Hr = 0.0
                                            Wr = 1000.
                                        else:
                                            Wr = (step2 + step4)*1.0
                                            Hr = BObj4.relativeHeight
                                            if Wr<=3.0:
                                                Wr = 3.0                                                                           
                                        if self.modelType=='scattering':
                                            sposVertical = (0.0, 0.0)
                                            rposVertical = (np.sqrt(distSR**2+(self.rHi-self.sHi)**2), self.rHi-self.sHi)
                                            N1point[1] = max(BObj.relativeHeight, 5.0)   # assume the ground is flat
                                            N2point[1] = max(BObj.relativeHeight, 5.0)   # assume the ground id flat
                                            mixAttenuation = fitModel_scatter(self.Cvsq, self.Ctsq, self.sHi, \
                                                        self.rHi, self.fr,distSR,\
                                                        sposVertical, N1point, rposVertical, N2point,\
                                                        phis, phir, Ws, Wr, BObj.relativeHeight)
                                            IL = -mixAttenuation + 20.0*np.log10(distSR) + 11   # insertion loss
                                            if min(IL)<=0:
                                                print 'IL: ', IL
                                                print ' '
                                                print self.Cvsq, self.Ctsq, self.sHi, \
                                                        self.rHi, self.fr,distSR,\
                                                        sposVertical, N1point, rposVertical, N2point,\
                                                        phis, phir, Ws, Wr, BObj.relativeHeight
                                                print 'step2, step4: ', step2, step4
                                                print ' '                                            
                                        elif self.modelType=='FDTDfitting':
                                            [Abar, AcanE, mixAttenuation] = fitModel(h1, h2, Hs, Hr, barrierWidth,\
                                                        self.waveLength, self.sHi, self.rHi, self.fr, distSR, \
                                                        N1point, N2point, Ws, Wr, rs, rr, spos, rpos, phis, phir)
                    #                        print "Abar: ", Abar
                    #                        print "mixAttenuation: ", mixAttenuation
                                            IL = -(10.*np.log10(10.**(0.1*Abar)+10.**(0.1*AcanE)) + mixAttenuation) + 20.0*np.log10(distSR)+11   # insertion loss
#                                        print IL
                                        #calculating source contribution to immission level
                                        spowerDEN = sourceObj.immissonSpectrum  # loop for different oct frequency    
                                        IDay += 10**((np.array(spowerDEN[0])-3.0 + self.Aweight - IL)/10.0)   # -3.0 is to remove the ground effect. Day level                                        
                LD = 10*np.log10(IDay)
                LweightedD = 10*np.log10(sum(10**(0.1*(LD))))
                print ("Noise level: ", LD)
                print ("total A weighted: ", LweightedD)     
                self._writeResultOut(self.i, receiverObj.identify, LD, LweightedD)
                self.i += 1                
        else:
            print "No receiver in this zone!"
            print "Program will continue without writing anything out!"
            
def mergeDBF(receiverFile, resultFile, mergedFile, ID):
    DBFin1 = dbflib.open(receiverFile)      
    DBFin2 = dbflib.open(resultFile)
    DBFOut = dbflib.create(mergedFile)
    print DBFin1.record_count()-DBFin2.record_count(), ' points are missed.'
    # add field
    for n in xrange(DBFin1.field_count()):  
        fi = DBFin1.field_info(n)
        DBFOut.add_field(fi[1], fi[0], fi[2], fi[3])
    for n in xrange(DBFin2.field_count()):
        fi = DBFin2.field_info(n)
        DBFOut.add_field(fi[1], fi[0], fi[2], fi[3])
    # copy attributes
    for r in xrange(DBFin1.record_count()):
        print 'merging ', r, ' record'
        for f in xrange(DBFin1.field_count()):
            v = DBFin1.read_attribute(r, f)
            DBFOut.write_attribute(r, f, v)
        IDentify = DBFin1.read_record(r)[ID]
        for r2 in xrange(DBFin2.record_count()):
            if IDentify==DBFin2.read_record(r2)[ID]:
                break                
        for f in xrange(DBFin2.field_count()):
            v = DBFin2.read_attribute(r2, f)
            DBFOut.write_attribute(r, f+DBFin1.field_count(), v)
    DBFin1.close()
    DBFin2.close()
    DBFOut.close()          

def call_Model():
    sourceShape = 'sources-all-day'
    receiverShape = 'Gent_2m_dec20'
    buildingShape = 'buildings-all-yesHeightInfo2'
    mswt = input('\n\n      Input model type: 1--Scattering; 2--Multi-reflection: ')
    if mswt==1:
        Ctsqs = np.linspace(0.4, 4.0, 10)
        Cvsqs = np.linspace(1.2, 12.0, 10)
        for n in xrange(len(Ctsqs)):
            Ctsq = Ctsqs[n]
            Cvsq = Cvsqs[n]
            resultOutFile = 'outDATA-YESHeightInfoSCAT-'+str(n)
            mObj = Model(Cvsq, Ctsq, buildingShape, receiverShape, sourceShape, resultOutFile, \
                        flags=['D'], modelType='scattering')
            mObj.DBFOut.close()
    elif mswt==2:
        resultOutFile = 'withHeightFDTD-v8.2.2-Mar-25-4'
        mObj = Model(1, 1, buildingShape, receiverShape, sourceShape, resultOutFile, \
                        flags=['D'], modelType='FDTDfitting')
    else:
        print "\n    Wrong input!    \n"
#    mergeDBF('Copy of allZones.dbf', resultOutFile+'\\'+resultOutFile, resultOutFile+'\\'+resultOutFile+'_merged', 'GID')            
    print 'Done!'
if __name__=="__main__":       
    if len(sys.argv)>=1:
        call_Model()

