#-*- coding: utf-8 -*-
from qgis.core import *
from math import *

def calc_circleBy2Points(p1, p2):
    center = QgsPoint( (p1.x() + p2.x()) / 2.0, (p1.y() + p2.y()) / 2.0 )
    rayon =QgsDistanceArea().measureLine(p1, center)
    return (center, rayon)

def calc_circleBy3Points(p1, p2, p3):
# Paul Bourke's algorithm
    m_Center = QgsPoint()
    m_dRadius = -1
    yDelta_a = p2.y() - p1.y()
    xDelta_a = p2.x() - p1.x()
    yDelta_b = p3.y() - p2.y()
    xDelta_b = p3.x() - p2.x()
    try:
        aSlope=yDelta_a/xDelta_a
    except ZeroDivisionError:
        return (-1,-1)
    try:
        bSlope=yDelta_b/xDelta_b
    except ZeroDivisionError:
        return (-1,-1)

    if (fabs(xDelta_a) <= 0.000000001 and fabs(yDelta_b) <= 0.000000001):
        m_Center.setX(0.5*(p2.x() + p3.x()))
        m_Center.setY(0.5*(p1.y() + p2.y()))
        m_dRadius = QgsDistanceArea().measureLine(m_Center,p1)

        return (m_Center, m_dRadius)

	# IsPerpendicular() assure that xDelta(s) are not zero

	if fabs(aSlope-bSlope) <= 0.000000001:	# checking whether the given points are colinear.
		return (-1,-1)


	# calc center
    m_Center.setX( (aSlope*bSlope*(p1.y() - p3.y()) + bSlope*(p1.x() + p2.x()) - aSlope*(p2.x()+p3.x()) )/(2.0* (bSlope-aSlope) ) )
    m_Center.setY( -1.0*(m_Center.x() - (p1.x()+p2.x())/2.0)/aSlope +  (p1.y()+p2.y())/2.0 )

    m_dRadius = QgsDistanceArea().measureLine(m_Center,p1)

    return (m_Center, m_dRadius)

    # longueur A = p1p2, B = p2p3, C = p3p1
#    A, B, C =QgsDistanceArea().measureLine(p1, p2),QgsDistanceArea().measureLine(p2, p3),QgsDistanceArea().measureLine(p3, p1)
#    rayon = (A * B * C) / sqrt( (A + B + C) * (-A + B + C) * (A - B + C) * (A + B - C) )
#    D = 2 * (p1.x() * (p2.y()-p3.y()) + p2.x() * (p3.y()-p1.y())+p3.x()*(p1.y()-p2.y()))
#    center = QgsPoint()
#    center.setX( ((pow(p1.x(), 2.0) + pow(p1.y(), 2.0))*(p2.y() - p3.y()) + (pow(p2.x(), 2.0) + pow(p2.y(), 2.0))*(p3.y()-p1.y()) + (pow(p3.x(), 2.0) + pow(p3.y(), 2.0))*(p1.y()-p2.y()))/D )
#    center.setY(((pow(p1.x(), 2.0) + pow(p1.y(), 2.0))*(p3.x() - p2.x()) + (pow(p2.x(), 2.0) + pow(p2.y(), 2.0))*(p1.x()-p3.x()) + (pow(p3.x(), 2.0) + pow(p3.y(), 2.0))*(p2.x()-p1.x()))/D )
#    return (center, rayon)

def calc_circleByCenterRadius(p1, radius):
    return (p1, radius)

def calc_circleByCenterPoint(pc, p1):
    return (pc,QgsDistanceArea().measureLine(pc, p1))


