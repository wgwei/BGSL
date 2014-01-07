# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 11:41:45 2014
split polyline to points by distance between adjacent points
@author: wgwei

"""

import sys
sys.path.append(r'/home/wgwei/Documents/projects/SSM/test')
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
        w2dbf.add_field('ID', dbflib.FTInteger, 10, 0)
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
            pobj = self.shp.read_object(m)
            polyline = pobj.vertices()[0]
            points = self.polyline_to_points_by_eqDist(polyline, distance)
            allPoints.append(points)
        self.shp.close()
        return allPoints
        
    def polyline_to_points_by_eqDist(self, polyline, distance):
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
                ixiy2next = dist2D((ix, iy), polyline[i+1])
                while ixiy2next>distance:
                    ix = ix+distance*(polyline[i+1][0]-polyline[i][0])/distij
                    iy = iy+distance*(polyline[i+1][1]-polyline[i][1])/distij
                    points.append((ix, iy))
                    ixiy2next = dist2D((ix,iy), polyline[i+1])
                dni = ixiy2next
            i = i+1
        return points               
           
def main():
    pobj = PolylineShape(r'tram')
    pointlist = pobj.polyShape_to_points_by_eqDist(10.0)
    pobj.write_point_shape_out('ti', pointlist)
                
    
if __name__=='__main__':
    main()
