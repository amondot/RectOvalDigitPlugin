# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CADDigitize
                                 A QGIS plugin
 CAD like tools for QGis
 Fork of Rectangles Ovals Digitizing. Inspired by CadTools, LibreCAD/AutoCAD.
                              -------------------
        begin                : 2014-08-11
        git sha              : $Format:%H$
        copyright            : (C) 2014 by Loïc BARTOLETTI
        email                : l.bartoletti@free.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

# List comprehensions in canvasMoveEvent functions are
# adapted from Benjamin Bohard`s part of rectovaldiams plugin.

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import iface
from math import *
from tools.calc import *
from tools.circle import *
from CADDigitize_dialog import Ui_CADDigitizeDialogRadius

class ToolBar:
    def __init__(self):
        self.optionsToolBar = iface.mainWindow().findChild(
                QToolBar, u"CADDigitize Options")
        self.clear()
        self.circleOptions()


    #####################
    #      Circle       #
    #####################

    def segmentsettingsCircle(self):
        settings = QSettings()
        settings.setValue("/CADDigitize/circle/segments", self.spinBox.value())

    def circleOptions(self):
        settings = QSettings()
        self.optionsToolBar.clear()
        ###
        # Options
        ###
        # Add spinbox circle
        self.spinBox = QSpinBox(iface.mainWindow())
        self.spinBox.setMinimum(3)
        self.spinBox.setMaximum(3600)
        segvalue = settings.value("/CADDigitize/circle/segments",36,type=int)
        if not segvalue:
            settings.setValue("/CADDigitize/circle/segments", 36)
        self.spinBox.setValue(segvalue)
        self.spinBox.setSingleStep(1)
        self.spinBoxAction = self.optionsToolBar.addWidget(self.spinBox)
        self.spinBox.setToolTip( QCoreApplication.translate( "CADDigitize","Number of quadrant segments", None, QApplication.UnicodeUTF8))
        self.spinBoxAction.setEnabled(True)


        QObject.connect(self.spinBox, SIGNAL("valueChanged(int)"), self.segmentsettingsCircle)

    def clear(self):
        self.optionsToolBar.clear()

