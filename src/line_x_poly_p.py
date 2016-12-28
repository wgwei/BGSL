# -*- coding: utf-8 -*-
"""
Created on Fri Dec 20 17:54:57 2013
find the intersection of a line and a polygon
@author: W.Wei
"""

def intersection(p1, p2, p3, p4):
    ''' calcualte the intersection of two lines defined by piont1 ->p1, 
        point 2, point 3 and point4. 
        p1 and p2 stand for line 1
        p3 and p4 stand for line 2
    '''
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    x3, y3 = p3[0], p3[1]
    x4, y4 = p4[0], p4[1]
    try:
        x = ((x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4))/((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))
        y = ((x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4))/((x1-x2)*(y3-y4)-(y1-y2)*(x3-x4))
        return [x, y]
    except:
        # one point coincides each other 
        if (x1==x3 and y1==y3) or (x1==x4 and y1==y4):
            return [x1, y1]
        elif (x2==x3 and y2==y3) or (x2==x4 and y2==y4):
            return [x2, y2]
        else:
            # parallized line segments
            return [[], []]
    

def is_interSegment(point, lineStartPt, lineEndPt, lineStartPt2, lineEndPt2):
    ''' Check wether point is the intersection point of line [lineStartPt, lineEndPt]
         and line [lineStartPt2, lineEndPt2]
        point = [x, y] 
        lineStartPt = [x, y]
        lineEndPt = [x, y]
        lineStartPt2 = [x, y]
        lineEndPt2 = [x, y]
    '''
    x, y = point[0], point[1]
    leftPtLi = min(lineStartPt[0], lineEndPt[0])
    rightPtLi = max(lineStartPt[0], lineEndPt[0])
    highPtLi = max(lineStartPt[1], lineEndPt[1])
    lowPtLi = min(lineStartPt[1], lineEndPt[1])
    leftPtL2 = min(lineStartPt2[0], lineEndPt2[0])
    rightPtL2 = max(lineStartPt2[0], lineEndPt2[0])
    highPtL2 =  max(lineStartPt2[1], lineEndPt2[1])
    lowPtL2 = min(lineStartPt2[1], lineEndPt2[1])

    xlim = [max(leftPtLi, leftPtL2), min(rightPtLi, rightPtL2)]
    ylim = [max(lowPtLi, lowPtL2), min(highPtLi, highPtL2)]
    
    if x>=xlim[0] and x<=xlim[1] and y>=ylim[0] and y<=ylim[1]:
        return True
    else:
        return False
        
def line_x_poly(lineStartPt, lineEndPt, polygonx, polygony):
    ''' Find the intersection by a line and a polygon    
        WARNING: if the instersection point is coincide with the joint point 
        between two line segment, the resutls will return one point more than 
        once.         
        lineStartPt = [x, y]
        lineEndPt = [x, y]
        polygonx = [x1, x2, x3,..., xn, x1]
        polygony = [y1, y2, y3,...,yn, y1]        
    '''
    assert (len(polygonx)==len(polygony)), 'The size x-corrdinate must be the same with y-coordinate'
    assert (polygonx[0]==polygonx[-1] and polygony[0]==polygony[-1]), 'The start point of the vector must be coincide with the last point'
    intersecPt = []
    for n in xrange(len(polygonx)-1):
        pti = [polygonx[n], polygony[n]]
        pt2 = [polygonx[n+1], polygony[n+1]]
        ipt = intersection(lineStartPt, lineEndPt, pti, pt2)        
        if ipt:
            isintsec = is_interSegment(ipt, lineStartPt, lineEndPt, pti, pt2)
            if isintsec:
                intersecPt.append(ipt)                     
    return intersecPt
        
        
if __name__=='__main__':
    if 1:
        for n in range(100):
            p1 = [0., 0.]
            p2 = [10., 10]
            polyx = [1, 5, 5, 1, 1]
            polyy = [1, 1, 10, 10, 1]
            intersecPt = line_x_poly(p1,p2,polyx,polyy)
            print 'intersecPt'
            print intersecPt
        
       