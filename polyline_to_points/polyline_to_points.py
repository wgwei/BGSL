# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 11:41:45 2014
split polyline to points by distance between adjacent points
@author: wgwei

"""

import shapelib
import dbflib
import numpy as np

def dist2D(p1, p2):
    return np.sqrt((p1[0]-p2[0])**2.+(p1[1]-p2[1])**2.)
    
class PolylineShape():
    def __init__(self, polylineShapeFile):
        self.shp = shapelib.ShapeFile(polylineShapeFile)
        self.PLNUM = self.shp.info()[0]
        print 'shape info: -> ', self.shp.info()
    
    def write_point_shape_out(self, pointShapeFileName, pointsList):
        w2shp = shapelib.create(pointShapeFileName, shapelib.SHPT_POINT)
        w2dbf = dbflib.create(pointShapeFileName)
        w2dbf.add_field('ID', dbflib.FTInteger, 10, 0) # create 3 field for the ID and x, y coordinate
        w2dbf.add_field('x', dbflib.FTDouble, 16, 2)
        w2dbf.add_field('y', dbflib.FTDouble, 16, 2)
        i = 0
        for pts in pointsList:
            for pt in pts:
                shpObj = shapelib.SHPObject(shapelib.SHPT_POINT, i, [[pt]])
                w2shp.write_object(i, shpObj)
                w2dbf.write_record(i, {'ID':i})
                w2dbf.write_record(i, {'x':pt[0]})
                w2dbf.write_record(i, {'y':pt[1]})
                i += 1
        w2shp.close()
        w2dbf.close()
        
    def polyShape_to_points_by_eqDist(self, distance):
        allPoints = []
        for m in xrange(self.PLNUM):
            print 'processing polyline %d' %m
            # read shape object and feed function polyline_to_points_by_eqDist
            pobj = self.shp.read_object(m)
            polyline = pobj.vertices()[0]
            points = self.polyline_to_points_by_eqDist(polyline, distance)
            allPoints.append(points)
        self.shp.close()
        return allPoints # a list of points for different polyline segments as: [[(x1, y1), (x2, y2)...], [(x1, y1), (x2, y2)...]]
        
    def polyline_to_points_by_eqDist(self, polyline, distance):
        ''' Split the polyline to points by distance. 
            polyline = [(x1, y1), (x2, y2), (x3, y3)...] is a list of points
            distance = number. The distance between two adjacent points. The 
            distance is along the polyline NOT the direct distance from two points
        '''
        i = 0
        dni = 0.0  #distance from the inserted pt to the vertice of polyline
        points = []   # coordinate of the splitted points as (x,y)
        points.append(polyline[0])
        while i<len(polyline)-1:
            distij = dist2D(polyline[i], polyline[i+1])
            dni = dni+distij
            
            # find the inserting points
            ix = polyline[i][0]
            iy = polyline[i][1]            
            if dni>=distance:
                ix = ix+(distance-(dni-distij))*(polyline[i+1][0]-polyline[i][0])/distij
                iy = iy+(distance-(dni-distij))*(polyline[i+1][1]-polyline[i][1])/distij
                points.append((ix, iy))
                ixiy2next = dist2D((ix, iy), polyline[i+1]) # updating the distance from the inserting points to the next vertice of the polyline
                while ixiy2next>distance:
                    ix = ix+distance*(polyline[i+1][0]-polyline[i][0])/distij
                    iy = iy+distance*(polyline[i+1][1]-polyline[i][1])/distij
                    points.append((ix, iy))
                    ixiy2next = dist2D((ix,iy), polyline[i+1])
                dni = ixiy2next # updating again
            i = i+1
        return points    # point list as: [(x1, y1), (x2, y2), (x3, y3)...]       
           
def split_polyline_to_points(lineShapeFileName, distance, newPointShapeFileName):
    ''' main function to split a polyline to points
        lineShapeFileName = shape file name of the poly line
        distance = distance between two points
        newPointShapeFileName = file name of the generated points
    '''
    pobj = PolylineShape(lineShapeFileName)
    pointlist = pobj.polyShape_to_points_by_eqDist(distance)
    pobj.write_point_shape_out(newPointShapeFileName, pointlist)
                
    
if __name__=='__main__':
    split_polyline_to_points()