class CircleBy2PointsTool(QgsMapTool):
    def __init__(self, canvas):
        QgsMapTool.__init__(self,canvas)
        self.settings = QSettings()
        self.canvas=canvas
        self.nbPoints = 0
        self.rb = None
        self.x_p1, self.y_p1, self.x_p2, self.y_p2 = None, None, None, None
        self.mCtrl = None

        #our own fancy cursor
        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                      "      c None",
                                      ".     c #FF0000",
                                      "+     c #1210f3",
                                      "                ",
                                      "       +.+      ",
                                      "      ++.++     ",
                                      "     +.....+    ",
                                      "    +.     .+   ",
                                      "   +.   .   .+  ",
                                      "  +.    .    .+ ",
                                      " ++.    .    .++",
                                      " ... ...+... ...",
                                      " ++.    .    .++",
                                      "  +.    .    .+ ",
                                      "   +.   .   .+  ",
                                      "   ++.     .+   ",
                                      "    ++.....+    ",
                                      "      ++.++     ",
                                      "       +.+      "]))



    def keyPressEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = True


    def keyReleaseEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = False
        if event.key() == Qt.Key_Escape:
            if self.rb:
                self.rb.reset(True)
            self.nbPoints = 0
            self.rb = None
            self.x_p1, self.y_p1, self.x_p2, self.y_p2 = None, None, None, None
            self.canvas.refresh()

            return

    def changegeomSRID(self, geom):
        layer = self.canvas.currentLayer()
        renderer = self.canvas.mapRenderer()
        layerCRSSrsid = layer.crs().srsid()
        projectCRSSrsid = renderer.destinationCrs().srsid()
        if layerCRSSrsid != projectCRSSrsid:
            g = QgsGeometry.fromPoint(geom)
            g.transform(QgsCoordinateTransform(projectCRSSrsid, layerCRSSrsid))
            retPoint = g.asPoint()
        else:
            retPoint = geom

        return retPoint

    def canvasPressEvent(self,event):
        layer = self.canvas.currentLayer()
        if self.nbPoints == 0:
            color = QColor(255,0,0)
            self.rb = QgsRubberBand(self.canvas, True)
            self.rb.setColor(color)
            self.rb.setWidth(1)


        else:
            self.rb.reset(True)
            self.rb=None

            self.canvas.refresh()

        x = event.pos().x()
        y = event.pos().y()
        if self.mCtrl:
            (layerid, enabled, snapType, tolUnits, tol, avoidInt) = QgsProject.instance().snapSettingsForLayer(layer.id())
            startingPoint = QPoint(x,y)
            snapper = QgsMapCanvasSnapper(self.canvas)
            (retval,result) = snapper.snapToCurrentLayer (startingPoint, snapType, tol)
            if result <> [] and enabled == True:
                point = self.changegeomSRID(result[0].snappedVertex)
            else:
                (retval,result) = snapper.snapToBackgroundLayers(startingPoint)
                print result
                if result <> []:
                    point = self.changegeomSRID(result[0].snappedVertex)
                else:
                    point = self.toLayerCoordinates(layer,event.pos())
        else:
            point = self.toLayerCoordinates(layer,event.pos())
        pointMap = self.toMapCoordinates(layer, point)


        if self.nbPoints == 0:
            self.x_p1 = pointMap.x()
            self.y_p1 = pointMap.y()
        else:
            self.x_p2 = pointMap.x()
            self.y_p2 = pointMap.y()

        self.nbPoints += 1

        if self.nbPoints == 2:
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
            geom = Circle.getCircleBy2Points(QgsPoint(self.x_p1, self.y_p1), QgsPoint(self.x_p2, self.y_p2), segments)

            self.nbPoints = 0
            self.x_p1, self.y_p1, self.x_p2, self.y_p2 = None, None, None, None

            self.emit(SIGNAL("rbFinished(PyQt_PyObject)"), geom)

        if self.rb:return


    def canvasMoveEvent(self,event):
        segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
        if not self.rb:return
        currpoint = self.toMapCoordinates(event.pos())
        currx = currpoint.x()
        curry = currpoint.y()
        segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
        geom = Circle.getCircleBy2Points(QgsPoint(self.x_p1, self.y_p1), QgsPoint(currx, curry), segments)
    	self.rb.setToGeometry(geom, None)

    def showSettingsWarning(self):
        pass

    def activate(self):
        self.canvas.setCursor(self.cursor)
        self.optionsToolbar = ToolBar()

    def deactivate(self):
        if self.rb:
            self.rb.reset(True)
        self.nbPoints = 0
        self.rb = None
        self.x_p1, self.y_p1, self.x_p2, self.y_p2 = None, None, None, None

        self.optionsToolbar.clear()

        self.canvas.refresh()

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True



class CircleBy3PointsTool(QgsMapTool):
    def __init__(self, canvas):
        QgsMapTool.__init__(self,canvas)
        self.settings = QSettings()
        self.canvas = canvas
        self.nbPoints = 0
        self.rb = None
        self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.x_p3, self.y_p3 = None, None, None, None, None, None
        self.mCtrl = None
        #our own fancy cursor
        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                      "      c None",
                                      ".     c #FF0000",
                                      "+     c #1210f3",
                                      "                ",
                                      "       +.+      ",
                                      "      ++.++     ",
                                      "     +.....+    ",
                                      "    +.     .+   ",
                                      "   +.   .   .+  ",
                                      "  +.    .    .+ ",
                                      " ++.    .    .++",
                                      " ... ...+... ...",
                                      " ++.    .    .++",
                                      "  +.    .    .+ ",
                                      "   +.   .   .+  ",
                                      "   ++.     .+   ",
                                      "    ++.....+    ",
                                      "      ++.++     ",
                                      "       +.+      "]))


    def keyPressEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = True


    def keyReleaseEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = False
        if event.key() == Qt.Key_Escape:
            self.nbPoints = 0
            self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.x_p3, self.y_p3 = None, None, None, None, None, None
            if self.rb:
                self.rb.reset(True)
            self.rb=None

            self.canvas.refresh()

            return

    def changegeomSRID(self, geom):
        layer = self.canvas.currentLayer()
        renderer = self.canvas.mapRenderer()
        layerCRSSrsid = layer.crs().srsid()
        projectCRSSrsid = renderer.destinationCrs().srsid()
        if layerCRSSrsid != projectCRSSrsid:
            g = QgsGeometry.fromPoint(geom)
            g.transform(QgsCoordinateTransform(projectCRSSrsid, layerCRSSrsid))
            retPoint = g.asPoint()
        else:
            retPoint = geom

        return retPoint


    def canvasPressEvent(self,event):
        layer = self.canvas.currentLayer()
        if self.nbPoints == 0:
            color = QColor(255,0,0)
            self.rb = QgsRubberBand(self.canvas, True)
            self.rb.setColor(color)
            self.rb.setWidth(1)
        elif self.nbPoints == 2:
            self.rb.reset(True)
            self.rb=None

            self.canvas.refresh()

        x = event.pos().x()
        y = event.pos().y()
        if self.mCtrl:
            (layerid, enabled, snapType, tolUnits, tol, avoidInt) = QgsProject.instance().snapSettingsForLayer(layer.id())
            startingPoint = QPoint(x,y)
            snapper = QgsMapCanvasSnapper(self.canvas)
            (retval,result) = snapper.snapToCurrentLayer (startingPoint, snapType, tol)
            if result <> [] and enabled == True:
                point = self.changegeomSRID(result[0].snappedVertex)
            else:
                (retval,result) = snapper.snapToBackgroundLayers(startingPoint)
                print result
                if result <> []:
                    point = self.changegeomSRID(result[0].snappedVertex)
                else:
                    point = self.toLayerCoordinates(layer,event.pos())
        else:
            point = self.toLayerCoordinates(layer,event.pos())
        pointMap = self.toMapCoordinates(layer, point)


        if self.nbPoints == 0:
            self.x_p1 = pointMap.x()
            self.y_p1 = pointMap.y()
        elif self.nbPoints == 1:
            self.x_p2 = pointMap.x()
            self.y_p2 = pointMap.y()
        else:
            self.x_p3 = pointMap.x()
            self.y_p3 = pointMap.y()

        self.nbPoints += 1

        if self.nbPoints == 3:
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
            geom = Circle.getCircleBy3Points(QgsPoint(self.x_p1, self.y_p1), QgsPoint(self.x_p2, self.y_p2), QgsPoint(self.x_p3, self.y_p3), segments)

            self.nbPoints = 0
            self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.x_p3, self.y_p3 = None, None, None, None, None, None

            if geom != None:
                self.emit(SIGNAL("rbFinished(PyQt_PyObject)"), geom)

        if self.rb:return


    def canvasMoveEvent(self,event):

        if not self.rb:return
        currpoint = self.toMapCoordinates(event.pos())
        currx = currpoint.x()
        curry = currpoint.y()
        if self.nbPoints == 1:
            self.rb.setToGeometry(QgsGeometry.fromPolyline([QgsPoint(self.x_p1, self.y_p1), QgsPoint(currx, curry)]), None)

        if self.nbPoints >= 2 and calc_isCollinear(QgsPoint(self.x_p1, self.y_p1), QgsPoint(self.x_p2, self.y_p2), QgsPoint(currx, curry)) != 0:
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
            geom = Circle.getCircleBy3Points(QgsPoint(self.x_p1, self.y_p1), QgsPoint(self.x_p2, self.y_p2), QgsPoint(currx, curry), segments)
            if geom != None:
                self.rb.setToGeometry(geom, None)

    def showSettingsWarning(self):
        pass

    def activate(self):
        self.canvas.setCursor(self.cursor)
        self.optionsToolbar = ToolBar()

    def deactivate(self):
        self.nbPoints = 0
        self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.x_p3, self.y_p3 = None, None, None, None, None, None
        if self.rb:
            self.rb.reset(True)
        self.rb=None

        self.optionsToolbar.clear()

        self.canvas.refresh()

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True



class CircleByCenterPointTool(QgsMapTool):
    def __init__(self, canvas):
        QgsMapTool.__init__(self,canvas)
        self.settings = QSettings()
        self.canvas=canvas
        self.nbPoints = 0
        self.rb = None
        self.x_p1, self.y_p1, self.x_p2, self.y_p2 = None, None, None, None
        self.mCtrl = None
        #our own fancy cursor
        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                      "      c None",
                                      ".     c #FF0000",
                                      "+     c #1210f3",
                                      "                ",
                                      "       +.+      ",
                                      "      ++.++     ",
                                      "     +.....+    ",
                                      "    +.     .+   ",
                                      "   +.   .   .+  ",
                                      "  +.    .    .+ ",
                                      " ++.    .    .++",
                                      " ... ...+... ...",
                                      " ++.    .    .++",
                                      "  +.    .    .+ ",
                                      "   +.   .   .+  ",
                                      "   ++.     .+   ",
                                      "    ++.....+    ",
                                      "      ++.++     ",
                                      "       +.+      "]))



    def keyPressEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = True


    def keyReleaseEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = False
        if event.key() == Qt.Key_Escape:
            self.nbPoints = 0
            self.x_p1, self.y_p1, self.x_p2, self.y_p2 = None, None, None, None
            if self.rb:
                self.rb.reset(True)
            self.rb=None

            self.canvas.refresh()


            return

    def changegeomSRID(self, geom):
        layer = self.canvas.currentLayer()
        renderer = self.canvas.mapRenderer()
        layerCRSSrsid = layer.crs().srsid()
        projectCRSSrsid = renderer.destinationCrs().srsid()
        if layerCRSSrsid != projectCRSSrsid:
            g = QgsGeometry.fromPoint(geom)
            g.transform(QgsCoordinateTransform(projectCRSSrsid, layerCRSSrsid))
            retPoint = g.asPoint()
        else:
            retPoint = geom

        return retPoint


    def canvasPressEvent(self,event):
        layer = self.canvas.currentLayer()
        if self.nbPoints == 0:
            color = QColor(255,0,0)
            self.rb = QgsRubberBand(self.canvas, True)
            self.rb.setColor(color)
            self.rb.setWidth(1)
        else:
            self.rb.reset(True)
            self.rb=None

            self.canvas.refresh()

        x = event.pos().x()
        y = event.pos().y()
        if self.mCtrl:
            (layerid, enabled, snapType, tolUnits, tol, avoidInt) = QgsProject.instance().snapSettingsForLayer(layer.id())
            startingPoint = QPoint(x,y)
            snapper = QgsMapCanvasSnapper(self.canvas)
            (retval,result) = snapper.snapToCurrentLayer (startingPoint, snapType, tol)
            if result <> [] and enabled == True:
                point = self.changegeomSRID(result[0].snappedVertex)
            else:
                (retval,result) = snapper.snapToBackgroundLayers(startingPoint)
                print result
                if result <> []:
                    point = self.changegeomSRID(result[0].snappedVertex)
                else:
                    point = self.toLayerCoordinates(layer,event.pos())
        else:
            point = self.toLayerCoordinates(layer,event.pos())
        pointMap = self.toMapCoordinates(layer, point)


        if self.nbPoints == 0:
            self.x_p1 = pointMap.x()
            self.y_p1 = pointMap.y()
        else:
            self.x_p2 = pointMap.x()
            self.y_p2 = pointMap.y()

        self.nbPoints += 1

        if self.nbPoints == 2:
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
            geom = Circle.getCircleByCenterPoint(QgsPoint(self.x_p1, self.y_p1), QgsPoint(self.x_p2, self.y_p2), segments)

            self.nbPoints = 0
            self.x_p1, self.y_p1, self.x_p2, self.y_p2 = None, None, None, None

            self.emit(SIGNAL("rbFinished(PyQt_PyObject)"), geom)

        if self.rb:return


    def canvasMoveEvent(self,event):
        segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
        if not self.rb:return
        currpoint = self.toMapCoordinates(event.pos())
        currx = currpoint.x()
        curry = currpoint.y()
    	self.rb.setToGeometry(Circle.getCircleByCenterPoint(QgsPoint(self.x_p1, self.y_p1), QgsPoint(currx, curry), segments), None)

    def showSettingsWarning(self):
        pass

    def activate(self):
        self.canvas.setCursor(self.cursor)
        self.optionsToolbar = ToolBar()

    def deactivate(self):
        self.nbPoints = 0
        self.x_p1, self.y_p1, self.x_p2, self.y_p2 = None, None, None, None
        if self.rb:
            self.rb.reset(True)
        self.rb=None

        self.optionsToolbar.clear()

        self.canvas.refresh()

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True


class CircleByCenterRadiusTool(QgsMapTool):
    def __init__(self, canvas):
        QgsMapTool.__init__(self,canvas)
        self.settings = QSettings()
        self.canvas=canvas
        self.nbPoints = 0
        self.rb = None
        self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.currx, self.curry = None, None, None, None, None, None
        self.circ_rayon = -1
        self.mCtrl = None
        self.setval = False
        #our own fancy cursor
        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                      "      c None",
                                      ".     c #FF0000",
                                      "+     c #1210f3",
                                      "                ",
                                      "       +.+      ",
                                      "      ++.++     ",
                                      "     +.....+    ",
                                      "    +.     .+   ",
                                      "   +.   .   .+  ",
                                      "  +.    .    .+ ",
                                      " ++.    .    .++",
                                      " ... ...+... ...",
                                      " ++.    .    .++",
                                      "  +.    .    .+ ",
                                      "   +.   .   .+  ",
                                      "   ++.     .+   ",
                                      "    ++.....+    ",
                                      "      ++.++     ",
                                      "       +.+      "]))
        self.initGui()

    def setRadiusValue(self):
        self.circ_rayon = self.dialog.SpinBox_Radius.value()
        if self.circ_rayon != None and self.circ_rayon > 0:
            self.currx = self.x_p1 + sin(self.circ_rayon)
            self.curry = self.y_p1 + cos(self.circ_rayon)
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
    	    self.rb.setToGeometry(Circle.getCircleByCenterRadius(QgsPoint(self.x_p1, self.y_p1), self.circ_rayon, segments), None)

    def finishedRadius(self):
        segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
        geom = Circle.getCircleByCenterRadius(QgsPoint(self.x_p1, self.y_p1), self.circ_rayon, segments)

        self.nbPoints = 0
        self.emit(SIGNAL("rbFinished(PyQt_PyObject)"), geom)
        self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.currx, self.curry = None, None, None, None, None, None
        self.circ_rayon = -1
        self.setval = True
        self.rb.reset(True)
        self.rb=None

        self.canvas.refresh()
        self.dialog.SpinBox_Radius.setValue(0)

        return

    def initGui(self):
        self.dialog = Ui_CADDigitizeDialogRadius()
        self.dialog.SpinBox_Radius.valueChanged.connect(self.setRadiusValue)
        self.dialog.buttonBox.accepted.connect(self.finishedRadius)

    def keyPressEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = True

    def keyReleaseEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = False
        if event.key() == Qt.Key_Escape:
            self.nbPoints = 0
            self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.currx, self.curry = None, None, None, None, None, None
            self.circ_rayon = -1
            self.setval = True
            if self.rb:
                self.rb.reset(True)
            self.rb=None

            self.canvas.refresh()
            self.dialog.SpinBox_Radius.setValue(0)
            self.dialog.close()

            return

    def changegeomSRID(self, geom):
        layer = self.canvas.currentLayer()
        renderer = self.canvas.mapRenderer()
        layerCRSSrsid = layer.crs().srsid()
        projectCRSSrsid = renderer.destinationCrs().srsid()
        if layerCRSSrsid != projectCRSSrsid:
            g = QgsGeometry.fromPoint(geom)
            g.transform(QgsCoordinateTransform(projectCRSSrsid, layerCRSSrsid))
            retPoint = g.asPoint()
        else:
            retPoint = geom

        return retPoint


    def canvasPressEvent(self,event):
        layer = self.canvas.currentLayer()
        if self.nbPoints == 0:
            self.setval = False
            color = QColor(255,0,0)
            self.rb = QgsRubberBand(self.canvas, True)
            self.rb.setColor(color)
            self.rb.setWidth(1)
        else:
            self.rb.reset(True)
            self.rb=None

            self.canvas.refresh()

        x = event.pos().x()
        y = event.pos().y()
        if self.mCtrl:
            (layerid, enabled, snapType, tolUnits, tol, avoidInt) = QgsProject.instance().snapSettingsForLayer(layer.id())
            startingPoint = QPoint(x,y)
            snapper = QgsMapCanvasSnapper(self.canvas)
            (retval,result) = snapper.snapToCurrentLayer (startingPoint, snapType, tol)
            if result <> [] and enabled == True:
                point = self.changegeomSRID(result[0].snappedVertex)
            else:
                (retval,result) = snapper.snapToBackgroundLayers(startingPoint)
                print result
                if result <> []:
                    point = self.changegeomSRID(result[0].snappedVertex)
                else:
                    point = self.toLayerCoordinates(layer,event.pos())
        else:
            point = self.toLayerCoordinates(layer,event.pos())
        pointMap = self.toMapCoordinates(layer, point)


        if self.nbPoints == 0:
            self.x_p1 = pointMap.x()
            self.y_p1 = pointMap.y()
            self.dialog.show()
        else:
            self.x_p2 = pointMap.x()
            self.y_p2 = pointMap.y()

        self.nbPoints += 1

        if self.nbPoints == 2:
            self.dialog.close()
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
            geom = Circle.getCircleByCenterRadius(QgsPoint(self.x_p1, self.y_p1), self.circ_rayon, segments)

            self.nbPoints = 0
            self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.currx, self.curry = None, None, None, None, None, None

            self.emit(SIGNAL("rbFinished(PyQt_PyObject)"), geom)


        if self.rb:return


    def canvasMoveEvent(self,event):
        segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
        if not self.rb:return
        currpoint = self.toMapCoordinates(event.pos())
        self.currx = currpoint.x()
        self.curry = currpoint.y()
        if self.setval == False:
            self.circ_rayon = QgsDistanceArea().measureLine(QgsPoint(self.x_p1, self.y_p1), QgsPoint(self.currx, self.curry))
            self.dialog.SpinBox_Radius.setValue(self.circ_rayon)


        geom = Circle.getCircleByCenterRadius(QgsPoint(self.x_p1, self.y_p1), self.circ_rayon, segments)
    	self.rb.setToGeometry(geom, None)

    def showSettingsWarning(self):
        pass

    def activate(self):
        self.canvas.setCursor(self.cursor)
        self.optionsToolbar = ToolBar()

    def deactivate(self):
        self.nbPoints = 0
        self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.currx, self.curry = None, None, None, None, None, None
        self.circ_rayon = -1
        self.setval = True
        if self.rb:
            self.rb.reset(True)
        self.rb=None

        self.optionsToolbar.clear()

        self.canvas.refresh()
        self.dialog.SpinBox_Radius.setValue(0)
        self.dialog.close()

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

class CircleBy2TangentsTool(QgsMapTool):
    def __init__(self, canvas):
        QgsMapTool.__init__(self,canvas)
        self.settings = QSettings()
        self.canvas=canvas
        self.nbPoints = 0
        self.rb, self.rb1, self.rb2, self.rb_points = None, None, None, None
        self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.currx, self.curry = None, None, None, None, None, None
        self.point1, self.point2 = None, None
        self.p1, self.p2, self.p3, self.p4 = None, None, None, None
        self.p11, self.p12, self.p21, self.p22 = None, None, None, None
        self.circ_rayon = -1
        self.mCtrl = None
        self.setval = False
        #our own fancy cursor
        self.cursor = QCursor(QPixmap(["16 16 3 1",
                                      "      c None",
                                      ".     c #FF0000",
                                      "+     c #1210f3",
                                      "                ",
                                      "       +.+      ",
                                      "      ++.++     ",
                                      "     +.....+    ",
                                      "    +.     .+   ",
                                      "   +.   .   .+  ",
                                      "  +.    .    .+ ",
                                      " ++.    .    .++",
                                      " ... ...+... ...",
                                      " ++.    .    .++",
                                      "  +.    .    .+ ",
                                      "   +.   .   .+  ",
                                      "   ++.     .+   ",
                                      "    ++.....+    ",
                                      "      ++.++     ",
                                      "       +.+      "]))
        self.initGui()

    def setRadiusValue(self):
        self.circ_rayon = self.dialog.SpinBox_Radius.value()
        if self.circ_rayon != None and self.circ_rayon > 0:
            self.currx = self.x_p1 + sin(self.circ_rayon)
            self.curry = self.y_p1 + cos(self.circ_rayon)
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
    	    self.rb.setToGeometry(Circle.getCircleByCenterRadius(QgsPoint(self.x_p1, self.y_p1), self.circ_rayon, segments), None)

    def getPossibleCenter(self):
        of_join = self.settings.value("Qgis/digitizing/offset_join_style",0,type=int)
        of_quad = self.settings.value("Qgis/digitizing/offset_quad_seg",8,type=int)
        of_miter = self.settings.value("Qgis/digitizing/offset_miter_limit",5,type=int)

        lo1m = self.rb1.asGeometry().offsetCurve(-self.circ_rayon, of_quad, of_join, of_miter)
        lo1p = self.rb1.asGeometry().offsetCurve(+self.circ_rayon, of_quad, of_join, of_miter)
        lo2m = self.rb2.asGeometry().offsetCurve(-self.circ_rayon, of_quad, of_join, of_miter)
        lo2p = self.rb2.asGeometry().offsetCurve(+self.circ_rayon, of_quad, of_join, of_miter)

        lo1m1, lo1m2 = qgsPolyline_NParray(lo1m)
        lo2m1, lo2m2 = qgsPolyline_NParray(lo2m)
        lo1p1, lo1p2 = qgsPolyline_NParray(lo1p)
        lo2p1, lo2p2 = qgsPolyline_NParray(lo2p)

        self.p1 = npArray_qgsPoint(seg_intersect(lo1m1, lo1m2, lo2m1, lo2m2) )
        self.p2 = npArray_qgsPoint(seg_intersect(lo1m1, lo1m2, lo2p1, lo2p2) )
        self.p3 = npArray_qgsPoint(seg_intersect(lo1p1, lo1p2, lo2m1, lo2m2) )
        self.p4 = npArray_qgsPoint(seg_intersect(lo1p1, lo1p2, lo2p1, lo2p2) )


        self.rb_points = QgsRubberBand(self.canvas, QGis.Point)
        self.rb_points.setColor(QColor(0,0,255))
        self.rb_points.setWidth(3)
        self.rb_points.setToGeometry(QgsGeometry.fromMultiPoint([self.p1, self.p2, self.p3, self.p4]), None)

        self.canvas.refresh

    def finishedRadius(self):
        self.getPossibleCenter()
        self.setval = True


    def initGui(self):
        self.dialog = Ui_CADDigitizeDialogRadius()
        self.dialog.SpinBox_Radius.valueChanged.connect(self.setRadiusValue)
        self.dialog.buttonBox.accepted.connect(self.finishedRadius)
        self.dialog.buttonBox.rejected.connect(self.clear)

    def keyPressEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = True

    def keyReleaseEvent(self,  event):
        if event.key() == Qt.Key_Control:
            self.mCtrl = False
        if event.key() == Qt.Key_Escape:

            self.clear()
            return


    def canvasPressEvent(self,event):
        layer = self.canvas.currentLayer()

        x = event.pos().x()
        y = event.pos().y()

        flag = False

        if self.nbPoints == 2:
            flag = True

        (layerid, enabled, snapType, tolUnits, tol, avoidInt) = QgsProject.instance().snapSettingsForLayer(layer.id())
        startingPoint = QPoint(x,y)
        snapper = QgsMapCanvasSnapper(self.canvas)
        (retval,result) = snapper.snapToCurrentLayer (startingPoint, snapType, tol)
        if result <> []:
            self.point1 = result[0].beforeVertex
            self.point2 = result[0].afterVertex
            flag = True
        else:
            (retval,result) = snapper.snapToBackgroundLayers(startingPoint)
            if result <> []:
                self.point1 = result[0].beforeVertex
                self.point2 = result[0].afterVertex
                flag = True


        if self.nbPoints == 0 and flag:
            self.setval = False

            self.p11 = qgsPoint_NParray(self.point1)
            self.p12 = qgsPoint_NParray(self.point2)

            self.rb1 = QgsRubberBand(self.canvas, True)
            self.rb1.setColor(QColor(0,0,255))
            self.rb1.setWidth(3)
            self.rb1.setToGeometry(QgsGeometry.fromPolyline([self.point1, self.point2]), None)

        if self.nbPoints == 1 and flag:
            self.p21 = qgsPoint_NParray(self.point1)
            self.p22 = qgsPoint_NParray(self.point2)

            p_inter = seg_intersect(self.p11, self.p12, self.p21, self.p22)

            if p_inter == None:
                iface.messageBar().pushMessage(QCoreApplication.translate( "CADDigitize","Error", None, QApplication.UnicodeUTF8), QCoreApplication.translate( "CADDigitize", "Segments are parallels", None, QApplication.UnicodeUTF8), level=QgsMessageBar.CRITICAL)
                flag = False
            else:
                self.x_p1 = p_inter[0]
                self.y_p1 = p_inter[1]

                self.rb2 = QgsRubberBand(self.canvas, True)
                self.rb2.setColor(QColor(0,0,255))
                self.rb2.setWidth(3)
                self.rb2.setToGeometry(QgsGeometry.fromPolyline([self.point1, self.point2]), None)

                self.rb = QgsRubberBand(self.canvas, True)
                self.rb.setColor(QColor(255,0,0))
                self.rb.setWidth(1)

                self.dialog.show()

        if self.nbPoints == 2:
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
            geom = Circle.getCircleByCenterRadius(QgsPoint(self.x_p1, self.y_p1), self.circ_rayon, segments)

            self.emit(SIGNAL("rbFinished(PyQt_PyObject)"), geom)


            self.clear()

            return

        if self.nbPoints < 2 and flag:
            self.nbPoints += 1

        if self.rb:return

    def canvasMoveEvent(self,event):
        if self.nbPoints >= 2 and self.setval == True:
            segments = self.settings.value("/CADDigitize/circle/segments",36,type=int)
            if not self.rb:return
            currpoint = self.toMapCoordinates(event.pos())
            self.currx = currpoint.x()
            self.curry = currpoint.y()
            list_points = [self.p1, self.p2, self.p3, self.p4]

            distance = [QgsDistanceArea().measureLine(p, QgsPoint(self.currx, self.curry) ) for p in list_points]

            i = distance.index(min(distance))
            self.x_p1 = list_points[i].x()
            self.y_p1 = list_points[i].y()

            geom = Circle.getCircleByCenterRadius(QgsPoint(self.x_p1, self.y_p1), self.circ_rayon, segments)
            self.rb.setToGeometry(geom, None)

            self.canvas.refresh()


    def activate(self):
        self.canvas.setCursor(self.cursor)
        self.optionsToolbar = ToolBar()

    def clear(self):
        self.nbPoints = 0
        self.x_p1, self.y_p1, self.x_p2, self.y_p2, self.currx, self.curry = None, None, None, None, None, None
        self.circ_rayon = -1
        self.point1, self.point2 = None, None
        self.p11, self.p12, self.p21, self.p22 = None, None, None, None
        self.p1, self.p2, self.p3, self.p4 = None, None, None, None
        self.setval = False
        if self.rb:
            self.rb.reset(True)
        if self.rb1:
            self.rb1.reset(True)
        if self.rb2:
            self.rb2.reset(True)
        if self.rb_points:
            self.rb_points.reset(True)
        self.rb, self.rb1, self.rb2, self.rb_points = None, None, None, None

        self.canvas.refresh()
        self.dialog.SpinBox_Radius.setValue(0)
        self.dialog.close()


    def deactivate(self):
        self.clear()
        self.optionsToolbar.clear()

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True


